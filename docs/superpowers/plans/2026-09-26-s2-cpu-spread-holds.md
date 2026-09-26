# S2 CPU-spread holds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run five both-off S2 holds under one agreed CPU table, in mix order 6 → 7 → 10 → 26 → 12, then score every service with the (a)/(b)/(c) reading.

**Architecture:** The both-off YAML carries absolute `cpu_limit_millicores` for the ten services whose caps change. Frontend stays at the paper 1150 m per replica and is pinned to 5 replicas with an HPA patch, because `scale_constraints` rejects replica changes on HPA-managed deployments. The runner's paper-CPU reconcile is turned off for these five holds: paper backends plus 5 × 1150 m do not fit the worker. Spread CPU is applied once while frontend is still at 4 replicas, then the fifth replica is added, then the five holds run without another CPU rollout. After the last hold, frontend is scaled back to 4 before paper CPU is restored. A small scorer then writes the all-service (a)/(b)/(c) guide.

**Tech Stack:** Python 3, PyYAML, `experiments/run_scenario.py`, `experiments/topfull_cpu_quotas.py`, kubectl over `ssh topfull-master`, Locust via `online_boutique_create_v2.sh`.

## Global Constraints

- Mix order is fixed: mix 6, mix 7, mix 10, mix 26, mix 12. Counts are getproduct / postcheckout / getcart / postcart / emptycart.
- Slots, in that order: `baseline_no_topfull_sustained_overload_run30` (340/100/240/10/10), `run31` (380/100/270/20/20), `run32` (325/80/100/100/5), `run33` (325/100/100/100/5), `run34` (100/150/100/100/5). Do not reuse or overwrite run6, run7, run10, run12, or run26.
- Each hold is 600 s, `spawn_rate` 50, `topfull_rl.enabled: false`, `retryguard.enabled: false`, Istio `attempts: 3`, `per_try_timeout_ms: 500`.
- Cool-off is 360 s of idle cluster after each hold's pull-and-gate and before the next launch. Four gaps: after run30, run31, run32, and run33. Also 360 s after the fifth frontend pod is Ready and before run30.
- Agreed per-replica millicores: frontend 1150, checkoutservice 1500, recommendationservice 2000, productcatalogservice 600, cartservice 1000, currencyservice 500, shippingservice 400, adservice 600, paymentservice 150, emailservice 150, redis-cart 500. Request equals limit. Frontend is 5 replicas. Every other service stays at 1 replica (catalog HPA `maxReplicas: 1` for the series).
- Deployment total at 5 × frontend is 13150 m. That must stay ≤ the paper 4 × frontend total of 13360 m.
- `redis-cart` container name is `redis`. Every other constrained container is `server`. Frontend is not a `scale_constraints` entry.
- While pinned: leave `sidecar.istio.io/proxyCPU` at 100m. Do not drop it to 90m. `sidecar.istio.io/proxyCPULimit` stays absent. The 90m request was only so a fourth frontend pod could schedule against the paper app table (13360 m + 14 × 100 m sidecars was about 10 m over allocatable). This table's app total is 13150 m; five frontend sidecars at 100 m plus ten backend sidecars at 100 m is 15900 m with the same ~1250 m of system requests, 70 m under the 4 × 90 m pin that already scheduled. A Deployment-object annotate does not roll pods; if `proxyCPULimit` is present, remove it by patching `spec.template.metadata.annotations`.
- `paper_cpu_reconcile: false` on the five launches. Restore paper CPU only after frontend HPA is back to `minReplicas: 1`, `maxReplicas: 4`.
- SSH host aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`). Do not hardcode IPs. Do not stop the VMs.
- If a hold fails its gate, do not launch the next mix. Go to the restore task.
- (a) A high sample is `(Δ5xx + Δresets) / Δtotal > 0.20`. A disable is a streak of at least 30 consecutive high samples. Frontend and redis-cart are reported and are not controlled.
- (b) Detector bar is `overloaded=1` on at least half of that service's `topfull_detect.csv` rows. Layer A threshold stays at the 10000 passthrough sentinel.
- (c) Retry volume is the sum of positive Envoy `retry` increments on each caller→target edge.

---

### Task 1: Lock the spread table on the both-off YAML

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Modify: `experiments/test_topfull_cpu_quotas.py`
- Modify: `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md`
- Test: `experiments/test_topfull_cpu_quotas.py`

**Interfaces:**
- Consumes: `topfull_cpu_quotas.effective_cpu_quotas(constraints) -> dict[str, int]`
- Produces: YAML key `paper_cpu_reconcile: false` and ten `scale_constraints` entries. Later tasks read this file and change only `run_number`, `log_folder`, `description`, and `locust.user_counts` until Task 10.

- [ ] **Step 1: Write the failing test**

Append this class to `experiments/test_topfull_cpu_quotas.py`:

```python
class TestBothOffSpreadYaml(unittest.TestCase):
    def test_spread_table_and_five_replica_budget(self):
        import yaml
        from pathlib import Path

        path = Path(__file__).resolve().parent / "configs" / "scenario_2_baseline_no_topfull.yaml"
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertIs(cfg["paper_cpu_reconcile"], False)
        self.assertIs(cfg["topfull_rl"]["enabled"], False)
        self.assertIs(cfg["retryguard"]["enabled"], False)
        self.assertEqual(cfg["duration_seconds"], 600)
        self.assertEqual(cfg["locust"]["spawn_rate"], 50)

        by_dep = {c["deployment"]: c for c in cfg["scale_constraints"]}
        self.assertNotIn("frontend", by_dep)
        self.assertEqual(by_dep["redis-cart"]["container"], "redis")
        for dep, entry in by_dep.items():
            if dep == "redis-cart":
                continue
            self.assertEqual(entry["container"], "server")
            self.assertEqual(entry["method"], "cpu_limit")
            self.assertNotIn("cpu_limit_fraction", entry)

        got = q.effective_cpu_quotas(cfg["scale_constraints"])
        expected = {
            "frontend": 1150,
            "checkoutservice": 1500,
            "recommendationservice": 2000,
            "productcatalogservice": 600,
            "cartservice": 1000,
            "currencyservice": 500,
            "shippingservice": 400,
            "adservice": 600,
            "paymentservice": 150,
            "emailservice": 150,
            "redis-cart": 500,
        }
        for name, millis in expected.items():
            self.assertEqual(got[name], millis, name)
        deployment_total = expected["frontend"] * 5 + sum(
            millis for name, millis in expected.items() if name != "frontend"
        )
        self.assertEqual(deployment_total, 13150)
        paper_four = 4 * 1150 + (
            615 + 1150 + 1535 + 1920 + 770 + 770 + 1150 + 155 + 155 + 540
        )
        self.assertEqual(paper_four, 13360)
        self.assertLessEqual(deployment_total, paper_four)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python experiments/test_topfull_cpu_quotas.py TestBothOffSpreadYaml -v`

Expected: FAIL because `paper_cpu_reconcile` is missing. There is no `experiments/__init__.py`; run the test file directly.

- [ ] **Step 3: Write the YAML and the guide table**

Replace `experiments/configs/scenario_2_baseline_no_topfull.yaml` with:

```yaml
# Both-off S2. run30–run34 are the CPU-spread series (mixes 6, 7, 10, 26, 12).
# paper_cpu_reconcile stays false until that series is restored to paper CPU.
# Frontend is not in scale_constraints: 1150m is already the paper limit.
# The fifth replica is an HPA pin, applied outside this file.

