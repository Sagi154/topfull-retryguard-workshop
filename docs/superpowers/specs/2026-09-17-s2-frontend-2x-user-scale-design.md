# S2 frontend 2× + Locust 1.5× / 2× user-scale baselines

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Keep frontend at **2000 m** (K8s + Detector) and raise Locust offered load
> to **1.5×** and **2×** deck S2 user counts (baseline only). Test whether the
> unused frontend core from the 1.0×-users frontend-2× run gets consumed and
> whether a backend trips Detector / Envoy retries appear.

Related: [2026-09-17-s2-frontend-2x-quota-design.md](2026-09-17-s2-frontend-2x-quota-design.md),
[2026-09-15-TOPFULL-E2-16-RETRY-SUMMARY.md](../../../Guides%20and%20Info/2026-09-15-TOPFULL-E2-16-RETRY-SUMMARY.md).

---

## 1. Hypothesis

The frontend-2× baseline at deck Locust intensity
(`baseline_frontend_2x_sustained_overload_run1`) confirmed:

- Frontend quota / capacity **2000 m** (gate **1600 m**).
- Frontend max CPU stayed ~**1058 m** — the second core was unused.
- Catalog moved **away** from its 475 m gate; mesh Δ`retry` ≈ 3; TopFull
  thresholds stayed at the uncapped sentinel on fresh scrapes.

Raising offered load while keeping the same frontend headroom should push
more work through the aggregator. Positive outcomes: frontend CPU climbs
toward 1600 m and/or a backend (catalog was the prior bet) trips Detector,
with outbound Envoy retries rising above the 1.0×-users floor.

**Negative result is still useful:** if frontend stays ~1 core and retries
stay ~0 at 2× users, uniform Locust scaling alone will not unlock
unconstrained S2 under live TopFull + frontend-2×.

---

## 2. What changes

| Knob | Value |
|---|---|
| Frontend K8s + Detector | **2000 m** (`cpu_limit_fraction: 2.0`) — same as frontend-2× probe |
| Backend quotas | Paper table (unchanged) |
| Locust intensity | **1.5×** then **2×** deck S2 users; spawn scaled (135 / 180) |
| Condition | **Baseline only** (RetryGuard off) |
| Duration | 600 s |
| Worker | **e2-standard-16** (abort if not) |

### Locust table

| API | 1.0× (ref run1) | 1.5× | 2× |
|---|---|---|---|
| getproduct | 100 | 150 | 200 |
| postcheckout | 20 | 30 | 40 |
| getcart | 100 | 150 | 200 |
| postcart | 100 | 150 | 200 |
| emptycart | 300 | 450 | 600 |
| **users / spawn** | 620 / 90 | 930 / 135 | 1240 / 180 |

Configs (independent of `scenario_2_baseline.yaml` and of
`scenario_2_baseline_frontend_2x.yaml` run counters):

| YAML | `log_folder` (run1) |
|---|---|
| [`scenario_2_baseline_frontend_2x_users15.yaml`](../../../experiments/configs/scenario_2_baseline_frontend_2x_users15.yaml) | `baseline_frontend_2x_users15_sustained_overload_run1` |
| [`scenario_2_baseline_frontend_2x_users2.yaml`](../../../experiments/configs/scenario_2_baseline_frontend_2x_users2.yaml) | `baseline_frontend_2x_users2_sustained_overload_run1` |

Results land under `experiments/results/campaign_48/S2_sustained_overload/`.

**Do not overwrite:** `baseline_frontend_2x_sustained_overload_run1`, paper-quota
S2 baseline **run23**, S2 RG **run12**, or campaign-matrix slots.

---

## 3. Lab sequence

1. Confirm VMs RUNNING, SSH as `idozacharia`, worker `e2-standard-16`.
2. Wait until any in-flight frontend-2× RetryGuard run finishes (do not overlap Locust).
3. Cluster health: nodes Ready, Boutique 2/2, VirtualServices present.
4. Clear stale `/tmp/rg_*.sh` / `envoy_retry_params.json` on master.
5. **300 s cool-off**, then 1.5× baseline; pull via `pull_results.py`.
6. Confirm `effective_cpu_quotas.frontend == 2000`. If still 1000 — **stop**.
7. Clear `/tmp` again; **300 s cool-off**; 2×-users baseline; pull.
8. Leave VMs **RUNNING** unless asked to stop.

---

## 4. Pass / fail gates (vs frontend-2× 1.0×-users run1)

| Gate | Positive | Negative (still informative) |
|---|---|---|
| Frontend quota | Layer B / manifest `quota` 2000 | Still 1000 → stop |
| Frontend CPU | Climbs toward **1600 m** gate (run1 max ~1058 m) | Still ~1 core |
| Detector | A **backend** `overloaded=1` (catalog 475 m gate) | Frontend-only or ads 1-tick spikes |
| Locust | `total` goodput / Fail vs run1 (`Fail` = 1 s SLO-miss) | Higher Fail, no mesh 5xx = SLO-only |
| Retries | `service_edges.csv` outbound Δ`retry` ≫ run1’s +3 | Still ~0 |
| Layer A | `threshold` leaves 10000 on fresh rows | Stays 10000 + Layer B ov=0 |

Use [METRICS-GATHERED.md](../../../Guides%20and%20Info/METRICS-GATHERED.md) for the
file inventory. `pull_results.py` writes `rho_estimate_report.md` into each folder.

---

## 5. Out of scope

- RetryGuard arms at the new loads.
- Paper-quota (1000 m frontend) variants.
- Changing Locust `wait_time` / arrival shape.
- Raising backend quotas or editing the global paper table.
- Campaign-matrix overwrites.

---

## 6. Readout (2026-09-18)

All three folders confirmed `effective_cpu_quotas.frontend = 2000`.

| Gate | 1.0× users (run1) | 1.5× users | 2× users |
|---|---|---|---|
| Frontend max CPU (Layer B) | 1058 m (util 0.529) | 959 m (0.479) | **1143 m** (0.572) — still under 1600 m |
| Catalog max CPU | 366 m | 421 m | **435 m** (gate 475) — still ov=0 |
| Backend `overloaded=1` | ads 1 tick only | none | none |
| Layer A fresh `threshold<10000` | 0 | 0 | 0 |
| Outbound Δ`retry` | +3 (→recommendation) | **0** | **+358** (→recommendation) |
| Locust total mean Fail/s | 2.8 | 83.3 | 6.0 |

**Verdict:** Uniform Locust scale with frontend-2× did **not** trip Detector on backends and did not consume the second frontend core. 2× users produced a modest recommendation-edge retry bump, not a storm. YAMLs bumped to run2; VMs terminated after the sequence.
