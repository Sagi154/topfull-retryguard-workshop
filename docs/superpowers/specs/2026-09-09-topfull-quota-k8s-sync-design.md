# TopFull quota ↔ Kubernetes CPU sync — design

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Keep TopFull’s hardcoded detector quotas and the live Kubernetes CPU limits on the same number for every run. Baseline = KAIST paper constants. S3/S4 bottlenecks = one fraction of those constants, applied to **both** Kubernetes and TopFull. Fixes the S2 run7 failure mode: checkout sat at 100m in Kubernetes while `Detector.detect()` still divided by 1000.

Related: [TOPFULL-THROTTLE-METRICS.md](../../../Guides%20and%20Info/TOPFULL-THROTTLE-METRICS.md), [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md), [2026-09-09-topfull-throttle-collector-design.md](2026-09-09-topfull-throttle-collector-design.md).

---

## 1. Purpose and scope

TopFull only marks a service overloaded when `cAdvisor_CPU > quota × α` (`α` = 0.8, or 0.95 for cart / productcatalog). `quota` is **not** read from the cluster. It is a dict in `overload_detection.py` `Detector.__init__`, written to match KAIST’s Boutique YAML (`online_boutique_original_custom.yaml`). Dynamic quota probing was never built.

Our cluster can (and did) diverge: S3 patches checkout to `100m` and a failed/skipped restore left that as the new “baseline.” S2 then offered `ρ > 1` against a 100m checkout while TopFull still used quota 1000, so Layer B never saw `overloaded=1` and the RL had no reason to cut a cap.

**This spec makes Kubernetes follow the paper table, and makes the paper table follow a run’s bottleneck fraction.**

In scope:

- One paper-quota table in our repo (same numbers as `Detector.__init__` after its Boutique overrides).
- Every `run_scenario.py` run: reset named services to that table, then apply S3/S4 as a **fraction** of it.
- The same millicores written into TopFull’s detector for that run (optional JSON overlay).
- Layer B (`topfull_detect.csv`) uses those per-run quotas, not a second stale dict.
- `service_capacity.json` / `run_manifest.json` record paper vs effective quotas.
- S3 / S4A / S4B YAMLs (both arms): `cpu_limit_fraction: 0.1` instead of `cpu_limit: "100m"`.

Out of scope:

- Teaching TopFull to `kubectl` live limits every detect() cycle.
- Changing `campaign_48/` or `august_38/` (historical; S4A there used 100m, not 50m).
- Changing Locust user counts, RetryGuard windows, or Layer A scrape (`/thresholds`, `/stats`).
- Reconciling services **not** in the paper override table (e.g. leaving `redis-cart` at Boutique `125m` even though Detector’s for-loop default is 1000).
- Autoscaling / replica changes (`instance_scaling.py` stays replicas-only).

---

## 2. Paper table (source of truth)

Copy of `Detector.__init__` after the Boutique override block. Units are **millicores**, same as cAdvisor `latest_usage.cpu`.

| Service | Paper limit (quota) | Boutique request (restore) |
|---|---|---|
| `cartservice` | 1000 | 500 |
| `currencyservice` | 1000 | 500 |
| `frontend` | 1000 | 500 |
| `adservice` | 1000 | 500 |
| `productcatalogservice` | 500 | 250 |
| `checkoutservice` | 1000 | 500 |
| `recommendationservice` | 2000 | 1000 |

**Default for any other service TopFull tracks** (the `for svc in data['services']: cpu = 1000` loop): limit **1000**. `paymentservice` is in this bucket (S4B). Request for payment on our cluster today is 200m; restore request **200** when reconciling payment to paper 1000.

The unused module constant `cpu_quota = 200` in `overload_detection.py` is **not** the detector default. Layer B’s current `DEFAULT_QUOTA = 200` is wrong relative to live `detect()` and must change to **1000** as part of this work.

Live in one module, e.g. `experiments/topfull_cpu_quotas.py` (importable from `run_scenario.py`, the throttle collector, and tests). Do not keep a third copy in YAML comments only.

---

## 3. Bottleneck = one fraction

S3 / S4A / S4B (baseline and RetryGuard) replace:

```yaml
method: cpu_limit
cpu_limit: "100m"
```

with:

```yaml
method: cpu_limit
cpu_limit_fraction: 0.1
```

`0.1` is the same fraction on every bottleneck service.

| Scenario | Service | Paper | Effective limit at 0.1 |
|---|---|---|---|
| S3 | `checkoutservice` | 1000 | 100m |
| S4A | `productcatalogservice` | 500 | **50m** |
| S4B | `paymentservice` | 1000 | 100m |

S4A is **not** comparable to campaign_48 S4A (that was 100m = 20% of 500). New slots only. Changing the pinch later is one YAML number.

**Compute:** `millicores = int(paper_limit * fraction)` (truncate toward zero). Reject `fraction <= 0` or `fraction > 1` at config-load. Format the kubectl quantity as `f"{millicores}m"`. For the constrained pod, set **both** `limits.cpu` and `requests.cpu` to that quantity (same as today’s patch: request must be ≤ limit).