scenario_id: 2
scenario_name: sustained_overload
condition: baseline
run_number: 30
description: >
  Both controllers off. Spread CPU table, frontend pinned at 5.
  This slot is mix 6: 340/100/240/10/10.

duration_seconds: 600

locust:
  user_counts:
    getproduct:   340
    postcheckout: 100
    getcart:      240
    postcart:     10
    emptycart:    10
  spawn_rate: 50
  scripts:
    - online_boutique_create_v2.sh

paper_cpu_reconcile: false

scale_constraints:
  - {deployment: checkoutservice, namespace: default, method: cpu_limit, cpu_limit_millicores: 1500, container: server}
  - {deployment: recommendationservice, namespace: default, method: cpu_limit, cpu_limit_millicores: 2000, container: server}
  - {deployment: productcatalogservice, namespace: default, method: cpu_limit, cpu_limit_millicores: 600, container: server}
  - {deployment: cartservice, namespace: default, method: cpu_limit, cpu_limit_millicores: 1000, container: server}
  - {deployment: currencyservice, namespace: default, method: cpu_limit, cpu_limit_millicores: 500, container: server}
  - {deployment: shippingservice, namespace: default, method: cpu_limit, cpu_limit_millicores: 400, container: server}
  - {deployment: adservice, namespace: default, method: cpu_limit, cpu_limit_millicores: 600, container: server}
  - {deployment: paymentservice, namespace: default, method: cpu_limit, cpu_limit_millicores: 150, container: server}
  - {deployment: emailservice, namespace: default, method: cpu_limit, cpu_limit_millicores: 150, container: server}
  - {deployment: redis-cart, namespace: default, method: cpu_limit, cpu_limit_millicores: 500, container: redis}

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

log_folder: baseline_no_topfull_sustained_overload_run30

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

In `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md`, replace the Suggested column and the mixes section so the agreed table is the one this series runs. Replacement table:

```markdown
| Service | Paper | Dispense (runs 18–21) | Agreed (runs 30–34) |
|---|---:|---:|---:|
| frontend | 1150 | 1150 | 1150 × 5 replicas |
| checkoutservice | 615 | 1500 | 1500 |
| recommendationservice | 1150 | 1250 | 2000 |
| productcatalogservice | 1535 | 1535 | 600 |
| cartservice | 1920 | 1200 | 1000 |
| currencyservice | 770 | 770 | 500 |
| shippingservice | 770 | 770 | 400 |
| adservice | 1150 | 800 | 600 |
| paymentservice | 155 | 155 | 150 |
| emailservice | 155 | 155 | 150 |
| redis-cart | 540 | 540 | 500 |
| **Deployment total** | **13360** | **13275** | **13150** |
```

Replacement mixes paragraph:

```markdown
## Which mixes to run under the agreed table

Order is fixed. Cool-off between holds is 360 s.

| Slot | Source mix | Counts (getproduct / postcheckout / getcart / postcart / emptycart) |
|---|---|---|
| run30 | 6 | 340 / 100 / 240 / 10 / 10 |
| run31 | 7 | 380 / 100 / 270 / 20 / 20 |
| run32 | 10 | 325 / 80 / 100 / 100 / 5 |
| run33 | 26 | 325 / 100 / 100 / 100 / 5 |
| run34 | 12 | 100 / 150 / 100 / 100 / 5 |
```

Leave the rest of that guide in place. Do not delete the paper or dispense columns.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python experiments/test_topfull_cpu_quotas.py -v`

Expected: PASS, including the existing quota tests.

- [ ] **Step 5: Commit**

```powershell
git add experiments/configs/scenario_2_baseline_no_topfull.yaml experiments/test_topfull_cpu_quotas.py "Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md"
git commit -m @"
test: lock the both-off spread CPU table at 13150m

"@
```

---

### Task 2: Skip paper CPU reconcile when the YAML asks

**Files:**
- Modify: `experiments/run_scenario.py` (the reconcile call near the start of `main`, and the reconcile call in the `finally` block)
- Modify: `experiments/test_run_scenario.py`
- Test: `experiments/test_run_scenario.py`

**Interfaces:**
- Consumes: `reconcile_paper_cpu_limits(cfg, wait: bool) -> None`
- Produces: `paper_cpu_reconcile_enabled(cfg) -> bool` and `reconcile_paper_cpu_limits_if_enabled(cfg, wait: bool = True) -> None`. `main` calls the wrapper at both existing reconcile sites.

- [ ] **Step 1: Write the failing test**

Append to `experiments/test_run_scenario.py`:

```python
class TestPaperCpuReconcileFlag(unittest.TestCase):
    def test_missing_key_stays_on(self):
        self.assertTrue(run_scenario.paper_cpu_reconcile_enabled({}))

    def test_false_skips_the_live_patch(self):
        calls = []

        def fake_reconcile(cfg, wait=True):
            calls.append(wait)

        with mock.patch.object(run_scenario, "reconcile_paper_cpu_limits", fake_reconcile), \
             mock.patch.object(run_scenario, "step", lambda *a, **k: None):
            run_scenario.reconcile_paper_cpu_limits_if_enabled(
                {"paper_cpu_reconcile": False}, wait=True
            )
        self.assertEqual(calls, [])

    def test_true_calls_through(self):
        calls = []

        def fake_reconcile(cfg, wait=True):
            calls.append(wait)

        with mock.patch.object(run_scenario, "reconcile_paper_cpu_limits", fake_reconcile), \
             mock.patch.object(run_scenario, "step", lambda *a, **k: None):
            run_scenario.reconcile_paper_cpu_limits_if_enabled({}, wait=False)
        self.assertEqual(calls, [False])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python experiments/test_run_scenario.py TestPaperCpuReconcileFlag -v`

Expected: FAIL with `AttributeError: paper_cpu_reconcile_enabled`.

- [ ] **Step 3: Write the wrapper and use it at both call sites**

Add next to `reconcile_paper_cpu_limits` in `experiments/run_scenario.py`:

```python
def paper_cpu_reconcile_enabled(cfg: dict) -> bool:
    """Default true. The CPU-spread series sets false so a 5-replica
    frontend is not combined with the paper backend table mid-run."""
    return bool(cfg.get("paper_cpu_reconcile", True))


