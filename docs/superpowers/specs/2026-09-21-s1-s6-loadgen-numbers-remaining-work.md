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

**Methodology decided (2026-09-21)** — [2026-09-21-s1-s6-methodology-and-calibration-design.md](2026-09-21-s1-s6-methodology-and-calibration-design.md). Not yet executed.

- [ ] Run the 5-run recalibration battery (design doc §3): frontend, checkoutservice, productcatalogservice, paymentservice at 50m under the current Ron-config topology, plus one unconstrained bottleneck reference load
- [ ] Re-calibrate S1/S2/S5/S6 per-tag user counts and spawn rate under the Ron-config regime (separate from the battery above — no mechanism dependency, just new numbers)
- [ ] Update `experiments/capacity/capacity_frozen.json` / `README.md` from the battery's results

All 16 scenario YAMLs' current `locust.user_counts` / `spawn_rate` (example: S3 baseline `getproduct: 100, postcheckout: 20, getcart: 100, postcart: 100, emptycart: 300, spawn_rate: 90`) were calibrated against the **paper-config regime** — old CPU limits, no frontend HPA, old Detector table.

Those numbers are stale for two independent reasons:

1. The cluster's compute shape changed (Ron-config CPU trims, frontend now HPA 1→4 instead of fixed).
2. The loadgen launcher shape changed (five fully independent single-tag swarms instead of a merged `$CART` swarm) — so even "the same total user count" distributes differently across services than before.

This needs a real calibration exercise: find out what per-tag rate each of S1–S6 needs to hit their intended load *character* ("normal", "sustained overload", "moderate load with one bottleneck saturated", etc.) under the new cluster. The design doc's §1 (methodology) settles *how*: a rough `mu_sat`-based starting guess, reused only at the exact CPU value it was measured at (never extrapolated across CPU values — see `CONTEXT.md`'s "`mu_per_millicore`'s trust boundary"), always confirmed live before locking a number.

Neither Ron's launcher-script numbers nor the 2026-09-20 loadgen-redesign §4 numbers are reused.

---

## 2. S1–S6 scenario methodology rework (not just numbers)

Some scenarios' *mechanism*, not just their load numbers, assumed the old regime.

**Decided (2026-09-21)** — [2026-09-21-s1-s6-methodology-and-calibration-design.md](2026-09-21-s1-s6-methodology-and-calibration-design.md), [ADR-0005](../../adr/0005-productcatalog-hpa-max-replicas-2.md), [ADR-0006](../../adr/0006-absolute-bottleneck-cap-not-fraction.md). Not yet implemented.

- [ ] Add `cpu_limit_millicores` (absolute) as a new `scale_constraints` method in `topfull_cpu_quotas.py`/`run_scenario.py`
- [ ] Switch S3/S4A/S4B's `scale_constraints` from `cpu_limit_fraction: 0.1` to `cpu_limit_millicores: 50`; fix stale pre-migration docstrings
- [ ] Create `productcatalogservice-hpa.yaml` (`minReplicas: 1, maxReplicas: 2`); stop force-pinning productcatalog's replica count at run start
- [ ] Verify S1 / S2 / S5 / S6 still only need new numbers, not new mechanism — **confirmed during grilling**: `resolve_locust_phases()`/`switch_locust_phase()` are script-shape-agnostic, no further verification needed
- [ ] After HPA is implemented: note the productcatalog/frontend simultaneous-max-replica node-overcommit risk in `RON-NEZER-BASE-MIGRATION.md` (ADR-0005)

Resolved issues (previously open, now settled by the design doc):

- **S3 / S4 "targeted bottleneck"** — was `cpu_limit_fraction: 0.1` on the Ron-config-trimmed number (untested small absolutes: 61.5m/153.5m/15.5m, all different). **Now**: absolute `cpu_limit_millicores: 50` for all three, same value, matching the one CPU point each service has real `mu_sat` data for.
- **S4A vs. `productcatalogservice` HPA** — **now**: enable HPA on productcatalog universally (`maxReplicas: 2`), no mechanism change to the bottleneck cap itself (K8s CPU limits are per-pod-template regardless of replica count). Explicit, accepted node-overcommit risk if frontend and productcatalog are both maxed simultaneously — see ADR-0005.
- **S1 / S2 / S6 / S5** — confirmed: only need new numbers, no mechanism change.

---

## 3. Rewire the 16 scenario YAMLs

**Mechanics decided (2026-09-21)** — [2026-09-21-s1-s6-methodology-and-calibration-design.md](2026-09-21-s1-s6-methodology-and-calibration-design.md) §5. Only the actual numbers are still blocked on §1's battery (including its S1/S2/S6 system-load half); everything else below is decidable/executable independent of that.

- [ ] Point `locust.scripts` at `online_boutique_create_v2.sh` (drop `create2.sh`; no trickle-pattern replacement) — no code change needed, `run_scenario.py` already dual-exports `EMPTYCART`
- [ ] Update `scale_constraints` on S3 / S4A / S4B to `cpu_limit_millicores: 50` (ADR-0006) — mechanical once the new constraint kind (§2's checklist item 1) exists
- [ ] Write new `locust.user_counts` / `spawn_rate` from §1's completed battery (bottleneck-cap half for S3/S4A/S4B, system-load half for S1/S2/S6; S5's 4 files just inherit S6's numbers)
- [ ] Bump `log_folder` / `run_number` to new slots (these are new runs, not resumes) — use whatever's next-free at execution time, not a number fixed today

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