S1 / S2 / S5 / S6 keep `scale_constraints: []`. After the start-of-run reconcile they sit on the paper table.

A constraint that still has `cpu_limit` (with or without a fraction) is a config error: the runner refuses to start. Tests fail if any S3/S4 YAML still contains `cpu_limit:`.

---

## 4. Runner sequence

In `run_scenario.py`, replace “capture then maybe patch 100m” with:

1. **Reconcile to paper.** For every service in the paper table (plus `paymentservice`), `kubectl patch` `limits.cpu` / `requests.cpu` to the paper limit / request in §2. This clears leftover S3 `100m` on checkout before S2 starts.
2. **Apply fractions.** For each `cpu_limit_fraction` constraint, patch that Deployment to `paper × fraction` (limit = request = computed m).
3. **Write effective quotas.** JSON map `service → millicores`: start from the paper table (and default 1000 for other Detector services we care about), overwrite constrained services with the computed millicores. Upload to master as `/home/idozacharia/experiments/topfull_run_quotas.json`.
4. **Ensure the detector loads that file** (see §5) **before** `deploy_rl.py` starts.
5. **Snapshot `service_capacity.json` after steps 1–2** (what the run actually used), not before. `run_manifest.json` also stores `paper_cpu_quotas`, `cpu_limit_fraction` (if any), and `effective_cpu_quotas`.
6. **Run** the existing stack / Locust / collectors.
7. **Teardown:** delete `topfull_run_quotas.json`; **reconcile Kubernetes back to the paper table** (§2), not to whatever dirty limits were present when the process started. If a run crashes, the *next* run’s step 1 still heals the cluster.

Layer B params include the same effective quota map (or the path to that JSON) so `topfull_detect.csv` `quota` / `utilization` / `overloaded` match `detect()`.

---

## 5. How TopFull sees the new quota

Do **not** rely on rewriting the seven assignment lines by hand each run.

**Once (idempotent):** if `overload_detection.py` on master does not already contain a marker comment, append at the end of `Detector.__init__`: if `/home/idozacharia/experiments/topfull_run_quotas.json` exists, load it and for each key that is already in `self.services`, set `self.services[svc]['cpu'] = int(value)`. Missing file → today’s hardcoded table (safe if someone starts `deploy_rl.py` by hand).

**Every run:** the runner only writes / deletes the JSON. `deploy_rl` is started after the file is in place so `__init__` sees it.

Backup the `.py` before the first marker patch so a bad edit is reversible. Do not commit a fork of all of TopFull; the overlay file is the per-run state.

---

## 6. Collector and docs

- `experiments/topfull_throttle_collector.py`: `quota_for()` reads the per-run map from params (required when the runner sent one). Fallback: paper table + default **1000**, never 200.
- `topfull_detect.csv` schema unchanged (`quota` column now means effective quota for that run).
- Guides to update when implementing (not this spec): [PHASE5-EXPERIMENTS-GUIDE.md](../../../Guides%20and%20Info/PHASE5-EXPERIMENTS-GUIDE.md) `scale_constraints` / `cpu_limit` wording; [SCENARIOS-GUIDE.md](../../../Guides%20and%20Info/SCENARIOS-GUIDE.md) S3/S4 “100m”; [AGENTS.md](../../../AGENTS.md) leftover-checkout note; [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md) “quotas are not K8s limits” — they are, for the duration of a run, after this lands.
- `campaign_48/` / `august_38/` unchanged. Next S2 after this lands is a **new** slot (S2 YAMLs are already on run7 consumed; bump before launch). Next S3/S4 are a new series (S4A 50m).

---

## 7. Tests

`experiments/test_topfull_cpu_quotas.py` (or cases on `test_run_scenario.py`):

- `millicores_from_fraction(1000, 0.1) == 100`
- `millicores_from_fraction(500, 0.1) == 50`
- fraction `0` / `1.1` / missing paper service → error
- YAML cannot set both `cpu_limit` and `cpu_limit_fraction`
- effective quota map: paper + one overwrite
- Layer B `quota_for('checkoutservice')` with params override 100 vs paper 1000

No live cluster required for merge. First live check after implement: `kubectl` checkout is 1000m on an S2 start; 100m on an S3 start; `topfull_run_quotas.json` matches; `topfull_detect.csv` `quota` for checkout is 1000 or 100 accordingly.

---

## 8. Success

- S1/S2/S6: Kubernetes checkout **1000m**, TopFull quota **1000**, leftover **100m** gone after any run’s reconcile.
- S3: checkout K8s **100m** and TopFull quota **100** for the run; both back to 1000 after.
- S4A: catalog **50m** / quota 50; S4B: payment **100m** / quota 100.
- Layer B `overloaded` can become 1 when usage exceeds `effective_quota × α` (S3 checkout ~90m vs 80m trip).
- Campaign folders not rewritten.

---

## Status

Design only. Approved direction: Kubernetes matches the paper table; S3/S4 apply **one fraction (0.1)** of that table to both Kubernetes and TopFull. Not implemented.