def reconcile_paper_cpu_limits_if_enabled(cfg: dict, wait: bool = True) -> None:
    if not paper_cpu_reconcile_enabled(cfg):
        step("paper_cpu_reconcile is false; leaving live CPU limits unchanged")
        return
    reconcile_paper_cpu_limits(cfg, wait=wait)
```

In `main`, replace:

```python
        has_constraints = bool(cfg.get("scale_constraints"))
        reconcile_paper_cpu_limits(cfg, wait=not has_constraints)
```

with:

```python
        has_constraints = bool(cfg.get("scale_constraints"))
        reconcile_paper_cpu_limits_if_enabled(cfg, wait=not has_constraints)
```

In the `finally` block, replace:

```python
        reconcile_paper_cpu_limits(cfg, wait=False)
```

with:

```python
        reconcile_paper_cpu_limits_if_enabled(cfg, wait=False)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python experiments/test_run_scenario.py TestPaperCpuReconcileFlag -v`

Expected: PASS. Then run `python experiments/test_run_scenario.py -v` and expect the existing suite to pass.

- [ ] **Step 5: Commit**

```powershell
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m @"
feat: allow a scenario to skip the paper CPU reconcile

"@
```

---

### Task 3: Do not roll a deployment whose CPU is already the target

**Files:**
- Modify: `experiments/run_scenario.py` (`apply_constraints`, the `cpu_limit` branch)
- Modify: `experiments/test_run_scenario.py`
- Test: `experiments/test_run_scenario.py`

**Interfaces:**
- Consumes: `cpu_limit_millicores_for`, `kubectl_cpu_quantity`
- Produces: `cpu_resources_already_set(resources_json: str, cpu_quantity: str) -> bool`. When it returns true, `apply_constraints` does not call `kubectl patch` and does not append a restore record.

- [ ] **Step 1: Write the failing test**

Append to `experiments/test_run_scenario.py`:

```python
class TestCpuPatchSkip(unittest.TestCase):
    def _cfg(self):
        return {
            "infra": {"master_ssh_host": "topfull-master"},
            "scale_constraints": [{
                "deployment": "checkoutservice",
                "namespace": "default",
                "method": "cpu_limit",
                "cpu_limit_millicores": 1500,
                "container": "server",
            }],
        }

    def test_parser_accepts_kubectl_json(self):
        raw = '{"limits":{"cpu":"1500m","memory":"128Mi"},"requests":{"cpu":"1500m"}}'
        self.assertTrue(run_scenario.cpu_resources_already_set(raw, "1500m"))
        self.assertFalse(run_scenario.cpu_resources_already_set(raw, "615m"))

    def test_patch_skipped_when_request_and_limit_match(self):
        raw = '{"limits":{"cpu":"1500m"},"requests":{"cpu":"1500m"}}'
        cmds = []

        def fake_ssh(host, cmd, check=True):
            cmds.append(cmd)
            return SimpleNamespace(stdout=raw, returncode=0)

        with mock.patch.object(run_scenario, "ssh", fake_ssh), \
             mock.patch.object(run_scenario, "banner", lambda *a, **k: None), \
             mock.patch.object(run_scenario, "step", lambda *a, **k: None), \
             mock.patch.object(run_scenario, "wait_with_progress", lambda *a, **k: None):
            records = run_scenario.apply_constraints(self._cfg())
        self.assertEqual(records, [])
        self.assertFalse(any("kubectl patch" in c for c in cmds))

    def test_patch_sent_when_limit_differs(self):
        raw = '{"limits":{"cpu":"615m"},"requests":{"cpu":"615m"}}'
        cmds = []

        def fake_ssh(host, cmd, check=True):
            cmds.append(cmd)
            return SimpleNamespace(stdout=raw, returncode=0)

        with mock.patch.object(run_scenario, "ssh", fake_ssh), \
             mock.patch.object(run_scenario, "banner", lambda *a, **k: None), \
             mock.patch.object(run_scenario, "step", lambda *a, **k: None), \
             mock.patch.object(run_scenario, "wait_with_progress", lambda *a, **k: None):
            records = run_scenario.apply_constraints(self._cfg())
        self.assertEqual(len(records), 1)
        self.assertTrue(any("kubectl patch" in c and "1500m" in c for c in cmds))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python experiments/test_run_scenario.py TestCpuPatchSkip -v`

Expected: FAIL with `AttributeError: cpu_resources_already_set`.

- [ ] **Step 3: Implement the skip**

Add in `experiments/run_scenario.py`:

```python
def cpu_resources_already_set(resources_json: str, cpu_quantity: str) -> bool:
    text = (resources_json or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1]
    try:
        resources = json.loads(text or "{}")
    except json.JSONDecodeError:
        return False
    if not isinstance(resources, dict):
        return False
    limits = resources.get("limits") or {}
    requests = resources.get("requests") or {}
    return limits.get("cpu") == cpu_quantity and requests.get("cpu") == cpu_quantity
```

In the `cpu_limit` branch of `apply_constraints`, after `original_resources = r.stdout.strip() or "{}"` and after `cpu_limit` is computed, insert:

```python
            if cpu_resources_already_set(original_resources, cpu_limit):
                step(f"{dep}/{container} already at {cpu_limit}; skipping patch")
                continue
```

Leave the patch, the rollout status, and the restore-record append on the path where the limit differs.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python experiments/test_run_scenario.py TestCpuPatchSkip -v`

Expected: PASS. Then run `python experiments/test_run_scenario.py -v` and expect the existing suite to pass.

- [ ] **Step 5: Commit**

```powershell
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m @"
fix: skip a CPU constraint patch when the deployment is already there

"@
```

---

### Task 4: All-service (a)/(b)/(c) scorer

**Files:**
- Create: `experiments/s2_both_off_abc.py`
- Create: `experiments/test_s2_both_off_abc.py`
- Test: `experiments/test_s2_both_off_abc.py`

**Interfaces:**
- Consumes: `service_inbound.csv` columns `service,total,5xx,resets`; `topfull_detect.csv` columns `service,overloaded`; `service_edges.csv` columns `caller,target,retry`; `topfull_throttle.csv` column `threshold`; `resource_usage.csv` columns `service,cpu_millicores`.
- Produces: `score_run(run_dir: Path) -> dict` with keys `inbound`, `overloaded`, `retry_by_target`, `retry_by_edge`, `layer_a_admitting_rows`, `cpu_mean_max`. `main(argv)` prints one markdown section per directory.

