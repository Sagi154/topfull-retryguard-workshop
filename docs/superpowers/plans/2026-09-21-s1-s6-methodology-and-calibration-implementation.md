# S1–S6 methodology rework + recalibration battery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement everything designed in [2026-09-21-s1-s6-methodology-and-calibration-design.md](../specs/2026-09-21-s1-s6-methodology-and-calibration-design.md) — the `cpu_limit_millicores` absolute bottleneck-cap mechanism, productcatalog HPA, the 5-run bottleneck-cap recalibration battery, the S1/S2/S6 empirical system-load calibration, and rewiring all 16 scenario YAMLs onto real numbers and the v2 loadgen launcher — closing tracker sections [§1](../specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md#1-fresh-calibration-pass-blocker-for-everything-else), [§2](../specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md#2-s1s6-scenario-methodology-rework-not-just-numbers), and [§3](../specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md#3-rewire-the-16-scenario-yamls).

**Architecture:** Two layers. (1) A pure-code layer (Tasks 1–4): a new absolute CPU-limit constraint kind in `topfull_cpu_quotas.py` + `run_scenario.py`, an HPA-managed-replica guard extended to `productcatalogservice`, and a new `productcatalogservice-hpa.yaml` manifest applied live. (2) A config + live-execution layer (Tasks 5–10): fix the 4 existing bottleneck-cap calibration YAMLs and the 6 S3/S4A/S4B scenario YAMLs onto the new mechanism, add a 5th "reference load" calibration YAML, run the 5-run bottleneck-cap battery live and re-freeze `capacity_frozen.json`, run the S1/S2/S6 empirical system-load calibration live (≤3 tries each), then rewrite all 16 scenario YAMLs with real numbers and the v2 launcher. Task 11 closes the loop on documentation (`RON-NEZER-BASE-MIGRATION.md`, `AGENTS.md`, the tracker).

**Tech Stack:** Python 3 (`unittest`), YAML scenario configs, `kubectl`/SSH via `run_scenario.py`'s existing `ssh()` wrapper, GCP VMs (`topfull-master`/`topfull-worker-1`/`topfull-load`).

## Global Constraints

