# S2 frontend 2× CPU quota probe

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Raise only frontend’s Kubernetes CPU limit and TopFull Detector quota to
> **2000 m** (2× paper 1000 m) on unconstrained Scenario 2, same Locust mix.
> Test whether a backend can become the Detector trip and whether mesh
> retries / RetryGuard then appear. Locust `user_counts` unchanged.

Related: [2026-09-09-topfull-quota-k8s-sync-design.md](2026-09-09-topfull-quota-k8s-sync-design.md),
[2026-09-15-TOPFULL-E2-16-RETRY-SUMMARY.md](../../../Guides%20and%20Info/2026-09-15-TOPFULL-E2-16-RETRY-SUMMARY.md),
[TOPFULL-ACTIVATION-DIAGNOSIS.md](../../../Guides%20and%20Info/TOPFULL-ACTIVATION-DIAGNOSIS.md).

---

## 1. Hypothesis

On e2-standard-16 unconstrained S2 with paper quotas, **frontend** is the only
service that crosses Detector (`CPU > quota × α`, frontend gate 800 m). TopFull
then clusters all five storefront APIs and caps entry. Backends stay under
quota (catalog closest: ~442 m vs 475 m). Mesh retries ≈ 0; RetryGuard never
disables.

If frontend’s cgroup **and** Detector quota both rise to **2000 m** (gate
**1600 m**) while backends stay on paper, the same Locust mix may push more
work through the aggregator. A backend may then trip Detector, produce
outbound Envoy retries, and give RetryGuard a sustained rejection signal.

**Negative result is still useful:** if frontend remains the only overload and
retries stay ~0, the extra core was eaten at the gate and Locust-mix tweaks
alone will not fix unconstrained S2 under live TopFull.

---

## 2. What changes

| Knob | Value |
|---|---|
| Frontend K8s `limits.cpu` / `requests.cpu` | **2000 m** (`cpu_limit_fraction: 2.0`) |
| Frontend Detector quota (`topfull_run_quotas.json`) | **2000** |
| Backend quotas | Paper table (unchanged) |
| Locust `user_counts` / `spawn_rate` | Same as deck S2 |
| Duration | 600 s |
| Worker | **e2-standard-16** (abort if not) |

`millicores_from_fraction` allows `(0, 4]` so fraction `2.0` is valid.
Teardown reconciles everyone back to the paper table.

Configs (independent of `scenario_2_baseline.yaml` / `scenario_2_retryguard.yaml`
run counters):

| YAML | `log_folder` (run1) |
|---|---|
| [`scenario_2_baseline_frontend_2x.yaml`](../../../experiments/configs/scenario_2_baseline_frontend_2x.yaml) | `baseline_frontend_2x_sustained_overload_run1` |
| [`scenario_2_retryguard_frontend_2x.yaml`](../../../experiments/configs/scenario_2_retryguard_frontend_2x.yaml) | `run_frontend_2x_retryguard_sustained_overload_run1` |

Results land under `experiments/results/campaign_48/S2_sustained_overload/`.
**Do not overwrite** paper-quota e2-16 folders: S2 baseline **run23**, S2 RG
**run12** (or earlier run21/run10).

---

## 3. Lab sequence

1. Start VMs if `TERMINATED`; refresh SSH `HostName`; confirm `idozacharia`.
2. Confirm worker `machineType` is `e2-standard-16`.
3. Wait for `kubectl get nodes` / Boutique pods 2/2 / VirtualServices healthy.
4. Clear stale `/tmp/rg_*.sh` on master.
5. **300 s cool-off**, then baseline frontend-2× run; pull.
6. Confirm `service_capacity.json` / `run_manifest.json` show frontend **2000**.
   If still 1000 m — **stop** (quota path failed).
7. Clear `/tmp` again; **300 s cool-off**; RetryGuard frontend-2× run; pull.
8. Leave VMs **RUNNING** unless asked to stop.

---

## 4. Pass / fail gates (vs run23 / run12)

| Gate | Positive | Negative (still informative) |
|---|---|---|
| Frontend quota | Layer B / capacity JSON `quota` 2000 | Still 1000 → bug |
| Detector | Frontend max CPU **below 1600 m**; a **backend** `overloaded=1` | Frontend still only overload |
| Retries | `service_edges.csv` outbound `retry` Δ ≫ paper-quota S2 (~0) | Still ~0 |
| RetryGuard | `ON→OFF` in `retryguard.log` | Zero toggles (same as run12) |

---

## 5. Out of scope

- Raising Locust users or reweighting the mix — follow-up probe:
  [2026-09-17-s2-frontend-2x-user-scale-design.md](2026-09-17-s2-frontend-2x-user-scale-design.md).
- Raising backend quotas.
- Editing the global paper table for all scenarios.
- Campaign-matrix overwrites.
- Optional later: S1 with the same frontend 2× overlay.