- [ ] **Step 1: Write the failing test**

Create `experiments/test_s2_both_off_abc.py`:

```python
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s2_both_off_abc as abc


class TestRejectionStreak(unittest.TestCase):
    def test_streak_breaks_on_a_cool_sample(self):
        # cumulative counters. Two high samples, one cool, one high.
        rows = [
            {"total": 0, "5xx": 0, "resets": 0},
            {"total": 10, "5xx": 0, "resets": 4},   # 0.40 high
            {"total": 20, "5xx": 0, "resets": 8},   # 0.40 high
            {"total": 30, "5xx": 0, "resets": 8},   # 0.00 cool, breaks
            {"total": 40, "5xx": 0, "resets": 12},  # 0.40 high
        ]
        streak, high, samples, frac = abc.rejection_streak(rows)
        self.assertEqual(streak, 2)
        self.assertEqual(high, 3)
        self.assertEqual(samples, 4)
        self.assertAlmostEqual(frac, 12 / 40)

    def test_negative_delta_breaks_and_is_not_counted(self):
        rows = [
            {"total": 100, "5xx": 0, "resets": 50},
            {"total": 10, "5xx": 0, "resets": 4},  # counter restart
            {"total": 20, "5xx": 0, "resets": 8},  # 0.40
        ]
        streak, high, samples, frac = abc.rejection_streak(rows)
        self.assertEqual(streak, 1)
        self.assertEqual(high, 1)
        self.assertAlmostEqual(frac, 4 / 10)


class TestRetryAndDetect(unittest.TestCase):
    def test_positive_retry_deltas_group_by_target(self):
        edges = [
            {"caller": "frontend", "target": "checkoutservice", "retry": 0},
            {"caller": "frontend", "target": "checkoutservice", "retry": 10},
            {"caller": "frontend", "target": "checkoutservice", "retry": 10},
            {"caller": "frontend", "target": "recommendationservice", "retry": 0},
            {"caller": "frontend", "target": "recommendationservice", "retry": 5},
        ]
        by_edge, by_target = abc.retry_deltas(edges)
        self.assertEqual(by_edge["frontend->checkoutservice"], 10)
        self.assertEqual(by_target["recommendationservice"], 5)

    def test_overloaded_share(self):
        ticks, hot, share = abc.overloaded_fraction([0, 1, 1, 0])
        self.assertEqual((ticks, hot), (4, 2))
        self.assertAlmostEqual(share, 0.5)


class TestScoreRun(unittest.TestCase):
    def test_reads_the_five_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "service_inbound.csv",
                   ["timestamp", "service", "total", "2xx", "4xx", "5xx", "resets"],
                   [
                       ["t0", "checkoutservice", "0", "0", "0", "0", "0"],
                       ["t1", "checkoutservice", "10", "6", "0", "0", "4"],
                   ])
            _write(root / "topfull_detect.csv",
                   ["timestamp", "service", "cadvisor_cpu", "quota", "alpha", "utilization", "overloaded"],
                   [
                       ["t0", "checkoutservice", "1", "1500", "0.8", "0.9", "1"],
                       ["t1", "checkoutservice", "1", "1500", "0.8", "0.1", "0"],
                   ])
            _write(root / "service_edges.csv",
                   ["timestamp", "caller", "target", "total", "2xx", "4xx", "5xx", "retry"],
                   [["t0", "frontend", "checkoutservice", "0", "0", "0", "0", "0"],
                    ["t1", "frontend", "checkoutservice", "10", "6", "0", "0", "3"]])
            _write(root / "topfull_throttle.csv",
                   ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"],
                   [["t0", "postcheckout", "0", "0", "0", "0"],
                    ["t1", "postcheckout", "10000", "1", "1", "1"],
                    ["t2", "postcheckout", "40", "1", "1", "1"]])
            _write(root / "resource_usage.csv",
                   ["timestamp", "service", "cpu_millicores", "memory_working_set_bytes", "replica_count"],
                   [["t0", "checkoutservice", "100", "1", "1"],
                    ["t1", "checkoutservice", "300", "1", "1"]])
            got = abc.score_run(root)
        self.assertEqual(got["inbound"]["checkoutservice"]["streak"], 1)
        self.assertEqual(got["overloaded"]["checkoutservice"]["overloaded_ticks"], 1)
        self.assertEqual(got["retry_by_target"]["checkoutservice"], 3)
        self.assertEqual(got["layer_a_admitting_rows"], 1)
        self.assertEqual(got["cpu_mean_max"]["checkoutservice"], (200.0, 300.0))


def _write(path: Path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python experiments/test_s2_both_off_abc.py -v`

Expected: FAIL with `ModuleNotFoundError: s2_both_off_abc`.

- [ ] **Step 3: Implement the scorer**

Create `experiments/s2_both_off_abc.py`:

```python
"""Score one both-off run directory the way
Guides and Info/2026-09-24-s2-both-off-abc-reading.md defines (a)/(b)/(c).

(a) longest consecutive inbound samples with (d5xx + dresets) / dtotal > 0.20
(b) share of topfull_detect.csv rows with overloaded == 1
(c) sum of positive service_edges.csv retry increments per caller->target

Also reports Layer A rows whose threshold is neither 0 nor 10000, and
per-service CPU mean/max from resource_usage.csv. Prints markdown.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path


HIGH = 0.20


def _num(row: dict, key: str) -> float:
    raw = row.get(key, "")
    if raw is None or raw == "":
        return 0.0
    return float(raw)


def rejection_streak(rows: list[dict]) -> tuple[int, int, int, float]:
    """Cumulative counters, already time-sorted for one service.

    Returns (longest_streak, high_samples, scored_samples, failure_fraction).
    A non-positive total delta scores as not-high and breaks the streak.
    Negative counter jumps are not added into the fraction.
    """
    longest = 0
    current = 0
    high = 0
    scored = 0
    fail_num = 0.0
    fail_den = 0.0
    prev = None
    for row in rows:
        total = _num(row, "total")
        failed = _num(row, "5xx") + _num(row, "resets")
        if prev is None:
            prev = (total, failed)
            continue
        d_total = total - prev[0]
        d_fail = failed - prev[1]
        prev = (total, failed)
        scored += 1
        is_high = d_total > 0 and (d_fail / d_total) > HIGH
        if d_total > 0 and d_fail > 0:
            fail_num += d_fail
            fail_den += d_total
        elif d_total > 0:
            fail_den += d_total
        if is_high:
            high += 1
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    fraction = (fail_num / fail_den) if fail_den else 0.0
    return longest, high, scored, fraction


def overloaded_fraction(flags: list[int]) -> tuple[int, int, float]:
    ticks = len(flags)
    hot = sum(1 for flag in flags if int(flag) == 1)
    share = (hot / ticks) if ticks else 0.0
    return ticks, hot, share


def retry_deltas(edges: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in edges:
        grouped[(row.get("caller", ""), row.get("target", ""))].append(_num(row, "retry"))
    by_edge: dict[str, int] = {}
    by_target: dict[str, int] = defaultdict(int)
    for (caller, target), values in grouped.items():
        delta = 0
        prev = None
        for value in values:
            if prev is not None and value > prev:
                delta += int(value - prev)
            prev = value
        key = f"{caller}->{target}"
        by_edge[key] = delta
        by_target[target] += delta
    return dict(by_edge), dict(by_target)


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def score_run(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    inbound_rows: dict[str, list[dict]] = defaultdict(list)
    for row in _rows(run_dir / "service_inbound.csv"):
        inbound_rows[row["service"]].append(row)
    inbound = {}
    for service, rows in inbound_rows.items():
        streak, high, scored, frac = rejection_streak(rows)
        inbound[service] = {
            "streak": streak,
            "high_samples": high,
            "samples": scored,
            "failure_fraction": frac,
        }

    detect_flags: dict[str, list[int]] = defaultdict(list)
    for row in _rows(run_dir / "topfull_detect.csv"):
        detect_flags[row["service"]].append(int(float(row.get("overloaded") or 0)))
    overloaded = {}
    for service, flags in detect_flags.items():
        ticks, hot, share = overloaded_fraction(flags)
        overloaded[service] = {
            "ticks": ticks,
            "overloaded_ticks": hot,
            "share": share,
        }

    by_edge, by_target = retry_deltas(_rows(run_dir / "service_edges.csv"))
    admitting = 0
    for row in _rows(run_dir / "topfull_throttle.csv"):
        threshold = int(float(row.get("threshold") or 0))
        if threshold not in (0, 10000):
            admitting += 1

    cpu: dict[str, list[float]] = defaultdict(list)
    for row in _rows(run_dir / "resource_usage.csv"):
        cpu[row["service"]].append(_num(row, "cpu_millicores"))
    cpu_mean_max = {
        service: (sum(values) / len(values), max(values))
        for service, values in cpu.items()
        if values
    }
    return {
        "inbound": inbound,
        "overloaded": overloaded,
        "retry_by_edge": by_edge,
        "retry_by_target": by_target,
        "layer_a_admitting_rows": admitting,
        "cpu_mean_max": cpu_mean_max,
    }


def _md(scored: dict) -> str:
    lines = ["| Service | streak / high | failure | overloaded | CPU mean / max | retry |",
             "|---|---:|---:|---:|---:|---:|"]
    names = sorted(set(scored["inbound"]) | set(scored["overloaded"]) | set(scored["cpu_mean_max"]) | set(scored["retry_by_target"]))
    for name in names:
        inbound = scored["inbound"].get(name, {})
        over = scored["overloaded"].get(name, {})
        cpu = scored["cpu_mean_max"].get(name)
        streak = inbound.get("streak", 0)
        high = inbound.get("high_samples", 0)
        frac = inbound.get("failure_fraction", 0.0)
        share = over.get("share", 0.0)
        hot = over.get("overloaded_ticks", 0)
        ticks = over.get("ticks", 0)
        cpu_cell = "" if cpu is None else f"{cpu[0]:.0f} / {cpu[1]:.0f}"
        lines.append(
            f"| {name} | {streak} / {high} | {frac:.3f} | {hot}/{ticks} ({share:.1%}) | {cpu_cell} | {scored['retry_by_target'].get(name, 0)} |"
        )
    lines.append("")
    lines.append(f"Layer A admitting rows (threshold not 0 or 10000): {scored['layer_a_admitting_rows']}")
    nonzero = [(k, v) for k, v in scored["retry_by_edge"].items() if v]
    nonzero.sort(key=lambda item: item[1], reverse=True)
    lines.append("Retry edges: " + ", ".join(f"{k} {v}" for k, v in nonzero[:12]))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python experiments/s2_both_off_abc.py <run_dir> [...]", file=sys.stderr)
        return 2
    for raw in argv[1:]:
        path = Path(raw)
        print(f"## {path.name}")
        print()
        print(_md(score_run(path)))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python experiments/test_s2_both_off_abc.py -v`

Expected: PASS. The failure-fraction assertion on the restart case uses only the post-restart positive deltas (4/10).

- [ ] **Step 5: Commit**

```powershell
git add experiments/s2_both_off_abc.py experiments/test_s2_both_off_abc.py
git commit -m @"
feat: score both-off holds with the (a)/(b)/(c) reading

"@
```

---

### Task 5: Apply the table at 4 replicas, then pin frontend at 5

**Files:**
- Modify: none. This task only changes the live cluster.

**Interfaces:**
- Consumes: the YAML from Task 1 (`paper_cpu_reconcile: false`, the ten constraints) and `run_scenario.apply_constraints`.
- Produces: live CPU limits equal to the agreed table, frontend HPA `minReplicas=maxReplicas=5`, catalog HPA `maxReplicas=1`, frontend sidecar request left at 100 m with no CPU limit, zero Pending pods. Run30 has not started.

- [ ] **Step 1: Confirm the cluster is idle and frontend is still at most 4**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get hpa -n default; kubectl get deploy frontend -n default -o jsonpath='{.status.readyReplicas}'"
```

Expected: nodes Ready, no experiment tmux sessions required yet, HPA names `frontend-hpa` and `productcatalogservice-hpa`, frontend ready replicas ≤ 4. If ready replicas are already 5, patch frontend HPA back to `minReplicas: 1`, `maxReplicas: 4` and wait until ready replicas are ≤ 4 before the CPU apply. Paper backends plus 5 frontend replicas do not fit the node.

- [ ] **Step 2: Apply the spread CPU table while frontend is at 4**

```powershell
python -c "import sys; sys.path.insert(0,'experiments'); import yaml, run_scenario; cfg=yaml.safe_load(open(r'experiments/configs/scenario_2_baseline_no_topfull.yaml',encoding='utf-8')); run_scenario.apply_constraints(cfg)"
```

Expected: ten patch lines, or skip lines where a service is already at the target. This command does not start Locust and does not reconcile paper CPU.

- [ ] **Step 3: Check the live limits before adding the fifth pod**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,LIMIT:.spec.template.spec.containers[0].resources.limits.cpu,REQ:.spec.template.spec.containers[0].resources.requests.cpu --no-headers"
```

Expected millicores: checkoutservice 1500m, recommendationservice 2000m, productcatalogservice 600m, cartservice 1000m, currencyservice 500m, shippingservice 400m, adservice 600m, paymentservice 150m, emailservice 150m, redis-cart 500m, frontend 1150m. Stop if any differ.

