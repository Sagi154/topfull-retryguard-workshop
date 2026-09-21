# Remaining work: S1–S6 methodology, loadgen numbers, YAML rewiring (2026-09-21)

Tracker for the work still deferred in:

- [2026-09-20-ron-nezer-base-migration-design.md](2026-09-20-ron-nezer-base-migration-design.md) §8
- [2026-09-21-loadgen-shape-ron-migration-design.md](2026-09-21-loadgen-shape-ron-migration-design.md) §3

This is an inventory, not a design. Check a box when the work is actually done. Do not treat unchecked items as decided.

Related (stale numbers — do not reuse as-is): [2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md](2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md).

---

## Already done (not part of this tracker)

These are context only. They are what the remaining work sits on.

- [x] CPU / replica / HPA migration (Ron-config regime numbers, quota-sync, frontend HPA) — [2026-09-20-ron-nezer-base-migration-implementation.md](../plans/2026-09-20-ron-nezer-base-migration-implementation.md)
- [x] Loadgen **shape** mechanism — [2026-09-21-loadgen-shape-ron-migration-implementation.md](../plans/2026-09-21-loadgen-shape-ron-migration-implementation.md)
  - `experiments/loadgen/online_boutique_create_v2.sh` is the launcher
  - `EMPTYCART` dual-export wired into `run_scenario.py`
  - `@task()` weight remix patcher exists (`experiments/patch_locust_task_weights.py`)
  - auto-deploy of repo-tracked loadgen scripts wired into `_launch_locust()`

What's still open is everything that depends on **loadgen numbers** and **scenario methodology**, not shape.

---

## 1. Fresh calibration pass (blocker for everything else)

- [ ] Re-calibrate per-tag user counts and spawn rate under the Ron-config regime
- [ ] Re-freeze `experiments/capacity/capacity_frozen.json` (and the μ-per-millicore values `estimate_service_mu.py` depends on) under the new CPU numbers before using them as a sizing aid

All 16 scenario YAMLs' current `locust.user_counts` / `spawn_rate` (example: S3 baseline `getproduct: 100, postcheckout: 20, getcart: 100, postcart: 100, emptycart: 300, spawn_rate: 90`) were calibrated against the **paper-config regime** — old CPU limits, no frontend HPA, old Detector table.

Those numbers are stale for two independent reasons:

1. The cluster's compute shape changed (Ron-config CPU trims, frontend now HPA 1→4 instead of fixed).
2. The loadgen launcher shape changed (five fully independent single-tag swarms instead of a merged `$CART` swarm) — so even "the same total user count" distributes differently across services than before.

This needs a real calibration exercise: find out what per-tag rate each of S1–S6 needs to hit their intended load *character* ("normal", "sustained overload", "moderate load with one bottleneck saturated", etc.) under the new cluster.

Neither Ron's launcher-script numbers nor the 2026-09-20 loadgen-redesign §4 numbers are reused.

---

## 2. S1–S6 scenario methodology rework (not just numbers)

Some scenarios' *mechanism*, not just their load numbers, assumed the old regime.

- [ ] Rebuild S3 / S4 targeted-bottleneck mechanism against Ron-config CPU numbers
- [ ] Resolve S4A vs productcatalog HPA conflict (decision still open)
- [ ] Verify S1 / S2 / S5 / S6 still only need new numbers, not new mechanism

Concrete open issues:

- **S3 / S4 "targeted bottleneck"** — currently `cpu_limit_fraction: 0.1` applied to the paper-quota CPU number for one service (e.g. checkout 1000m → 100m). Under the Ron-config regime the baseline CPU per service is different (already uniformly trimmed ~77% to fit the 16-vCPU worker), so what a "0.1 fraction" bottleneck even means, and whether it still produces a real bottleneck relative to everything else's new smaller CPU, has to be rebuilt. (Migration design, decision 3's note.)
- **S4A (productcatalog as the topology target)** — conflicts with the `productcatalogservice` HPA decision (disabled for now, but the premise "productcatalog is a fixed, non-compensating bottleneck" assumed no autoscaling). Options still open: re-enable HPA there and treat autoscale-compensation as a finding, pick a different S4A target service, or something else. (Migration design, decision 9.)
- **S1 / S2 / S6 / S5** — probably just need new numbers, not new mechanism, but that still needs to be verified case by case once real calibration data exists.

---

## 3. Rewire the 16 scenario YAMLs

Once §1 and §2 produce real numbers / mechanisms:

- [ ] Point `locust.scripts` at `online_boutique_create_v2.sh` (drop `create2.sh`; no trickle-pattern replacement)
- [ ] Write new `locust.user_counts` / `spawn_rate` from the calibration
- [ ] Update `scale_constraints` on S3 / S4 once §2 is resolved
- [ ] Bump `log_folder` / `run_number` to new slots (these are new runs, not resumes)

The 16 files (all currently still on the legacy `online_boutique_create.sh` + `online_boutique_create2.sh` pair):

| Scenario | Baseline | RetryGuard |
|---|---|---|
| S1 | `scenario_1_baseline.yaml` | `scenario_1_retryguard.yaml` |
| S2 | `scenario_2_baseline.yaml` | `scenario_2_retryguard.yaml` |
| S3 | `scenario_3_baseline.yaml` | `scenario_3_retryguard.yaml` |
| S4A | `scenario_4a_baseline.yaml` | `scenario_4a_retryguard.yaml` |
| S4B | `scenario_4b_baseline.yaml` | `scenario_4b_retryguard.yaml` |
| S5 | `scenario_5_interval_{10,20,30,60}s.yaml` (RG-only, 4 files) | |
| S6 | `scenario_6_recovery_baseline.yaml` | `scenario_6_recovery_retryguard.yaml` |

Also on disk, not in the 16, and not automatically in scope here: `scenario_2_baseline_no_topfull.yaml` and the `scenario_calibration_*.yaml` files. Decide later whether they get the same launcher rewire.

---

## 4. Deploying v2 for real use

- [ ] First real scenario run that lists `online_boutique_create_v2.sh` in `locust.scripts`

The auto-deploy mechanism already exists (`run_scenario.py` pushes any `experiments/loadgen/*.sh` listed in a scenario's `locust.scripts` onto `topfull-load` before launch), and the weight-remix patcher exists and was smoke-tested. Nothing has actually *run* v2 as part of a real scenario yet. Once a YAML is rewired, this happens automatically on the next `run_scenario.py` invocation — no separate manual deploy step.

---

## 5. Fresh campaign to replace `campaign_48/`

- [ ] Plan a new campaign under the Ron-config regime
- [ ] Run it; treat `campaign_48/` (and `august_38/`) as historical (migration design, decision 6)

This is last. It has not been scheduled.

---

## Dependency order

```
§1 calibration  ──┐
                  ├──►  §3 YAML rewiring  ──►  §4 v2 used in a real run  ──►  §5 new campaign
§2 methodology  ──┘     (S3/S4/S4A need §2
                         before those YAMLs
                         can be finalized)
```

Do not fill §3 with guessed numbers. Do not start §5 until §3 is stable.