- Never hardcode VM IPs — always use the SSH host aliases `topfull-master` / `topfull-worker-1` / `topfull-load` (`.cursor/rules/topfull-ssh.mdc`).
- Connect as `idozacharia` on all three VMs (see `AGENTS.md` §7).
- **VMs may be stopped** between sessions to save cost (`gcloud compute instances stop …` — someone stops them deliberately; they do not stop by themselves). Before any live `kubectl`/`ssh`/`run_scenario.py` work (Task 4 onward, and again before Task 8 if they were stopped after Task 4), check status; if `TERMINATED`, start all three, refresh ephemeral IPs in `~/.ssh/config` (CONNECT-VMS Step 3 start + Step 5 HostName update — **not** Step 4 key install, that is one-time), and wait for cluster health (`AGENTS.md` §4 "Live infra caveat"). Do not assume they are already running.
- Do not overwrite existing completed run folders — every YAML edit that changes `run_number`/`log_folder` must bump to the then-current next-free slot (check `AGENTS.md` §4/§6 immediately before running, since other sessions may have moved slots since this plan was written).
- Do not lower `SAT_5XX_FRACTION` (0.05) or `LOW_CONFIDENCE_SAT_TICKS` (10) in `estimate_service_mu.py`/`capacity_frozen.py` — established gates, not tunable per this plan.
- `cluster_shape` must stay `topfull-worker-1=e2-standard-16` for any `capacity_frozen.py freeze` call to succeed (hard error otherwise, by design) — confirm with `gcloud compute instances describe topfull-worker-1 --zone=us-central1-a --format='value(machineType)'` before Task 8.
- 300s+ cool-off between every live run in the battery and the S1/S2/S6 calibration loop (matches the established precedent in `AGENTS.md` §4's calibration history).
- Do not reuse the pre-migration `capacity_frozen.json` values (all four dated 2026-09-19, predate the Ron-Nezer migration) as anything other than *starting guesses* for the battery's `locust.user_counts` (design doc §2b/§2c).
- **Task 9 human gate:** after every S1/S2/S6 calibration try, stop and wait for explicit user approval before adjusting numbers or moving to the next try/scenario. The agent's metric checks are necessary but not sufficient — the user also judges whether the run matches what they had in mind for that scenario.

---

## Task 1: Absolute `cpu_limit_millicores` constraint kind in `topfull_cpu_quotas.py`

**Files:**
- Modify: `experiments/topfull_cpu_quotas.py`
- Test: `experiments/test_topfull_cpu_quotas.py`

**Interfaces:**
- Produces: `topfull_cpu_quotas.cpu_limit_millicores_for(constraint: dict) -> int` — resolves a `method: "cpu_limit"` constraint dict's absolute millicore value from either the new `cpu_limit_millicores` key (used directly) or the legacy `cpu_limit_fraction` key (relative to `paper_limit_for(deployment)`, existing behavior unchanged). Raises `ValueError` if both or neither key is present. Consumed by Task 2 (`run_scenario.py`) and by `validate_scale_constraints`/`effective_cpu_quotas` internally.

- [ ] **Step 1: Write the failing tests**

Add to `experiments/test_topfull_cpu_quotas.py`, inside `TestValidateScaleConstraints`:

```python
    def test_millicores_ok(self):
        q.validate_scale_constraints(
            [
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit_millicores": 50,
                    "container": "server",
                }
            ]
        )

    def test_millicores_and_fraction_together_is_error(self):
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit_fraction": 0.1,
                    "cpu_limit_millicores": 50,
                }
            ])

    def test_neither_millicores_nor_fraction_is_error(self):
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {"deployment": "checkoutservice", "method": "cpu_limit"}
            ])

    def test_unknown_service_millicores_is_error(self):
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {
                    "deployment": "not-a-boutique-service",
                    "method": "cpu_limit",
                    "cpu_limit_millicores": 50,
                }
            ])
```

Add a new test class at the end of the file, before `if __name__ == "__main__":`:

```python
class TestCpuLimitMillicoresFor(unittest.TestCase):
    def test_millicores_key_used_directly(self):
        got = q.cpu_limit_millicores_for(
            {"deployment": "checkoutservice", "cpu_limit_millicores": 50}
        )
        self.assertEqual(got, 50)

    def test_fraction_key_still_computed_from_paper_limit(self):
        got = q.cpu_limit_millicores_for(
            {"deployment": "checkoutservice", "cpu_limit_fraction": 0.1}
        )
        self.assertEqual(got, 61)  # int(615 * 0.1)

    def test_both_keys_is_error(self):
        with self.assertRaises(ValueError):
            q.cpu_limit_millicores_for({
                "deployment": "checkoutservice",
                "cpu_limit_fraction": 0.1,
                "cpu_limit_millicores": 50,
            })

    def test_neither_key_is_error(self):
        with self.assertRaises(ValueError):
            q.cpu_limit_millicores_for({"deployment": "checkoutservice"})
```

Update the existing `TestEffectiveCpuQuotas` class to also cover the millicores path:

```python
    def test_millicores_overwrite(self):
        got = q.effective_cpu_quotas(
            [
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit_millicores": 50,
                }
            ]
        )
        self.assertEqual(got["checkoutservice"], 50)
        self.assertEqual(got["productcatalogservice"], 1535)
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python experiments/test_topfull_cpu_quotas.py`
Expected: `AttributeError: module 'topfull_cpu_quotas' has no attribute 'cpu_limit_millicores_for'` (and related `ValueError`-not-raised failures for the `validate_scale_constraints` additions, since that function doesn't check for `cpu_limit_millicores` yet).

- [ ] **Step 3: Implement `cpu_limit_millicores_for` and wire it into `validate_scale_constraints`/`effective_cpu_quotas`**

In `experiments/topfull_cpu_quotas.py`, add this function right after `millicores_from_fraction` (currently ends at line 100):

```python
def cpu_limit_millicores_for(constraint: dict) -> int:
    """
    Resolve a `method: "cpu_limit"` constraint's absolute millicore value.

    Exactly one of `cpu_limit_millicores` (new, absolute — ADR-0006) or
    `cpu_limit_fraction` (legacy, relative to paper_limit_for(deployment))
    must be present.
    """
    has_millicores = "cpu_limit_millicores" in constraint
    has_fraction = "cpu_limit_fraction" in constraint
    if has_millicores and has_fraction:
        raise ValueError(
            "cpu_limit constraint cannot set both cpu_limit_millicores and "
            "cpu_limit_fraction - pick one"
        )
    if has_millicores:
        return int(constraint["cpu_limit_millicores"])
    if has_fraction:
        dep = constraint["deployment"]
        return millicores_from_fraction(
            paper_limit_for(dep), float(constraint["cpu_limit_fraction"])
        )
    raise ValueError(
        "cpu_limit constraint requires either cpu_limit_millicores or "
        "cpu_limit_fraction"
    )
```

Replace the body of `validate_scale_constraints`'s `method == "cpu_limit"` branch (currently):

```python
        if method != "cpu_limit":
            continue
        if "cpu_limit" in c:
            raise ValueError(
                "scale_constraints cpu_limit is removed; use cpu_limit_fraction"
            )
        if "cpu_limit_fraction" not in c:
            raise ValueError("cpu_limit constraint requires cpu_limit_fraction")
        dep = c.get("deployment")
        if dep not in known:
            raise ValueError(f"no paper quota for deployment {dep}")
        millicores_from_fraction(paper_limit_for(dep), float(c["cpu_limit_fraction"]))
```

with:

```python
        if method != "cpu_limit":
            continue
        if "cpu_limit" in c:
            raise ValueError(
                "scale_constraints cpu_limit is removed; use cpu_limit_fraction "
                "or cpu_limit_millicores"
            )
        dep = c.get("deployment")
        if dep not in known:
            raise ValueError(f"no paper quota for deployment {dep}")
        cpu_limit_millicores_for(c)
```

Replace the body of the `effective_cpu_quotas` loop (currently):

```python
    for c in constraints or []:
        if c.get("method") != "cpu_limit":
            continue
        dep = c["deployment"]
        out[dep] = millicores_from_fraction(
            paper_limit_for(dep), float(c["cpu_limit_fraction"])
        )
    return out
```

with:

```python
    for c in constraints or []:
        if c.get("method") != "cpu_limit":
            continue
        out[c["deployment"]] = cpu_limit_millicores_for(c)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_topfull_cpu_quotas.py`
Expected: `OK` — all tests (old and new) pass.

- [ ] **Step 5: Commit**

```bash
git add experiments/topfull_cpu_quotas.py experiments/test_topfull_cpu_quotas.py
git commit -m "feat: add absolute cpu_limit_millicores constraint kind (ADR-0006)"
```

---

## Task 2: Wire `cpu_limit_millicores` into `run_scenario.py`'s apply/dry-run paths

**Files:**
- Modify: `experiments/run_scenario.py`

**Interfaces:**
- Consumes: `topfull_cpu_quotas.cpu_limit_millicores_for(constraint: dict) -> int` (Task 1).

- [ ] **Step 1: Update `apply_constraints()`'s `cpu_limit` branch**

In `experiments/run_scenario.py`, find the `elif method == "cpu_limit":` branch inside `apply_constraints()` (currently lines 405–441):

```python
        elif method == "cpu_limit":
            frac = float(c["cpu_limit_fraction"])
            cpu_limit = topfull_cpu_quotas.kubectl_cpu_quantity(
                topfull_cpu_quotas.millicores_from_fraction(
                    topfull_cpu_quotas.paper_limit_for(dep), frac
                )
            )
            container = c.get("container", "server")
            # Capture full original resources so restore is exact (requests must
            # also drop: K8s requires request <= limit, and Boutique defaults
            # request 200m–500m which exceeds a 100m limit).
            r = ssh(master,
                    f"kubectl get deployment {dep} -n {ns} "
                    f"-o jsonpath='{{.spec.template.spec.containers[0].resources}}'")
            original_resources = r.stdout.strip() or "{}"
            step(
                f"Applying CPU limit {cpu_limit} "
                f"(fraction={frac}) to {dep}/{container} ({ns})"
            )
```

Replace with:

```python
        elif method == "cpu_limit":
            limit_millicores = topfull_cpu_quotas.cpu_limit_millicores_for(c)
            cpu_limit = topfull_cpu_quotas.kubectl_cpu_quantity(limit_millicores)
            container = c.get("container", "server")
            # Capture full original resources so restore is exact (requests must
            # also drop: K8s requires request <= limit, and Boutique defaults
            # request 200m–500m which exceeds a 100m limit).
            r = ssh(master,
                    f"kubectl get deployment {dep} -n {ns} "
                    f"-o jsonpath='{{.spec.template.spec.containers[0].resources}}'")
            original_resources = r.stdout.strip() or "{}"
            spec_desc = (
                f"millicores={limit_millicores}" if "cpu_limit_millicores" in c
                else f"fraction={c['cpu_limit_fraction']}"
            )
            step(
                f"Applying CPU limit {cpu_limit} "
                f"({spec_desc}) to {dep}/{container} ({ns})"
            )
```

- [ ] **Step 2: Update the dry-run print block**

Find this block in `run()` (currently lines 1256–1273):

```python
    if cfg.get("scale_constraints"):
        print(f"  Constraints:")
        for c in cfg["scale_constraints"]:
            method = c.get("method", "replicas")
            if method == "replicas":
                print(f"    {c['deployment']}: scale to {c['replicas']} replica(s)")
            elif method == "cpu_limit":
                frac = c.get("cpu_limit_fraction")
                qty = topfull_cpu_quotas.kubectl_cpu_quantity(
                    topfull_cpu_quotas.millicores_from_fraction(
                        topfull_cpu_quotas.paper_limit_for(c["deployment"]),
                        float(frac),
                    )
                )
                print(
                    f"    {c['deployment']}: cpu_limit_fraction={frac} "
                    f"({qty})"
                )
```

Replace the `elif method == "cpu_limit":` body with:

```python
            elif method == "cpu_limit":
                limit_millicores = topfull_cpu_quotas.cpu_limit_millicores_for(c)
                qty = topfull_cpu_quotas.kubectl_cpu_quantity(limit_millicores)
                spec_desc = (
                    f"cpu_limit_millicores={c['cpu_limit_millicores']}"
                    if "cpu_limit_millicores" in c
                    else f"cpu_limit_fraction={c['cpu_limit_fraction']}"
                )
                print(f"    {c['deployment']}: {spec_desc} ({qty})")
```

- [ ] **Step 3: Sanity-check with a dry run against an existing fraction-based YAML**

Run: `python -c "import sys; sys.path.insert(0,'experiments'); import run_scenario as r; cfg=r.yaml.safe_load(open('experiments/configs/scenario_3_baseline.yaml')); r.topfull_cpu_quotas.validate_scale_constraints(cfg.get('scale_constraints') or [])"`
Expected: no output, no exception (the existing `cpu_limit_fraction: 0.1` constraint in `scenario_3_baseline.yaml` still validates — confirms the refactor didn't break the legacy path before Task 5 rewrites this file).

- [ ] **Step 4: Commit**

```bash
git add experiments/run_scenario.py
git commit -m "feat: dispatch cpu_limit_millicores through run_scenario's apply/dry-run paths"
```

---

## Task 3: Extend the HPA-managed-replica guard to `productcatalogservice`

**Files:**
- Modify: `experiments/topfull_cpu_quotas.py`
- Test: `experiments/test_topfull_cpu_quotas.py`

**Interfaces:**
- Produces: `HPA_MANAGED_DEPLOYMENTS: frozenset[str]` (module-level constant, `{"frontend", "productcatalogservice"}`) — used by `validate_scale_constraints` and citable by future scenario-config docstrings.

- [ ] **Step 1: Write the failing test**

Add to `experiments/test_topfull_cpu_quotas.py`'s `TestValidateScaleConstraints` class:

```python
    def test_productcatalog_replicas_constraint_is_rejected(self):
        # HPA enabled on productcatalog (design doc decision 6 / ADR-0005) —
        # same reasoning as the frontend guard above.
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {"deployment": "productcatalogservice", "method": "replicas", "replicas": 1}
            ])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python experiments/test_topfull_cpu_quotas.py`
Expected: `FAIL` — `test_productcatalog_replicas_constraint_is_rejected` (no `ValueError` raised, since only `frontend` is currently guarded).

- [ ] **Step 3: Generalize the guard**

In `experiments/topfull_cpu_quotas.py`, add near the top (after `CONTAINER_NAME_OVERRIDES`, around line 62):

```python
# Ron-config regime: both of these services' replica counts are HPA-managed
# (frontend since the 2026-09-20 base migration; productcatalogservice since
# the 2026-09-21 methodology rework, ADR-0005) — a fixed `replicas`
# scale_constraint on either would fight the autoscaler.
HPA_MANAGED_DEPLOYMENTS = frozenset({"frontend", "productcatalogservice"})
```

In `validate_scale_constraints`, replace:

```python
        if method == "replicas" and c.get("deployment") == "frontend":
            raise ValueError(
                "scale_constraints cannot set replicas on frontend - its "
                "replica count is HPA-managed (minReplicas=1, maxReplicas=4, "
                "Ron-Nezer base migration); a fixed replicas constraint would "
                "fight the autoscaler"
            )
```

with:

```python
        if method == "replicas" and c.get("deployment") in HPA_MANAGED_DEPLOYMENTS:
            raise ValueError(
                f"scale_constraints cannot set replicas on {c['deployment']} - "
                "its replica count is HPA-managed; a fixed replicas constraint "
                "would fight the autoscaler"
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_topfull_cpu_quotas.py`
Expected: `OK` — including the pre-existing `test_frontend_replicas_constraint_is_rejected` (still passes — `frontend` is still in the set) and `test_other_services_replicas_constraint_is_still_allowed` (still passes — `checkoutservice` is not in the set).

- [ ] **Step 5: Commit**

```bash
git add experiments/topfull_cpu_quotas.py experiments/test_topfull_cpu_quotas.py
git commit -m "feat: guard productcatalogservice replicas constraint (HPA-managed, ADR-0005)"
```

---

## Task 4: Create and apply the productcatalog HPA manifest

**Files:**
- Create: `experiments/manifests/productcatalogservice-hpa.yaml`

**Pre-check:** confirm Tasks 1–3 are committed (the guard from Task 3 must exist before this HPA goes live, so a future scenario YAML can't accidentally fight it). This is the first live-cluster task — VMs must be running.

- [ ] **Step 0: Start VMs (if stopped), refresh SSH HostNames, wait for cluster health**

Check status first; only start if they are not already `RUNNING`. Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md) Step 3 (start) and Step 5 (refresh `HostName` in `~/.ssh/config`). Do **not** re-run Step 4 (key install) — that is a one-time setup.

```powershell
gcloud compute instances list --project=networks-workshop --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

If any of `topfull-master` / `topfull-worker-1` / `topfull-load` is `TERMINATED` or missing a `NAT_IP`:

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=networks-workshop
gcloud compute instances list --project=networks-workshop --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Update `HostName` in `$env:USERPROFILE\.ssh\config` for all three `Host topfull-*` blocks to the new IPs (ephemeral — they change on every stop/start). Then:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
ssh topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get hpa -n default"
```

Expected: `whoami` → `idozacharia`; 2 `Ready` nodes; Boutique pods coming up `2/2 Running` (may take a few minutes after start — wait and re-check, do not treat a brief API/kubeconfig delay as permanent failure; see `AGENTS.md` §4/§7). If SSH times out after start, re-check IPs / `HostName` before assuming a firewall issue.

- [ ] **Step 1: Confirm no productcatalog HPA exists yet**

```bash
ssh topfull-master "kubectl get hpa -n default"
```

Expected: only `frontend-hpa` listed (confirmed in `RON-NEZER-BASE-MIGRATION.md` §4: productcatalog HPA was deliberately deferred during the base migration).

- [ ] **Step 2: Write the manifest locally**

Create `experiments/manifests/productcatalogservice-hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: productcatalogservice-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: productcatalogservice
  minReplicas: 1
  maxReplicas: 2
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 85
```

This matches design doc §4/decision 6: `minReplicas: 1, maxReplicas: 2`, same 85% CPU-utilization target shape as `frontend-hpa.yaml`.

- [ ] **Step 3: Copy and apply it**

```bash
scp -o BatchMode=yes -o ControlMaster=no experiments/manifests/productcatalogservice-hpa.yaml topfull-master:/tmp/productcatalogservice-hpa.yaml
ssh topfull-master "kubectl apply -f /tmp/productcatalogservice-hpa.yaml"
```

Expected: `horizontalpodautoscaler.autoscaling/productcatalogservice-hpa created`.

- [ ] **Step 4: Verify**

```bash
ssh topfull-master "kubectl get hpa productcatalogservice-hpa -n default"
```

Expected: a row showing `MINPODS 1`, `MAXPODS 2`, `REPLICAS 1`, `TARGETS` a low single-digit percent under no load.

- [ ] **Step 5: Confirm no scenario YAML currently sets a `replicas` constraint on productcatalog** (would now fail preflight per Task 3's guard — this is intentional, but should not be a surprise mid-battery)

```bash
grep -rn "productcatalogservice" experiments/configs/*.yaml | grep -i replicas
```

Expected: no matches (S4A's `scale_constraints` only ever used `method: cpu_limit`, never `replicas` — confirmed by reading `scenario_4a_baseline.yaml` during design).

- [ ] **Step 6: Commit the manifest**

```bash
git add experiments/manifests/productcatalogservice-hpa.yaml
git commit -m "feat: add productcatalogservice HPA manifest (minReplicas=1, maxReplicas=2, ADR-0005)"
```

_The `kubectl apply` itself (Step 3) is a live-cluster action, not something this commit replays — re-running `kubectl apply -f experiments/manifests/productcatalogservice-hpa.yaml` from a future session is how you'd recreate it if the object were ever deleted._

---

## Task 5: Switch S3/S4A/S4B's `scale_constraints` to `cpu_limit_millicores: 50`

**Files:**
- Modify: `experiments/configs/scenario_3_baseline.yaml`
- Modify: `experiments/configs/scenario_3_retryguard.yaml`
- Modify: `experiments/configs/scenario_4a_baseline.yaml`
- Modify: `experiments/configs/scenario_4a_retryguard.yaml`
- Modify: `experiments/configs/scenario_4b_baseline.yaml`
- Modify: `experiments/configs/scenario_4b_retryguard.yaml`

**Pre-check:** Tasks 1–2 committed (`cpu_limit_millicores` must validate before these files are edited to use it).

- [ ] **Step 1: Edit `scenario_3_{baseline,retryguard}.yaml`**

In each file, replace the constraint block:

```yaml
scale_constraints:
  - deployment: checkoutservice
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.1    # 0.1 × paper 1000m → 100m
    container: server          # container name inside the checkoutservice pod
```

with:

```yaml
scale_constraints:
  - deployment: checkoutservice
    namespace: default
    method: cpu_limit
    cpu_limit_millicores: 50   # absolute cap (ADR-0006) — the one CPU point
                                # checkoutservice has trustworthy mu_sat data
                                # for (experiments/capacity/capacity_frozen.json)
    container: server          # container name inside the checkoutservice pod
```

Also update the file header comment block (currently lines 8–11):

```
# Constraint method: cpu_limit with cpu_limit_fraction: 0.1
#   Paper quota for checkout is 1000m; fraction 0.1 → 100m K8s limit AND
#   TopFull Detector quota for this run. Runner reconciles both back to paper
#   after the run.
```

to:

```
# Constraint method: cpu_limit with cpu_limit_millicores: 50 (ADR-0006).
#   Absolute 50m K8s limit AND TopFull Detector quota for this run — the
#   one CPU point checkoutservice has trustworthy mu_sat saturation data
#   for. Runner reconciles both back to paper after the run.
```

- [ ] **Step 2: Edit `scenario_4a_{baseline,retryguard}.yaml`**

Replace:

```yaml
scale_constraints:
  - deployment: productcatalogservice
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.1    # 0.1 × paper 500m → 50m (not comparable to campaign_48 100m)
    container: server
```

with:

```yaml
scale_constraints:
  - deployment: productcatalogservice
    namespace: default
    method: cpu_limit
    cpu_limit_millicores: 50   # absolute cap (ADR-0006), same value as S3/S4B
    container: server
```

Update the header comment (currently `# Constraint: cpu_limit_fraction: 0.1 × paper productcatalog 500m → 50m\n# (campaign_48 used absolute 100m — new runs are not comparable to that set).`) to:

```
# Constraint: absolute cpu_limit_millicores: 50 (ADR-0006), same value used
# for S3 (checkoutservice) and S4B (paymentservice) — "limit different
# services in a similar way." Not comparable to campaign_48's absolute 100m.
```

- [ ] **Step 3: Edit `scenario_4b_{baseline,retryguard}.yaml`**

Read the file first to confirm the exact current constraint block (paymentservice), then apply the same pattern as Steps 1–2: swap `cpu_limit_fraction: 0.1` (or whatever fraction is present) for `cpu_limit_millicores: 50`, and fix the header comment analogously.

- [ ] **Step 4: Validate all six files**

```bash
python -c "
import sys, yaml
sys.path.insert(0, 'experiments')
import topfull_cpu_quotas as q
for f in ['scenario_3_baseline','scenario_3_retryguard','scenario_4a_baseline','scenario_4a_retryguard','scenario_4b_baseline','scenario_4b_retryguard']:
    cfg = yaml.safe_load(open(f'experiments/configs/{f}.yaml'))
    q.validate_scale_constraints(cfg.get('scale_constraints') or [])
    eff = q.effective_cpu_quotas(cfg.get('scale_constraints') or [])
    target = cfg['scale_constraints'][0]['deployment']
    print(f, '->', target, eff[target])
"
```

Expected: six lines printed, each ending in `50` (the target service's effective quota is now exactly 50m, not the old untested 61/153/15 absolutes).

- [ ] **Step 5: Commit**

```bash
git add experiments/configs/scenario_3_baseline.yaml experiments/configs/scenario_3_retryguard.yaml experiments/configs/scenario_4a_baseline.yaml experiments/configs/scenario_4a_retryguard.yaml experiments/configs/scenario_4b_baseline.yaml experiments/configs/scenario_4b_retryguard.yaml
git commit -m "feat: switch S3/S4A/S4B bottleneck cap to absolute cpu_limit_millicores: 50 (ADR-0006)"
```

---

## Task 6: Fix the 4 existing bottleneck-cap calibration YAMLs onto `cpu_limit_millicores: 50`

**Why this is a bug fix, not a style change:** each of these 4 files currently sets `cpu_limit_fraction: 0.05` (or `0.1` for productcatalog) as a fraction of `paper_limit_for(deployment)`. That function now returns the **Ron-config trimmed** value (checkoutservice 615m, frontend 1150m, paymentservice 155m, productcatalogservice 1535m) instead of the pre-migration values the comments describe (1000m / 500m). So today, running any of these 4 files would silently apply the *wrong* absolute limit (e.g. checkout: `0.05 × 615 = 30m`, not `50m`) — not the calibration these files' own names and `capacity_frozen.json`'s `calibrated_at_cpu_limit_millicores: 50` claim.

**Files:**
- Modify: `experiments/configs/scenario_calibration_frontend_constrained_50m.yaml`
- Modify: `experiments/configs/scenario_calibration_checkout_constrained_50m.yaml`
- Modify: `experiments/configs/scenario_calibration_payment_constrained_50m.yaml`
- Modify: `experiments/configs/scenario_calibration_productcatalog_constrained.yaml`

**Pre-check:** Tasks 1–4 committed (`cpu_limit_millicores` mechanism exists; both HPAs are live).

- [ ] **Step 1: Fix `scenario_calibration_frontend_constrained_50m.yaml`**

Replace:

```yaml
scale_constraints:
  - deployment: frontend
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.05    # 0.05 x paper 1000m -> 50m
    container: server
```

with:

```yaml
scale_constraints:
  - deployment: frontend
    namespace: default
    method: cpu_limit
    cpu_limit_millicores: 50    # absolute (ADR-0006) — fraction 0.05 now computes
                                 # against the Ron-config 1150m paper value (57.5m),
                                 # not the intended 50m
    container: server
```

Add a new comment line directly above `scale_constraints:` (this file's header already warns run1 must not be overwritten — leave that intact, add below it):

```yaml
# 2026-09-21: frontend now has a live HPA (frontend-hpa.yaml). Before running
# this calibration, pin it off so the reading is a single-replica ceiling:
#   ssh topfull-master "kubectl delete hpa frontend-hpa -n default"
# After the run, restore it:
#   ssh topfull-master "kubectl apply -f /tmp/frontend-hpa.yaml"
# (re-scp experiments/manifests/frontend-hpa.yaml first if /tmp is stale).
```

- [ ] **Step 2: Fix `scenario_calibration_checkout_constrained_50m.yaml`**

Replace:

```yaml
scale_constraints:
  - deployment: checkoutservice
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.05    # 0.05 x paper 1000m -> 50m
    container: server
```

with:

```yaml
scale_constraints:
  - deployment: checkoutservice
    namespace: default
    method: cpu_limit
    cpu_limit_millicores: 50    # absolute (ADR-0006) — fraction 0.05 now computes
                                 # against the Ron-config 615m paper value (30.75m),
                                 # not the intended 50m
    container: server
```

No HPA note needed — checkoutservice has no HPA. paymentservice is left unconstrained on purpose, so it reconciles to its real Ron-config paper value (155m), not an artificial old-paper 1000m headroom (design doc §2c) — no change needed to make that true, `reconcile_paper_cpu_limits()` already reconciles every `RECONCILE_SERVICES` entry to the current paper table before `apply_constraints()` runs.

- [ ] **Step 3: Fix `scenario_calibration_payment_constrained_50m.yaml`**

Same pattern as Step 2, mirrored: replace `cpu_limit_fraction: 0.05` on `paymentservice` with `cpu_limit_millicores: 50` and an updated comment. checkoutservice stays unconstrained (reconciles to its real 615m).

- [ ] **Step 4: Fix `scenario_calibration_productcatalog_constrained.yaml`**

Replace:

```yaml
scale_constraints:
  - deployment: productcatalogservice
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.1    # 0.1 × paper 500m → 50m (same as S4A)
    container: server
```

with:

```yaml
scale_constraints:
  - deployment: productcatalogservice
    namespace: default
    method: cpu_limit
    cpu_limit_millicores: 50   # absolute (ADR-0006) — fraction 0.1 now computes
                                # against the Ron-config 1535m paper value (153.5m),
                                # not the intended 50m
    container: server
```

Add the same HPA-off note pattern as Step 1, but for productcatalog:

```yaml
# 2026-09-21: productcatalog now has a live HPA (productcatalogservice-hpa.yaml,
# ADR-0005). Before running this calibration, pin it off so the reading is a
# single-replica ceiling:
#   ssh topfull-master "kubectl delete hpa productcatalogservice-hpa -n default"
# After the run, restore it:
#   ssh topfull-master "kubectl apply -f /tmp/productcatalogservice-hpa.yaml"
# (re-scp experiments/manifests/productcatalogservice-hpa.yaml first if /tmp is stale).
```

- [ ] **Step 5: Validate all four files**

```bash
python -c "
import sys, yaml
sys.path.insert(0, 'experiments')
import topfull_cpu_quotas as q
for f in ['scenario_calibration_frontend_constrained_50m','scenario_calibration_checkout_constrained_50m','scenario_calibration_payment_constrained_50m','scenario_calibration_productcatalog_constrained']:
    cfg = yaml.safe_load(open(f'experiments/configs/{f}.yaml'))
    q.validate_scale_constraints(cfg.get('scale_constraints') or [])
    eff = q.effective_cpu_quotas(cfg.get('scale_constraints') or [])
    target = cfg['scale_constraints'][0]['deployment']
    print(f, '->', target, eff[target])
"
```

Expected: four lines, each ending in `50`.

- [ ] **Step 6: Commit**

```bash
git add experiments/configs/scenario_calibration_frontend_constrained_50m.yaml experiments/configs/scenario_calibration_checkout_constrained_50m.yaml experiments/configs/scenario_calibration_payment_constrained_50m.yaml experiments/configs/scenario_calibration_productcatalog_constrained.yaml
git commit -m "fix: bottleneck-cap calibration YAMLs now land on the intended 50m absolute cap (ADR-0006), not a stale-paper-relative fraction"
```

---

## Task 7: Create the shared bottleneck reference-load calibration YAML

**Files:**
- Create: `experiments/configs/scenario_calibration_bottleneck_reference.yaml`

- [ ] **Step 1: Write the file**

Base it on `scenario_calibration_checkout_constrained_50m.yaml`'s shape (same infra block, same collectors), with no `scale_constraints` and the combined load recipe from design doc §3 run 5:

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# Calibration — bottleneck reference load, UNCONSTRAINED, TopFull+RG OFF
#
# Not part of the S1-S6 scenario matrix. 5th run of the bottleneck-cap
# recalibration battery (design doc §3, decision 8). Combines the two heavy
# tags from the checkout/payment (postcheckout:500) and productcatalog
# (getproduct:800) calibrations with light cart-family traffic. Purpose:
# check whether this single load recipe keeps every service OTHER than
# checkout/productcatalog/payment healthy when nothing is capped — if so,
# it becomes the shared reference load for S3/S4A/S4B (decision 8's
# shared-first attempt). If something else (most likely cartservice, since
# checkout calls it) is pulled into overload as a side effect, fall back to
# three separate per-scenario reference loads instead.
# scenario_id 48 so scenario_dir_name() returns "" (results under campaign_48/).
# ─────────────────────────────────────────────────────────────────────────────

scenario_id: 48
scenario_name: calibration_bottleneck_reference
condition: calibration
run_number: 1
description: >
  Calibration-only run. No scale_constraints — everything at its real
  Ron-config paper CPU. Combined heavy load (postcheckout + getproduct)
  used to check whether one shared reference load works for S3/S4A/S4B.
  TopFull RL off, RetryGuard off.

duration_seconds: 600

locust:
  user_counts:
    getproduct:   800
    postcheckout: 500
    getcart:      50
    postcart:     50
    emptycart:    50
  spawn_rate: 150
  scripts:
    - online_boutique_create.sh
    - online_boutique_create2.sh

scale_constraints: []

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

log_folder: calibration_bottleneck_reference_run1

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

- [ ] **Step 2: Validate**

```bash
python -c "
import sys, yaml
sys.path.insert(0, 'experiments')
import topfull_cpu_quotas as q
cfg = yaml.safe_load(open('experiments/configs/scenario_calibration_bottleneck_reference.yaml'))
q.validate_scale_constraints(cfg.get('scale_constraints') or [])
print('ok, scale_constraints:', cfg.get('scale_constraints'))
"
```

Expected: `ok, scale_constraints: []`.

- [ ] **Step 3: Commit**

```bash
git add experiments/configs/scenario_calibration_bottleneck_reference.yaml
git commit -m "feat: add shared bottleneck reference-load calibration YAML (design doc §3 run 5)"
```

---

## Task 8: Run the 5-run bottleneck-cap recalibration battery (live VM execution)

**Pre-check:** Tasks 1–7 committed.

- [ ] **Step 0: Start VMs (if stopped), refresh SSH HostNames, wait for cluster health**

If this is a new session or VMs were stopped after Task 4, check status and only then start + refresh IPs (same as Task 4 Step 0). Do **not** skip the status check.

```powershell
gcloud compute instances list --project=networks-workshop --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
# if TERMINATED:
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=networks-workshop
# refresh HostName in ~/.ssh/config, then:
ssh topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get hpa -n default"
```

Expected: 2 `Ready` nodes, all Boutique pods `2/2 Running`, both `frontend-hpa` and `productcatalogservice-hpa` listed.

Also confirm cluster shape before any freeze:

```bash
gcloud compute instances describe topfull-worker-1 --zone=us-central1-a --format='value(machineType)' --project=networks-workshop
```

Expected: ends in `e2-standard-16` — `capacity_frozen.py freeze` hard-errors otherwise.

- [ ] **Step 1: Clear stale `/tmp` runner scripts on master**

```bash
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
```

- [ ] **Step 2: Run 1 — frontend, 50m, HPA pinned off**

```bash
ssh topfull-master "kubectl delete hpa frontend-hpa -n default"
python experiments/run_scenario.py experiments/configs/scenario_calibration_frontend_constrained_50m.yaml
```

Wait for completion (`duration_seconds: 600` + startup), then:

```bash
python experiments/pull_results.py experiments/configs/scenario_calibration_frontend_constrained_50m.yaml
```

Then restore the HPA:

```bash
scp -o BatchMode=yes -o ControlMaster=no experiments/manifests/frontend-hpa.yaml topfull-master:/tmp/frontend-hpa.yaml
ssh topfull-master "kubectl apply -f /tmp/frontend-hpa.yaml"
```

Inspect the pulled `rho_estimate_report.md` (auto-generated by `pull_results.py` unless `--no-report`). Do **not** call `capacity_frozen.py freeze` yet without `--force`: frontend is already frozen in `capacity_frozen.json`, so freeze without `--force` raises `FrozenCapacityError` (`"{service} already frozen; pass force=True to overwrite"`) — it is not a dry run. Locking with `--force` is Task 8 Step 7, after all five runs. If `n_sat_ticks < 10` (`low_confidence`) or the number looks implausible, do not lock it yet — note it and continue; a low-confidence frontend reading was already seen once before (9-tick, superseded by a 26-tick reading) and might need a repeat at end of battery if VM time allows.

Use the YAML's actual `log_folder` as the pulled path (current file is `calibration_frontend_constrained_50m_run2` — confirm at execution time; bump first if that slot is already occupied).

- [ ] **Step 3: Cool off 300s, then Run 2 — checkoutservice, 50m, paymentservice at real 155m**

```bash
python experiments/run_scenario.py experiments/configs/scenario_calibration_checkout_constrained_50m.yaml
python experiments/pull_results.py experiments/configs/scenario_calibration_checkout_constrained_50m.yaml
```

Do **not** freeze yet (same as Step 2 — already-frozen services error without `--force`; lock in Step 7). Use the YAML's `log_folder` as the pulled path (current file is `calibration_checkout_constrained_50m_run2` — confirm at execution time; bump first if that slot is already occupied).

Also inspect `service_inbound.csv` for `paymentservice`'s own resets/5xx fraction during this run (design doc §2c's compound-bottleneck check) — if paymentservice's own `Δ(5xx+resets)/Δtotal` is also elevated, note this as a compound-bottleneck finding in the eventual `capacity/README.md` update (Step 6), not something to re-engineer away.

- [ ] **Step 4: Cool off 300s, then Run 3 — paymentservice, 50m, checkoutservice at real 615m**

```bash
python experiments/run_scenario.py experiments/configs/scenario_calibration_payment_constrained_50m.yaml
python experiments/pull_results.py experiments/configs/scenario_calibration_payment_constrained_50m.yaml
```

Do **not** freeze yet (lock in Step 7). Use the YAML's `log_folder` (currently `calibration_payment_constrained_50m_run2`).

- [ ] **Step 5: Cool off 300s, then Run 4 — productcatalogservice, 50m, HPA pinned off**

```bash
ssh topfull-master "kubectl delete hpa productcatalogservice-hpa -n default"
python experiments/run_scenario.py experiments/configs/scenario_calibration_productcatalog_constrained.yaml
python experiments/pull_results.py experiments/configs/scenario_calibration_productcatalog_constrained.yaml
scp -o BatchMode=yes -o ControlMaster=no experiments/manifests/productcatalogservice-hpa.yaml topfull-master:/tmp/productcatalogservice-hpa.yaml
ssh topfull-master "kubectl apply -f /tmp/productcatalogservice-hpa.yaml"
```

Do **not** freeze yet (lock in Step 7). Use the YAML's `log_folder` (currently `calibration_productcatalog_constrained_run1` — bump first if that completed folder must not be overwritten).

- [ ] **Step 6: Cool off 300s, then Run 5 — bottleneck reference load, unconstrained**

```bash
python experiments/run_scenario.py experiments/configs/scenario_calibration_bottleneck_reference.yaml
python experiments/pull_results.py experiments/configs/scenario_calibration_bottleneck_reference.yaml
```

Inspect `service_inbound.csv`/`service_edges.csv`/`resource_usage.csv` for every one of the 11 Boutique services in the pulled folder. Decision criterion (design doc §3 step 5, decision 8):

- If checkoutservice, productcatalogservice, and paymentservice show real overload signal (elevated `Δ(5xx+resets)/Δtotal`, high CPU) **and** every other service (frontend, cartservice, recommendationservice, shippingservice, currencyservice, emailservice, adservice, redis-cart) stays healthy (`Δ(5xx+resets)/Δtotal` near 0, CPU well under its paper limit): this recipe becomes the **shared** reference load — record its `user_counts`/`spawn_rate` in `capacity/README.md` (Step 7) and reuse it verbatim as the baseline load for S3/S4A/S4B in Task 10.
- If something else (most likely cartservice) also shows overload signal as a side effect of combining `postcheckout: 500` and `getproduct: 800` in one run: fall back to **three separate** reference loads — one per scenario, each using only that scenario's own heavy tag (e.g. S3's reference load is `postcheckout: 500` alone, light everything else) — and repeat this run three times with the isolated recipes before locking S3/S4A/S4B's non-bottleneck `user_counts` in Task 10.

- [ ] **Step 7: Freeze the results and update `experiments/capacity/capacity_frozen.json` / `README.md`**

For each of the 4 services whose freeze produced `low_confidence: false` (or an accepted `low_confidence: true` if no better reading was possible in this battery), lock it:

```bash
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/<run_folder> --service <service> --force
```

Update `experiments/capacity/README.md`'s table and prose to describe the new 2026-09-21-dated freezes (mirroring the existing 2026-09-19 entry's format), explicitly noting: (a) these supersede all four 2026-09-19 entries (pre-migration, no longer valid per design doc decision 2); (b) whether the shared or per-scenario reference-load path was taken in Step 6; (c) any compound-bottleneck finding from Step 3/4.

- [ ] **Step 8: Commit the updated capacity table and README**

```bash
git add experiments/capacity/capacity_frozen.json experiments/capacity/README.md
git commit -m "feat: re-freeze mu_per_millicore for frontend/checkout/payment/productcatalog under Ron-config topology (post-migration recalibration battery)"
```

_Do not commit the pulled `experiments/results/campaign_48/calibration_*_run<N>/` folders in this step if they weren't already tracked — check `git status` first; if the repo's convention (per `AGENTS.md`) is to track calibration run folders in git like the rest of `campaign_48/`, add them in a separate commit for clarity._

---

> **SUPERSEDED (2026-09-21, mid-execution): Task 8 above ran on the legacy `online_boutique_create.sh`/`create2.sh` launcher, not `online_boutique_create_v2.sh`.** See design doc [§9 decision 16](../specs/2026-09-21-s1-s6-methodology-and-calibration-design.md#9-session-amendment-2026-09-21-discovered-mid-execution-after-task-8-landed). The legacy launcher's `RATE`-as-divisor bug and merged getcart/postcart/emptycart process mean Task 8's five runs did not measure the load their YAMLs specify. **Task 8a and Task 8b below re-run this work correctly before Task 9 proceeds.** The `capacity_frozen.json` values this Task 8 committed (frontend 0.26, checkout 1.47, payment 0.24, productcatalog 1.62) are superseded by Task 8b, not ground truth.

---

## Task 8a: Swap all scenario + calibration YAMLs to `online_boutique_create_v2.sh`

**Files (21):**
- Modify all 16 scenario YAMLs: `scenario_1_baseline.yaml`, `scenario_1_retryguard.yaml`, `scenario_2_baseline.yaml`, `scenario_2_retryguard.yaml`, `scenario_3_baseline.yaml`, `scenario_3_retryguard.yaml`, `scenario_4a_baseline.yaml`, `scenario_4a_retryguard.yaml`, `scenario_4b_baseline.yaml`, `scenario_4b_retryguard.yaml`, `scenario_5_interval_10s.yaml`, `scenario_5_interval_20s.yaml`, `scenario_5_interval_30s.yaml`, `scenario_5_interval_60s.yaml`, `scenario_6_recovery_baseline.yaml`, `scenario_6_recovery_retryguard.yaml`
- Modify the 5 Task 8 calibration YAMLs: `scenario_calibration_frontend_constrained_50m.yaml`, `scenario_calibration_checkout_constrained_50m.yaml`, `scenario_calibration_payment_constrained_50m.yaml`, `scenario_calibration_productcatalog_constrained.yaml`, `scenario_calibration_bottleneck_reference.yaml`

Mechanical only. No code change (`run_scenario.py`'s `_launch_locust()` already dual-exports `EMPTYCART`; a bare `spawn_rate` already maps to v2's shared `RATE`, applied to all 5 tags). No `user_counts`/`spawn_rate`/`run_number` changes in this task.

- [ ] **Step 1: For each of the 21 files, replace**

```yaml
  scripts:
    - online_boutique_create.sh
    - online_boutique_create2.sh
```

with:

```yaml
  scripts:
    - online_boutique_create_v2.sh
```

(both the top-level `locust.scripts` for single-phase files, and the shared top-level `locust.scripts` key for S5/S6's phase-based files.)

- [ ] **Step 2: Verify all 21 files**

```bash
python -c "
import yaml, glob
files = [
    'scenario_1_baseline','scenario_1_retryguard','scenario_2_baseline','scenario_2_retryguard',
    'scenario_3_baseline','scenario_3_retryguard','scenario_4a_baseline','scenario_4a_retryguard',
    'scenario_4b_baseline','scenario_4b_retryguard','scenario_5_interval_10s','scenario_5_interval_20s',
    'scenario_5_interval_30s','scenario_5_interval_60s','scenario_6_recovery_baseline','scenario_6_recovery_retryguard',
    'scenario_calibration_frontend_constrained_50m','scenario_calibration_checkout_constrained_50m',
    'scenario_calibration_payment_constrained_50m','scenario_calibration_productcatalog_constrained',
    'scenario_calibration_bottleneck_reference',
]
for f in files:
    cfg = yaml.safe_load(open(f'experiments/configs/{f}.yaml', encoding='utf-8'))
    scripts = cfg['locust'].get('scripts', [])
    assert scripts == ['online_boutique_create_v2.sh'], f'{f}: unexpected scripts {scripts}'
    print(f, 'ok')
"
```

Expected: 21 lines, all `ok`.

- [ ] **Step 3: Commit**

```bash
git add experiments/configs/scenario_1_baseline.yaml experiments/configs/scenario_1_retryguard.yaml experiments/configs/scenario_2_baseline.yaml experiments/configs/scenario_2_retryguard.yaml experiments/configs/scenario_3_baseline.yaml experiments/configs/scenario_3_retryguard.yaml experiments/configs/scenario_4a_baseline.yaml experiments/configs/scenario_4a_retryguard.yaml experiments/configs/scenario_4b_baseline.yaml experiments/configs/scenario_4b_retryguard.yaml experiments/configs/scenario_5_interval_10s.yaml experiments/configs/scenario_5_interval_20s.yaml experiments/configs/scenario_5_interval_30s.yaml experiments/configs/scenario_5_interval_60s.yaml experiments/configs/scenario_6_recovery_baseline.yaml experiments/configs/scenario_6_recovery_retryguard.yaml experiments/configs/scenario_calibration_frontend_constrained_50m.yaml experiments/configs/scenario_calibration_checkout_constrained_50m.yaml experiments/configs/scenario_calibration_payment_constrained_50m.yaml experiments/configs/scenario_calibration_productcatalog_constrained.yaml experiments/configs/scenario_calibration_bottleneck_reference.yaml
git commit -m "fix: switch all scenario and calibration YAMLs onto online_boutique_create_v2.sh (design doc decision 16a) - legacy launcher's RATE-as-divisor and merged getcart/postcart/emptycart process invalidated prior live runs"
```

---

## Task 8b: Re-run the 5-run bottleneck-cap recalibration battery under v2 (supersedes Task 8)

**Pre-check:** Task 8a committed. This is a verbatim repeat of Task 8's Steps 0–8, with two differences: (1) the 5 calibration YAMLs now use `online_boutique_create_v2.sh` (already true after Task 8a — no further script edit needed here); (2) every YAML's `run_number`/`log_folder` must be bumped past Task 8's own already-used slots (e.g. `calibration_frontend_constrained_50m_run2` → `run3`; check `AGENTS.md` §4/§6 and the local + master folders for the actual next-free slot, since other sessions may have advanced it).

- [ ] **Step 0: Start VMs (if stopped), refresh SSH HostNames, wait for cluster health** — same as Task 8 Step 0 (worker must be `e2-standard-16`; both `frontend-hpa` and `productcatalogservice-hpa` present).

- [ ] **Step 1: Clear stale `/tmp` runner scripts on master** — same as Task 8 Step 1.

- [ ] **Step 2: Run 1 — frontend, 50m, HPA pinned off** — same as Task 8 Step 2, but bump `scenario_calibration_frontend_constrained_50m.yaml`'s `run_number`/`log_folder` past `run2` first.

- [ ] **Step 3: Cool off 300s, then Run 2 — checkoutservice, 50m** — same as Task 8 Step 3, bump past `run2`.

- [ ] **Step 4: Cool off 300s, then Run 3 — paymentservice, 50m** — same as Task 8 Step 4, bump past `run2`.

- [ ] **Step 5: Cool off 300s, then Run 4 — productcatalogservice, 50m, HPA pinned off** — same as Task 8 Step 5, bump past `run2`.

- [ ] **Step 6: Cool off 300s, then Run 5 — bottleneck reference load, unconstrained** — same as Task 8 Step 6, bump past `run1`. Re-evaluate the shared-vs-three-separate decision fresh under v2 — do not assume Task 8's "three separate" verdict still holds; v2's real per-tag application may change which services show overload.

- [ ] **Step 7: Freeze the results and update `experiments/capacity/capacity_frozen.json` / `README.md`** — same `--force` process as Task 8 Step 7. In the README update, explicitly note these 2026-09-21-v2-dated freezes supersede *both* the 2026-09-19 pre-migration freezes *and* Task 8's same-day legacy-launcher freezes (0.26/1.47/0.24/1.62) — three generations of values for these four services, only this one measured under the correct launcher.

- [ ] **Step 8: Commit**

```bash
git add experiments/capacity/capacity_frozen.json experiments/capacity/README.md
git commit -m "fix: re-freeze mu_per_millicore under online_boutique_create_v2.sh (design doc decision 16b) - supersedes Task 8's legacy-launcher freeze"
```

Same result-folder-commit caveat as Task 8 Step 8 applies here.

---

## Task 9: Run the S1/S2/S6 empirical system-load calibration (live VM execution, ≤3 tries each)

**Pre-check:** Task 8a and Task 8b complete (script swap done; battery re-frozen under v2). Cool off 300s after Task 8b's last run before starting S1. If VMs were stopped between Task 8b and Task 9, re-run Task 8 Step 0 (start + IP refresh + cluster health) before any try.

**S1 `run27` is discarded** (ran on the legacy launcher before this defect was found — see design doc decision 16c). It does not count against S1's 3-try cap. Fresh S1 try 1 below re-runs the *same* YAML numbers, now genuinely applied via v2.

**Human approval gate (mandatory):** after every try (S1 try 1, S1 try 2, …, S2 try 1, …, S6 try N), the agent must (1) pull results, (2) report the metric checks below, (3) **stop and wait for explicit user approval** before adjusting numbers, starting the next try, or moving to the next scenario. The user's judgment is whether the run matches what they had in mind for that scenario — that can diverge from (or tighten) the agent's checklist. Do **not** auto-decide "this try passed / failed / next adjustment is X" without user sign-off. Cap remains 3 tries per scenario; if still unresolved after 3 approved tries, stop and record it as an open item.

**Method (design doc §3b), applied per scenario below:** run at the scenario's current YAML numbers unchanged as try 1, report metrics + wait for user, then only if the user says so: adjust and re-run (try 2 / try 3).

- [ ] **Step 1a: S1 — try 1 (current numbers, unchanged)**

```bash
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
python experiments/pull_results.py experiments/configs/scenario_1_baseline.yaml
```

Agent metric checks (report these to the user; do not treat them as the final verdict):

```bash
python -c "
import csv
path = 'experiments/results/campaign_48/S1_normal_op/<log_folder>/topfull_detect.csv'
rows = list(csv.DictReader(open(path)))
overloaded = [r for r in rows if r.get('overloaded') == '1']
print(f'{len(overloaded)} overloaded rows out of {len(rows)}')
"
```

Also check `service_inbound.csv` for any service whose `Δ(5xx+resets)/Δtotal` sustains > 0.20 for 30 consecutive samples.

**S1 target criterion (design doc decision 11):** zero `overloaded=1` rows, zero sustained RetryGuard-kind overload on any service — plus the user's own sense that this looks like "normal operation."

- [ ] **Step 1b: STOP — user approval for S1 try 1**

Present the metric summary and the pulled folder path. Ask: accept these numbers for S1 / try again with adjustment / leave S1 open? Do not start try 2 or move to S2 until the user replies. If the user wants try 2/3: apply their requested adjustment (agent may *suggest* e.g. −20–30% on overload, but the user chooses), bump `run_number`/`log_folder`, cool off 300s, re-run, then repeat this approval gate. Stop after try 3 regardless.

- [ ] **Step 2a: S2 — try 1 (current numbers, unchanged)** — only after S1 is accepted or explicitly left open

```bash
python experiments/run_scenario.py experiments/configs/scenario_2_baseline.yaml
python experiments/pull_results.py experiments/configs/scenario_2_baseline.yaml
```

Agent metric checks to report (design doc decision 12) — qualitative combo, not a single pass/fail:
- (a) how many of the 9 `CONTROLLED_SERVICES` show sustained `Δ(5xx+resets)/Δtotal > 0.20` for ≥30 samples.
- (b) `overloaded=1` rows per service in `topfull_detect.csv`, and admitted vs offered gap in `topfull_throttle.csv`.
- (c) `retry` deltas on hot edges in `service_edges.csv` (storm vs noise).

Flag decision 14 risk if try 1 looks suspiciously healthy under frontend HPA (suggest a large jump only as a *proposal*).

- [ ] **Step 2b: STOP — user approval for S2 try 1**

Same gate as Step 1b. After each try, keep a short table (try#, services-overloaded-count, throttle-gap, retry-storm) for the user to compare. The user picks which tried load (if any) is "overloaded enough" — not the agent. Cap 3 tries.

- [ ] **Step 3a: S6 — try 1** — only after S2's winning load is user-approved

Start S6's `phases[0].user_counts` at the S2 numbers the user accepted (decision 13). Run try 1 with those numbers first:

```bash
python experiments/run_scenario.py experiments/configs/scenario_6_recovery_baseline.yaml
python experiments/pull_results.py experiments/configs/scenario_6_recovery_baseline.yaml
```

Report (a)/(b)/(c) for the 0–300s peak window, plus whether 300–900s recovery drops rejection under 0.20 for ≥30 consecutive samples (proxy for `OFF→ON` chance).

- [ ] **Step 3b: STOP — user approval for S6 try 1**

Same gate. Adjust peak and/or recovery only if the user asks; cap 3 tries.

- [ ] **Step 4: Record results (only after user lock-in)**

Write down the user-approved final `user_counts`/`spawn_rate` (and S6 phases) for Task 10. For any scenario left open after 3 tries or user deferral, note that for Task 11.

_No code or config commit for this task by itself — it is data-gathering only. Task 10 commits the resulting numbers into the YAMLs._

---

## Task 10: Rewire all 16 scenario YAMLs

**Pre-check:** Tasks 5, 8a, 8b, and 9 complete — S3/S4A/S4B already point at `cpu_limit_millicores: 50` (Task 5); all 16 files already point at `online_boutique_create_v2.sh` (Task 8a — Step 1 below is now a verify-only step, not an edit); the bottleneck-cap battery (Task 8b, the v2 re-run) has produced final `user_counts` for S3/S4A/S4B's target tag (and non-target tags, from whichever reference-load path Task 8b Step 6 settled on); the system-load calibration (Task 9, run on v2) has produced **user-approved** final `user_counts`/`spawn_rate` for S1/S2/S6 (do not rewrite those YAMLs from agent-only metric checks).

**Files (all 16):**
- Modify: `experiments/configs/scenario_1_baseline.yaml`, `scenario_1_retryguard.yaml`
- Modify: `experiments/configs/scenario_2_baseline.yaml`, `scenario_2_retryguard.yaml`
- Modify: `experiments/configs/scenario_3_baseline.yaml`, `scenario_3_retryguard.yaml`
- Modify: `experiments/configs/scenario_4a_baseline.yaml`, `scenario_4a_retryguard.yaml`
- Modify: `experiments/configs/scenario_4b_baseline.yaml`, `scenario_4b_retryguard.yaml`
- Modify: `experiments/configs/scenario_5_interval_10s.yaml`, `scenario_5_interval_20s.yaml`, `scenario_5_interval_30s.yaml`, `scenario_5_interval_60s.yaml`
- Modify: `experiments/configs/scenario_6_recovery_baseline.yaml`, `scenario_6_recovery_retryguard.yaml`

- [ ] **Step 1: Verify all 16 files already use `online_boutique_create_v2.sh`** (Task 8a should have already made this edit — this is a check, not a fresh edit)

```bash
python -c "
import yaml
files = ['scenario_1_baseline','scenario_1_retryguard','scenario_2_baseline','scenario_2_retryguard','scenario_3_baseline','scenario_3_retryguard','scenario_4a_baseline','scenario_4a_retryguard','scenario_4b_baseline','scenario_4b_retryguard','scenario_5_interval_10s','scenario_5_interval_20s','scenario_5_interval_30s','scenario_5_interval_60s','scenario_6_recovery_baseline','scenario_6_recovery_retryguard']
for f in files:
    cfg = yaml.safe_load(open(f'experiments/configs/{f}.yaml', encoding='utf-8'))
    scripts = cfg['locust'].get('scripts', [])
    assert scripts == ['online_boutique_create_v2.sh'], f'{f}: unexpected scripts {scripts} - Task 8a did not land or was reverted'
    print(f, 'ok')
"
```

If any file fails this check, Task 8a's commit is missing or was reverted — stop and fix that before continuing; do not silently re-edit here without figuring out why.

- [ ] **Step 2: Write S1's final numbers**

In both `scenario_1_baseline.yaml` and `scenario_1_retryguard.yaml`, set `locust.user_counts`/`spawn_rate` to whatever Task 9 Step 1 **user-approved** (unchanged from the existing YAML if try 1 was accepted as-is).

- [ ] **Step 3: Write S2's final numbers**

In both `scenario_2_baseline.yaml` and `scenario_2_retryguard.yaml`, set `locust.user_counts`/`spawn_rate` to whatever Task 9 Step 2 **user-approved**.

- [ ] **Step 4: Write S3/S4A/S4B's final numbers**

In `scenario_3_{baseline,retryguard}.yaml`, `scenario_4a_{baseline,retryguard}.yaml`, `scenario_4b_{baseline,retryguard}.yaml`: set `locust.user_counts`/`spawn_rate` to Task 8's finalized reference load (shared or per-scenario, per whichever path Step 6 of Task 8 took) — the target tag (`postcheckout` for S3, `getproduct` for S4A, `postcheckout` for S4B — confirm S4B's actual primary tag by reading the file's header comment, since payment is reached via checkout) at the heavy value, the rest at the light reference values.

- [ ] **Step 5: Write S6's final numbers**

In `scenario_6_recovery_baseline.yaml` and `scenario_6_recovery_retryguard.yaml`, set both `locust.phases[0].user_counts` (peak) and `locust.phases[1].user_counts` (recovery, ~25% of peak) to whatever Task 9 Step 3 **user-approved**. Keep `spawn_rate` and `at_seconds: 0` / `at_seconds: 300` unchanged unless the user approved a phase-split change.

- [ ] **Step 6: Propagate S6's numbers to all four S5 files**

In each `scenario_5_interval_{10,20,30,60}s.yaml`, set `locust.phases` byte-identical to whatever `scenario_6_recovery_retryguard.yaml` now has (S5's load must match S6's RetryGuard arm exactly — only `retryguard.interval_samples` differs across the four S5 files, already correctly varying 10/20/30/60).

- [ ] **Step 7: Bump `run_number`/`log_folder` on all 16 files**

For each file, check `AGENTS.md` §4/§6 for the current next-free slot for that scenario (the exact numbers are not fixed by this plan — other sessions may have advanced them). Update both `run_number:` and the corresponding `log_folder:` value to that next-free slot. Do not reuse any `run_number`/`log_folder` combination already listed as completed in `AGENTS.md`.

- [ ] **Step 8: Validate all 16 files parse and their constraints still validate**

```bash
python -c "
import sys, yaml
sys.path.insert(0, 'experiments')
import topfull_cpu_quotas as q
files = [
    'scenario_1_baseline','scenario_1_retryguard',
    'scenario_2_baseline','scenario_2_retryguard',
    'scenario_3_baseline','scenario_3_retryguard',
    'scenario_4a_baseline','scenario_4a_retryguard',
    'scenario_4b_baseline','scenario_4b_retryguard',
    'scenario_5_interval_10s','scenario_5_interval_20s',
    'scenario_5_interval_30s','scenario_5_interval_60s',
    'scenario_6_recovery_baseline','scenario_6_recovery_retryguard',
]
for f in files:
    cfg = yaml.safe_load(open(f'experiments/configs/{f}.yaml'))
    q.validate_scale_constraints(cfg.get('scale_constraints') or [])
    scripts = cfg['locust'].get('scripts', [])
    assert scripts == ['online_boutique_create_v2.sh'], f'{f}: unexpected scripts {scripts}'
    print(f, 'ok, run_number=', cfg['run_number'], 'log_folder=', cfg['log_folder'])
"
```

Expected: 16 lines, all `ok`, no `AssertionError`/`ValueError`.

- [ ] **Step 9: Commit**

```bash
git add experiments/configs/scenario_1_baseline.yaml experiments/configs/scenario_1_retryguard.yaml experiments/configs/scenario_2_baseline.yaml experiments/configs/scenario_2_retryguard.yaml experiments/configs/scenario_3_baseline.yaml experiments/configs/scenario_3_retryguard.yaml experiments/configs/scenario_4a_baseline.yaml experiments/configs/scenario_4a_retryguard.yaml experiments/configs/scenario_4b_baseline.yaml experiments/configs/scenario_4b_retryguard.yaml experiments/configs/scenario_5_interval_10s.yaml experiments/configs/scenario_5_interval_20s.yaml experiments/configs/scenario_5_interval_30s.yaml experiments/configs/scenario_5_interval_60s.yaml experiments/configs/scenario_6_recovery_baseline.yaml experiments/configs/scenario_6_recovery_retryguard.yaml
git commit -m "feat: rewire all 16 scenario YAMLs onto v2 loadgen launcher + Ron-config-recalibrated numbers"
```

---

## Task 11: Close the documentation loop

**Files:**
- Modify: `Guides and Info/RON-NEZER-BASE-MIGRATION.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md`

- [ ] **Step 1: Add the productcatalog-HPA overcommit risk note to `RON-NEZER-BASE-MIGRATION.md`**

In §5's second bullet (the one ending "...ADR-0005, **flag this risk here once implemented**)"), append a new sentence immediately after that parenthetical, replacing the forward-reference with the actual content:

```
 **Risk now flagged, as promised above**: `topfull-worker-1`'s app-container budget is already at its edge at frontend's own full 4-replica scale-out (ADR-0003's ≈13,360m against a ≈13,350m budget); productcatalog's 2nd HPA replica (+1,535m app + 100m sidecar) has no guaranteed headroom if frontend is simultaneously at its own max — an accepted overcommit risk (ADR-0005), not an oversight. If both ever happen at once, new productcatalog pods can go `Pending` (silently unschedulable) rather than actually scaling out, which could look like "the bottleneck held" when it's really "the node ran out of room." A future agent debugging an unexplained "didn't scale" result on any productcatalog-HPA scenario (S4A in particular) should check node scheduling pressure (`kubectl describe node topfull-worker-1`) before assuming the scenario mechanism itself failed.
```

- [ ] **Step 2: Update `AGENTS.md` §4**

Add a new bullet to the "✅ Done" list (after the "Ron-Nezer base migration" bullet) summarizing: the `cpu_limit_millicores` mechanism landed; productcatalog HPA landed (`maxReplicas: 2`); the 5-run bottleneck-cap battery re-froze `capacity_frozen.json` under the Ron-config topology; the S1/S2/S6 empirical calibration ran (note which scenarios changed numbers, which stayed, and any still-open item from Task 9 Step 4); all 16 scenario YAMLs are rewired onto `online_boutique_create_v2.sh` with real numbers. Update the "❌ Not done yet" section to remove the now-closed items and add "fresh campaign to replace `campaign_48/`" as the next open item (tracker §5 — still not scheduled).

- [ ] **Step 3: Check off the completed tracker items**

In `docs/superpowers/specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md`, check off every `- [ ]` box in §1, §2, and §3 that this plan's tasks closed. Leave §4 ("Deploying v2 for real use") checked once Task 10's rewired YAMLs have actually been run at least once for real (not just calibration) — if this plan's execution session doesn't get that far, leave §4 unchecked and note why. Leave §5 ("Fresh campaign") unchecked — explicitly out of scope for this plan.

- [ ] **Step 4: Commit**

```bash
git add "Guides and Info/RON-NEZER-BASE-MIGRATION.md" AGENTS.md docs/superpowers/specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md
git commit -m "docs: close out S1-S6 methodology rework + recalibration battery tracker items"
```

---

## Self-Review Notes

- **Spec coverage:** Design doc §7's implementation checklist items 1–8 map to Tasks 1 (item 1), 2 (item 1, run_scenario.py half), 5 (item 2), 4 (item 3), 8 (item 4), 9 (item 5), 10 (item 6), 11 (item 7), 6 (item 8, plus Task 3's HPA guard extension which the design doc's item 3 implied but didn't spell out as a separate guard). Tracker §1/§2/§3's checkboxes are all covered by Tasks 1–10; §4/§5 are explicitly deferred per the design doc's own scope (Task 11 Step 3 records this rather than silently dropping it).
- **Ordering matches the design doc's own suggested order** (§7): "#1+#2 together, #3 independently [here: Task 3], #8 before #4 [here: Task 6 before Task 8], #4+#5 together [here: Task 8+9], #6 once #4/#5 have real numbers [here: Task 10], #7 last [here: Task 11]."
- **Placeholder scan:** Task 9's live-adjustment steps describe *how* to decide an adjustment (proportional reduction for S1, 2–3× jump for S2 if suspiciously healthy) rather than a fixed number, because the actual adjustment is inherently data-dependent on Task 9's own live results — this is a live-calibration procedure, not a code change with a knowable-in-advance answer, and mirrors the design doc's own decision 10 ("adjust and re-run" without pre-committing to a formula). Adjustments are **proposals only**: after every try the agent stops for explicit user approval before the next try or scenario (Global Constraints + Task 9 Steps 1b/2b/3b).
- **VM start:** Tasks 4 and 8 both open with an explicit status-check → start-if-stopped → IP-refresh → cluster-health step; Global Constraints forbid assuming VMs are already `RUNNING`.