- [ ] **Step 4: Leave the sidecar request at 100 m, pin frontend HPA, and cap catalog HPA**

```powershell
@'
kubectl patch deployment frontend -n default --type json -p '[{"op":"remove","path":"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit"}]' || true
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":5,"maxReplicas":5}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"maxReplicas":1}}'
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

PowerShell sends this here-string to remote bash unchanged. Do not set `proxyCPU` to 90 m. The `remove` of `proxyCPULimit` may print an error when the annotation is already absent. `|| true` keeps the HPA patches running. Confirm the request is still 100 m:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get deploy frontend -n default -o jsonpath='{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPU}'"
```

Expected output: `100m`.

- [ ] **Step 5: Wait until 5 frontend pods are Ready and nothing is Pending**

```powershell
@'
kubectl rollout status deployment/frontend -n default --timeout=180s
echo READY=$(kubectl get deploy frontend -n default -o jsonpath='{.status.readyReplicas}')
kubectl get pods -n default --field-selector=status.phase=Pending
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Expected: `READY=5` and no Pending pods. If a pod is still Pending after 180 s, do not start run30. Patch frontend HPA back to min 1 / max 4, set `proxyCPU` back to `100m`, call `run_scenario.reconcile_paper_cpu_limits` with a tiny cfg whose `infra.master_ssh_host` is `topfull-master`, and stop this plan.

- [ ] **Step 6: Cool off 360 s before the first hold**

```powershell
Start-Sleep -Seconds 360
```

Expected: the command returns after 360 seconds. Do not start Locust during this sleep.

---

### Task 6: Hold run30, mix 6

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (already mix 6 / run30 from Task 1)
- Pulls into: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run30/`

**Interfaces:**
- Consumes: the pinned cluster from Task 5.
- Produces: a pulled run30 folder that passes the gate below. The cluster stays on the spread table and at 5 frontend replicas.

- [ ] **Step 1: Clear stale runner scripts and launch**

`run_scenario.py` blocks for about 15 minutes. Wait at least 20 minutes for the command.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Expected log lines: `paper_cpu_reconcile is false`, ten `already at` skip lines (or a patch only if Task 5 missed one service), `TopFull RL: OFF`, `RetryGuard: OFF`, user counts 340/100/240/10/10, folder `baseline_no_topfull_sustained_overload_run30`.

- [ ] **Step 2: Pull**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

- [ ] **Step 3: Gate**

```powershell
python -c @"
import csv, json
from pathlib import Path
p = Path(r'experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run30')
cap = json.loads((p/'service_capacity.json').read_text(encoding='utf-8'))
expect = {'frontend':1150,'checkoutservice':1500,'recommendationservice':2000,'productcatalogservice':600,'cartservice':1000,'currencyservice':500,'shippingservice':400,'adservice':600,'paymentservice':150,'emailservice':150,'redis-cart':500}
for name, millis in expect.items():
    assert cap[name]['cpu_limit_millicores']==millis, (name, cap[name])
assert cap['frontend']['replica_count']==5
reps=set()
with (p/'resource_usage.csv').open(encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['service']=='frontend':
            reps.add(int(float(row['replica_count'])))
assert reps=={5}, reps
need = ['service_inbound.csv','service_edges.csv','topfull_detect.csv','resource_usage.csv','topfull_throttle.csv','total.csv']
missing = [n for n in need if not (p/n).exists()]
assert not missing, missing
rows = sum(1 for _ in (p/'total.csv').open(encoding='utf-8')) - 1
assert rows >= 500, rows
print('capacity ok', reps, 'locust rows', rows)
"@
```

Expected: `capacity ok` and locust rows at least 500. `total.csv` is the Locust series (there is no `*_stats_history.csv` in these folders). If any check fails, stop. Do not edit the YAML toward run31. Continue at Task 11.

- [ ] **Step 4: Cool off 360 s**

```powershell
Start-Sleep -Seconds 360
```

---

### Task 7: Hold run31, mix 7

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (`run_number`, `log_folder`, `description`, `locust.user_counts` only)
- Pulls into: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run31/`

**Interfaces:**
- Consumes: spread CPU and 5 frontend replicas still in place after run30.
- Produces: pulled run31 passing the same gate with this folder name.

- [ ] **Step 1: Point the YAML at mix 7 / run31**

Set `run_number: 31`, `log_folder: baseline_no_topfull_sustained_overload_run31`, description to mix 7, and:

```yaml
  user_counts:
    getproduct:   380
    postcheckout: 100
    getcart:      270
    postcart:     20
    emptycart:    20
```

Do not change `scale_constraints`, `paper_cpu_reconcile`, or `spawn_rate`.

- [ ] **Step 2: Clear stale scripts and launch**

`run_scenario.py` blocks for about 15 minutes. Wait at least 20 minutes.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Expected counts 380/100/270/20/20 and skip lines for the CPU patches.

- [ ] **Step 3: Pull and gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python -c @"
import csv, json
from pathlib import Path
p = Path(r'experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run31')
cap = json.loads((p/'service_capacity.json').read_text(encoding='utf-8'))
expect = {'frontend':1150,'checkoutservice':1500,'recommendationservice':2000,'productcatalogservice':600,'cartservice':1000,'currencyservice':500,'shippingservice':400,'adservice':600,'paymentservice':150,'emailservice':150,'redis-cart':500}
for name, millis in expect.items():
    assert cap[name]['cpu_limit_millicores']==millis, (name, cap[name])
assert cap['frontend']['replica_count']==5
reps=set()
with (p/'resource_usage.csv').open(encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['service']=='frontend':
            reps.add(int(float(row['replica_count'])))
assert reps=={5}, reps
need = ['service_inbound.csv','service_edges.csv','topfull_detect.csv','resource_usage.csv','topfull_throttle.csv','total.csv']
missing = [n for n in need if not (p/n).exists()]
assert not missing, missing
rows = sum(1 for _ in (p/'total.csv').open(encoding='utf-8')) - 1
assert rows >= 500, rows
print('capacity ok', reps, 'locust rows', rows)
"@
```

Expected: `capacity ok` and locust rows at least 500. On failure, stop and go to Task 11.

- [ ] **Step 4: Cool off 360 s**

```powershell
Start-Sleep -Seconds 360
```

---

### Task 8: Hold run32, mix 10

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (counts and slot only)
- Pulls into: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run32/`

**Interfaces:**
- Consumes: the still-pinned cluster.
- Produces: pulled run32 passing the gate.

- [ ] **Step 1: Point the YAML at mix 10 / run32**

`run_number: 32`, `log_folder: baseline_no_topfull_sustained_overload_run32`, counts:

```yaml
  user_counts:
    getproduct:   325
    postcheckout: 80
    getcart:      100
    postcart:     100
    emptycart:    5
```

- [ ] **Step 2: Clear stale scripts and launch**

`run_scenario.py` blocks for about 15 minutes. Wait at least 20 minutes.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Expected counts 325/80/100/100/5.

- [ ] **Step 3: Pull and gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python -c @"
import csv, json
from pathlib import Path
p = Path(r'experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run32')
cap = json.loads((p/'service_capacity.json').read_text(encoding='utf-8'))
expect = {'frontend':1150,'checkoutservice':1500,'recommendationservice':2000,'productcatalogservice':600,'cartservice':1000,'currencyservice':500,'shippingservice':400,'adservice':600,'paymentservice':150,'emailservice':150,'redis-cart':500}
for name, millis in expect.items():
    assert cap[name]['cpu_limit_millicores']==millis, (name, cap[name])
assert cap['frontend']['replica_count']==5
reps=set()
with (p/'resource_usage.csv').open(encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['service']=='frontend':
            reps.add(int(float(row['replica_count'])))
assert reps=={5}, reps
need = ['service_inbound.csv','service_edges.csv','topfull_detect.csv','resource_usage.csv','topfull_throttle.csv','total.csv']
missing = [n for n in need if not (p/n).exists()]
assert not missing, missing
rows = sum(1 for _ in (p/'total.csv').open(encoding='utf-8')) - 1
assert rows >= 500, rows
print('capacity ok', reps, 'locust rows', rows)
"@
```

Expected: `capacity ok` and locust rows at least 500. On failure, go to Task 11.

- [ ] **Step 4: Cool off 360 s**

```powershell
Start-Sleep -Seconds 360
```

---

### Task 9: Hold run33, mix 26

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (counts and slot only)
- Pulls into: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run33/`

**Interfaces:**
- Consumes: the still-pinned cluster.
- Produces: pulled run33 passing the gate.

- [ ] **Step 1: Point the YAML at mix 26 / run33**

`run_number: 33`, `log_folder: baseline_no_topfull_sustained_overload_run33`, counts:

```yaml
  user_counts:
    getproduct:   325
    postcheckout: 100
    getcart:      100
    postcart:     100
    emptycart:    5
```

- [ ] **Step 2: Clear stale scripts and launch**

`run_scenario.py` blocks for about 15 minutes. Wait at least 20 minutes.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Expected counts 325/100/100/100/5.

- [ ] **Step 3: Pull and gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python -c @"
import csv, json
from pathlib import Path
p = Path(r'experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run33')
cap = json.loads((p/'service_capacity.json').read_text(encoding='utf-8'))
expect = {'frontend':1150,'checkoutservice':1500,'recommendationservice':2000,'productcatalogservice':600,'cartservice':1000,'currencyservice':500,'shippingservice':400,'adservice':600,'paymentservice':150,'emailservice':150,'redis-cart':500}
for name, millis in expect.items():
    assert cap[name]['cpu_limit_millicores']==millis, (name, cap[name])
assert cap['frontend']['replica_count']==5
reps=set()
with (p/'resource_usage.csv').open(encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['service']=='frontend':
            reps.add(int(float(row['replica_count'])))
assert reps=={5}, reps
need = ['service_inbound.csv','service_edges.csv','topfull_detect.csv','resource_usage.csv','topfull_throttle.csv','total.csv']
missing = [n for n in need if not (p/n).exists()]
assert not missing, missing
rows = sum(1 for _ in (p/'total.csv').open(encoding='utf-8')) - 1
assert rows >= 500, rows
print('capacity ok', reps, 'locust rows', rows)
"@
```

Expected: `capacity ok` and locust rows at least 500. On failure, go to Task 11.

- [ ] **Step 4: Cool off 360 s**

```powershell
Start-Sleep -Seconds 360
```

---

### Task 10: Hold run34, mix 12

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (counts and slot only)
- Pulls into: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run34/`

**Interfaces:**
- Consumes: the still-pinned cluster.
- Produces: pulled run34 passing the gate. No further cool-off. Task 11 restores the cluster.

- [ ] **Step 1: Point the YAML at mix 12 / run34**

`run_number: 34`, `log_folder: baseline_no_topfull_sustained_overload_run34`, counts:

```yaml
  user_counts:
    getproduct:   100
    postcheckout: 150
    getcart:      100
    postcart:     100
    emptycart:    5
```

- [ ] **Step 2: Clear stale scripts and launch**

`run_scenario.py` blocks for about 15 minutes. Wait at least 20 minutes.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Expected counts 100/150/100/100/5.

- [ ] **Step 3: Pull and gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python -c @"
import csv, json
from pathlib import Path
p = Path(r'experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run34')
cap = json.loads((p/'service_capacity.json').read_text(encoding='utf-8'))
expect = {'frontend':1150,'checkoutservice':1500,'recommendationservice':2000,'productcatalogservice':600,'cartservice':1000,'currencyservice':500,'shippingservice':400,'adservice':600,'paymentservice':150,'emailservice':150,'redis-cart':500}
for name, millis in expect.items():
    assert cap[name]['cpu_limit_millicores']==millis, (name, cap[name])
assert cap['frontend']['replica_count']==5
reps=set()
with (p/'resource_usage.csv').open(encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['service']=='frontend':
            reps.add(int(float(row['replica_count'])))
assert reps=={5}, reps
need = ['service_inbound.csv','service_edges.csv','topfull_detect.csv','resource_usage.csv','topfull_throttle.csv','total.csv']
missing = [n for n in need if not (p/n).exists()]
assert not missing, missing
rows = sum(1 for _ in (p/'total.csv').open(encoding='utf-8')) - 1
assert rows >= 500, rows
print('capacity ok', reps, 'locust rows', rows)
"@
```

Expected: `capacity ok` and locust rows at least 500. On failure, still do Task 11 so the cluster is not left at 5 replicas.

---

### Task 11: Restore paper CPU, HPA, and the YAML

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Modify: `experiments/test_topfull_cpu_quotas.py` (replace `TestBothOffSpreadYaml` with the restored-YAML test below)
- Test: `experiments/test_topfull_cpu_quotas.py`

**Interfaces:**
- Consumes: `reconcile_paper_cpu_limits(cfg, wait=True)`, which patches every service in `RECONCILE_SERVICES` to `PAPER_CPU_LIMIT_MILLICORES`.
- Produces: frontend HPA min 1 / max 4, catalog HPA max 2, sidecar `proxyCPU=100m` and no `proxyCPULimit`, live app CPU back on the paper table, YAML `run_number: 35` with `scale_constraints: []` and no `paper_cpu_reconcile: false`.

- [ ] **Step 1: Scale frontend down before restoring paper CPU**

```powershell
@'
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":4}}'
kubectl rollout status deployment/frontend -n default --timeout=180s
echo READY=$(kubectl get deploy frontend -n default -o jsonpath="{.status.readyReplicas}")
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Expected: `READY` is 4 or less. Do not restore paper CPU while it is still 5.

- [ ] **Step 2: Restore paper CPU, catalog HPA, and the sidecar**

```powershell
python -c "import sys; sys.path.insert(0,'experiments'); import run_scenario; run_scenario.reconcile_paper_cpu_limits({'infra':{'master_ssh_host':'topfull-master'}}, wait=True)"
@'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"maxReplicas":2}}'
kubectl patch deployment frontend -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"100m"}}}}}'
kubectl patch deployment frontend -n default --type json -p '[{"op":"remove","path":"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit"}]' || true
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Then repeat the limits column command from Task 5 Step 3. Expected paper millicores: frontend 1150m, checkoutservice 615m, recommendationservice 1150m, productcatalogservice 1535m, cartservice 1920m, currencyservice 770m, shippingservice 770m, adservice 1150m, paymentservice 155m, emailservice 155m, redis-cart 540m.

- [ ] **Step 3: Replace the YAML test so the suite matches the restored file**

Replace class `TestBothOffSpreadYaml` in `experiments/test_topfull_cpu_quotas.py` with:

```python
class TestBothOffYamlRestored(unittest.TestCase):
    def test_next_slot_is_paper_and_unused(self):
        import yaml
        from pathlib import Path

        path = Path(__file__).resolve().parent / "configs" / "scenario_2_baseline_no_topfull.yaml"
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertTrue(cfg.get("paper_cpu_reconcile", True))
        self.assertEqual(cfg.get("scale_constraints") or [], [])
        self.assertEqual(cfg["run_number"], 35)
        self.assertEqual(cfg["log_folder"], "baseline_no_topfull_sustained_overload_run35")
        self.assertIs(cfg["topfull_rl"]["enabled"], False)
        self.assertIs(cfg["retryguard"]["enabled"], False)
```

- [ ] **Step 4: Reset the YAML to the unused paper slot**

After all five holds, set `run_number: 35`, `log_folder: baseline_no_topfull_sustained_overload_run35`, delete the `paper_cpu_reconcile` key, set `scale_constraints: []`, and set the description to the unused run35 slot on the paper table. Leave `topfull_rl.enabled` and `retryguard.enabled` false. User counts may stay at the mix-12 values; the description must say the slot is unused. If the series stopped early, use the first slot that was never launched instead of 35, and change `TestBothOffYamlRestored` to assert that same number and folder.

- [ ] **Step 5: Run the test and commit**

Run: `python experiments/test_topfull_cpu_quotas.py -v; python experiments/test_run_scenario.py -v; python experiments/test_s2_both_off_abc.py -v`

Expected: all three PASS.

```powershell
git add experiments/configs/scenario_2_baseline_no_topfull.yaml experiments/test_topfull_cpu_quotas.py
git commit -m @"
chore: return the both-off YAML to paper CPU at run35

"@
```

Leave the VMs running.

---

### Task 12: Write the all-service (a)/(b)/(c) reading

**Files:**
- Create: `Guides and Info/2026-09-26-s2-cpu-spread-runs-30-34.md`
- Modify: `AGENTS.md` (section 4, one new done bullet and the next-free slot sentence)
- Test: `experiments/s2_both_off_abc.py` against the pulled folders and the five source folders

**Interfaces:**
- Consumes: `score_run` / the CLI from Task 4. Source folders are `baseline_no_topfull_sustained_overload_run6`, `run7`, `run10`, `run26`, and `run12` under `experiments/results/campaign_48/S2_sustained_overload/`. New folders are `run30` through `run34` in that same directory.
- Produces: the guide below. Every number in it comes from this script's stdout. Do not edit the source run folders.

- [ ] **Step 1: Score the five new holds and the five source holds with the same function**

```powershell
python experiments/s2_both_off_abc.py experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run30 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run31 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run32 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run33 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run34 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run6 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run7 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run10 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run26 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run12
```

Expected: one markdown section per folder, one row per service that appears in any of the three CSVs, plus the Layer A line and the retry-edge line. If a new folder is missing because its gate failed, score only the folders that exist and say which slots were not run.

- [ ] **Step 2: Write the guide**

Create `Guides and Info/2026-09-26-s2-cpu-spread-runs-30-34.md` with this structure and the numbers from Step 1 filled in:

1. Setup paragraph: 600 s, both controllers off, `spawn_rate` 50, frontend pinned at 5, catalog HPA max 1, sidecar request left at 100 m with no CPU limit, agreed CPU table, 360 s cool-off before run30 and between holds. Link [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md) and [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).
2. Slot table: run30 mix 6 `340/100/240/10/10`, run31 mix 7 `380/100/270/20/20`, run32 mix 10 `325/80/100/100/5`, run33 mix 26 `325/100/100/100/5`, run34 mix 12 `100/150/100/100/5`.
3. Three full-service tables, rows for frontend, checkoutservice, recommendationservice, paymentservice, emailservice, productcatalogservice, cartservice, currencyservice, shippingservice, adservice, and redis-cart, columns run30 through run34:
   - (a) `streak / high_samples`. Bold a cell when streak ≥ 30 and the service is one of the nine controlled services.
   - (b) `overloaded_ticks/ticks (share)`. Bold when share ≥ 0.5.
   - (c) retry delta by target, plus a second small table of every caller→target edge whose delta is at least 1.
4. CPU mean/max table for the same eleven services and five runs, from `cpu_mean_max`.
5. One short paragraph per new run. State the mix counts, which controlled services cleared streak ≥ 30, which cleared overloaded share ≥ 0.5, the largest retry edge, and the Layer A admitting-row count. Then the same three facts for the source folder as this same script scored it (run30 vs run6, run31 vs run7, run32 vs run10, run33 vs run26, run34 vs run12). If the script's source-run streak differs from an older guide, report the script's number and name the script. Do not add a conclusion beyond which bars cleared.
6. Related links to the source-mix guides and to this plan.

- [ ] **Step 3: Update AGENTS.md section 4**

Add one done bullet naming runs 30–34, the agreed table, frontend pinned at 5, the 360 s cool-offs, and the new guide. Set the both-off next-free slot to **run35**. Say HPAs were restored (frontend 1–4, catalog max 2, sidecar `proxyCPU` 100 m, limit unset) and the VMs were left running.

- [ ] **Step 4: Commit**

```powershell
git add "Guides and Info/2026-09-26-s2-cpu-spread-runs-30-34.md" AGENTS.md
git commit -m @"
docs: score the CPU-spread holds across every service

"@
```

Do not stop the VMs.
