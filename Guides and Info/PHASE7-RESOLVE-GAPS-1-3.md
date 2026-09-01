# Resolving Gaps 1 and 3 — What to Run Now

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Purpose:** A runbook for closing [Gap 1](PHASE7-DATA-GAPS.md#gap-1--no-re-enable-events-in-any-run-blocks-scenario-5) (no re-enable events, blocks Scenario 5) and [Gap 3](PHASE7-DATA-GAPS.md#gap-3--no-direct-retry-storm-evidence-retries-per-request) (no retries-per-request evidence) — the two gaps in [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) that still require **new scenario runs** (Gap 2/P99 was resolved by dropping the metric, no runs needed). This doc assumes the mechanisms for both gaps are already built and tested (recovery-phase `locust.phases`, `envoy_retry_collector.py`) — it's the "what to actually execute" checklist.
>
> **Before you run anything, read §1** — it verifies we actually have all the metrics the eval deck ([`Evaluating_RetryGuard_on_TopFull.md`](../context/Evaluating_RetryGuard_on_TopFull.md)) requires once these runs complete, and is honest about what stays open regardless.

---

## 1. Metric coverage verification (do this understanding before running anything)

### 1a. Slide 16's three measurement layers

| Layer | Deck requires | Status **after** Gaps 1 & 3 close | Status if you skip them |
|---|---|---|---|
| **Layer 1** — Goodput | ✅ Have it (`Goodput` column, all 38 runs) | ✅ Same | ✅ Same |
| **Layer 1** — API latency | ✅ Have it (`Latency95`; P99 dropped, see Gap 2) | ✅ Same | ✅ Same |
| **Layer 1** — API rejection rate | ✅ Have it (derived `Fail/RPS`, all 38 runs) | ✅ Same | ✅ Same |
| **Layer 1** — Retries per request | ❌ Missing in all 38 runs | ✅ **Closed** for whichever scenarios you re-run (§3) | ❌ Stays missing — headline hypothesis (slide 2) has no direct evidence |
| **Layer 2** — CPU/Memory limits | ❌ Missing in all 38 runs | ✅ **Closed** for whichever scenarios you re-run (collector enabled by default) | ❌ Stays missing |
| **Layer 2** — Pod instance counts | N/A by design (all services fixed at 1 replica, slide 6) | N/A | N/A |
| **Layer 3** — Per-service toggle timing | ✅ Have it (`retryguard.log` `ON→OFF`/`OFF→ON`) | ✅ Same | ✅ Same |
| **Layer 3** — Time-to-recovery intervals | ❌ No `OFF→ON` events exist to measure from | ✅ **Closed** for S6/S5 (§3, Tier 1) | ❌ Stays missing |

**Layer 2 (CPU/Memory) is now instrumented for new runs.** `resource_usage_collector.py` writes `resource_usage.csv` (CPU millicores + memory working set per service). The existing 38 matrix folders still lack it — same pattern as Gap 3. Pod replica counts in the CSV will be flat at `1` (fixed-replica design); autoscaling/over-scaling charts remain N/A.

### 1b. Slides 8–9 open questions

| Open question | Status today | Status after Tier 1 (§3) | Status after Tier 1 + Tier 2 (§3) |
|---|---|---|---|
| System-Level Gains | Answerable (goodput, P95, rejection) | Same, now also with direct retry evidence for **S6** | Same, across all scenarios |
| Topology Beneficiaries | Answerable (per-endpoint) | Same | Enriched — retry counts per service, not just goodput |
| Chain Propagation | Answerable, coarse (5 Locust endpoints only) | Enriched for S6 — Envoy CSVs show retries at `checkoutservice`'s *own* outbound calls | Enriched for S3/S4 too |
| Controller Interaction | Partial (`RPS` proxy; `num_agent.csv` empty — **stays partial**, out of scope) | Partial, but now has recovery-cycle data for **S6** (load drop), not for flat S2 | Same |
| Topology Position Sensitivity | Answerable (S4A vs S4B goodput/rejection) | Same | Enriched — retry-count comparison between shallow (S4A) and deep (S4B) bottlenecks |
| Interval Parameter Sensitivity | **Blocked** (Gap 1 — zero `OFF→ON` events) | **Unblocked** — this is the entire point of Tier 1 (S6 + S5) | Same |
| Combined Equilibrium | Weakened (no recovery phase ever reached under continued overload) | Answerable for **S6** — disable→recover→re-enable after a Locust load drop | Same |

**Conclusion: running Tier 1 (§3) is necessary and sufficient to unblock Interval Parameter Sensitivity and Combined Equilibrium (via Scenario 6's load-drop, not by changing Scenario 2) and to get Layer 1 retry-storm evidence for the recovery profile. Scenario 2 stays the deck's 10-minute hold — re-run it in Tier 2 if you want Envoy/resource CSVs on that shape. Tier 2 is optional polish for S1/S2/S3/S4 collectors.**

### 1c. A blocking issue was found and fixed while verifying this (2026-08-20)

Live validation against the actual cluster (not just unit tests) found that **Istio's default stats reduction hides `upstream_rq_retry*` counters** from the Envoy admin `/stats` endpoint — confirmed by `kubectl exec`-ing into `frontend`'s sidecar and finding zero `cluster.outbound.*` stat lines at all, even though the clusters were correctly configured (visible via `/clusters`). Without a fix, `envoy_retry_collector.py` would have run for the full 900s of every Tier-1/Tier-2 run and produced **syntactically valid but permanently all-zero CSVs** — a silent failure that would only have been caught after burning VM-hours.

**This has already been fixed, both live on the cluster and in the codebase:**
- `frontend` and `checkoutservice` Deployments were patched live with annotation `sidecar.istio.io/statsInclusionRegexps: cluster\.outbound.*upstream_rq.*` (one rollout restart each, already done).
- `run_scenario.py`'s `start_envoy_retry_collector()` now calls a new `ensure_envoy_stats_enabled()` before every run, reapplying this patch idempotently (no-op, no restart, once already applied) — so this fix survives a future cluster rebuild.
- `envoy_retry_collector.py` was deployed to master (`/home/idozacharia/experiments/envoy_retry_collector.py`) and smoke-tested directly: a live 8-second run produced correctly-formatted `envoy_retries_frontend.csv` / `envoy_retries_checkoutservice.csv` rows (all zero, as expected with no traffic running at the time).

Full writeup: [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 3. **You do not need to redo any of this** — it's a one-time cluster fix and it's already in place. It's documented here so you understand why the runs in §3 will actually work.

---

## 2. Prerequisites (verify before running anything)

```powershell
# 1. VMs up and cluster healthy
ssh topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
# All nodes Ready, all pods Running 2/2, all 10 VirtualServices present.

# 2. Confirm the stats-inclusion fix is still in place (should already be — see §1c)
ssh topfull-master "kubectl get deployment frontend -o jsonpath='{.spec.template.metadata.annotations.sidecar\.istio\.io/statsInclusionRegexps}'; echo"
ssh topfull-master "kubectl get deployment checkoutservice -o jsonpath='{.spec.template.metadata.annotations.sidecar\.istio\.io/statsInclusionRegexps}'; echo"
# Both should print: cluster\.outbound.*upstream_rq.*
# If either is empty, don't worry — run_scenario.py's ensure_envoy_stats_enabled()
# will reapply it automatically on your next run (adds ~15-20s for the rollout).

# 3. Confirm envoy_retry_collector.py is on master
ssh topfull-master "ls -la /home/idozacharia/experiments/envoy_retry_collector.py"
# Already deployed as of 2026-08-20. If missing (e.g. after a VM rebuild), redeploy:
#   scp experiments/envoy_retry_collector.py topfull-master:/home/idozacharia/experiments/

# 4. Local test suite still green (sanity check before spending VM time)
python experiments/test_run_scenario.py
python experiments/test_envoy_retry_collector.py
```

If the VMs were stopped, remember IPs are ephemeral — refresh `~/.ssh/config` per [CONNECT-VMS.md](CONNECT-VMS.md) before anything above will work.

---

## 3. Exact runs to execute

**Never use `run_all_scenarios.py` for any of the runs below.** Its `build_matrix()` targets hardcoded slots (`run1–3` for most scenarios, `run1–2` for S5) and `patch_config()` rewrites `run_number`/`log_folder` back to those slots before each run — for every config listed below, that would silently overwrite already-collected, already-accepted matrix data under the same folder name. Run each one individually:

```powershell
python experiments/run_scenario.py experiments/configs/<file>.yaml
```

Pull results after each run (the runner prints the exact command, but for reference):

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/<log_folder> experiments/results/
```

### Tier 1 — Required (closes Gap 1 fully; retry-storm evidence for Scenario 6 and Scenario 5)

These 6 configs carry the **Scenario 6** recovery-phase load (peak 0–300s, ~25% 300–900s, `duration_seconds: 900`) **and** collectors enabled. Scenario 2 is **not** in this list — S2 is the flat 600s hold again.

| # | Config | Slot | Duration | Closes |
|---|---|---|---|---|
| 1 | `scenario_6_recovery_baseline.yaml` | run1 (new) | 900s (~17 min incl. overhead) | S6 / S5 comparison baseline |
| 2 | `scenario_6_recovery_retryguard.yaml` | run1 (new) | 900s | S6 RetryGuard arm (paper-default interval); retries-per-request |
| 3 | `scenario_5_interval_10s.yaml` | run3 (free) | 900s | Interval sensitivity, interval=10s |
| 4 | `scenario_5_interval_20s.yaml` | run3 (free) | 900s | Interval sensitivity, interval=20s |
| 5 | `scenario_5_interval_30s.yaml` | run3 (free) | 900s | Interval sensitivity, interval=30s (same params as S6 RetryGuard) |
| 6 | `scenario_5_interval_60s.yaml` | run3 (free) | 900s | Interval sensitivity, interval=60s |

Total: ~6 × 17 min ≈ **1.7 hours sequential VM time**.

```powershell
python experiments/run_scenario.py experiments/configs/scenario_6_recovery_baseline.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_forced_recovery_run1 experiments/results/

python experiments/run_scenario.py experiments/configs/scenario_6_recovery_retryguard.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_forced_recovery_run1 experiments/results/

python experiments/run_scenario.py experiments/configs/scenario_5_interval_10s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_10s_run3 experiments/results/

python experiments/run_scenario.py experiments/configs/scenario_5_interval_20s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_20s_run3 experiments/results/

python experiments/run_scenario.py experiments/configs/scenario_5_interval_30s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_30s_run3 experiments/results/

python experiments/run_scenario.py experiments/configs/scenario_5_interval_60s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_60s_run3 experiments/results/
```

> **This is not guaranteed to trigger `OFF→ON` on the first try.** The recovery phase drops load to ~25% of peak, which *should* pull rejection back under RetryGuard's 20% threshold, but real system behavior can surprise you. **After each run, check immediately** (§4) before moving to the next one — if `OFF→ON` never fires even during the 300–900s recovery window, stop and re-read [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 1 remediation option 2 (soften the load further) rather than burning VM-hours on 5 more runs with the same problem.

### Tier 2 — Recommended, not required (retries-per-request evidence for Scenarios 1, 2, 3, 4A, 4B)

These configs do **not** need the recovery-phase load (S2 is the deck's flat hold). They need the Envoy + resource collectors, already enabled. `scenario_2_*`/`scenario_3_*`/`scenario_4*_*` sit on free `run4`; `scenario_1_*` needs a one-line bump first.

**Step A — bump Scenario 1 configs (required before running them, skip for S3/S4A/S4B):**

```yaml
# experiments/configs/scenario_1_baseline.yaml
run_number: 4                                                    # was 3
log_folder: baseline_topfull_no_retryguard_normal_op_run4         # was run3

# experiments/configs/scenario_1_retryguard.yaml
run_number: 4                                                    # was 3
log_folder: run_topfull_retryguard_normal_op_run4                 # was run3
```

**Step B — run all 10:**

| # | Config | Slot | Duration | Closes |
|---|---|---|---|---|
| 7 | `scenario_1_baseline.yaml` | run4 (after bump) | 300s | Retry-count parity for the sanity-check scenario (expect near-zero retries both arms) |
| 8 | `scenario_1_retryguard.yaml` | run4 (after bump) | 300s | Same, RetryGuard arm |
| 9 | `scenario_2_baseline.yaml` | run4 (free) | 600s | Retries-per-request on the **flat** S2 hold (deck intent) |
| 10 | `scenario_2_retryguard.yaml` | run4 (free) | 600s | Same, RetryGuard arm |
| 11 | `scenario_3_baseline.yaml` | run4 (free, as-is) | 600s | Retries-per-request at the targeted bottleneck |
| 12 | `scenario_3_retryguard.yaml` | run4 (free, as-is) | 600s | Same, RetryGuard arm |
| 13 | `scenario_4a_baseline.yaml` | run4 (free, as-is) | 600s | Retries-per-request, gateway-adjacent bottleneck |
| 14 | `scenario_4a_retryguard.yaml` | run4 (free, as-is) | 600s | Same, RetryGuard arm |
| 15 | `scenario_4b_baseline.yaml` | run4 (free, as-is) | 600s | Retries-per-request, deep-leaf bottleneck |
| 16 | `scenario_4b_retryguard.yaml` | run4 (free, as-is) | 600s | Same, RetryGuard arm |

Total: ~2×~7min + 8×~11.5min ≈ **1.8 hours sequential VM time**.

```powershell
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
python experiments/run_scenario.py experiments/configs/scenario_1_retryguard.yaml
python experiments/run_scenario.py experiments/configs/scenario_2_baseline.yaml
python experiments/run_scenario.py experiments/configs/scenario_2_retryguard.yaml
python experiments/run_scenario.py experiments/configs/scenario_3_baseline.yaml
python experiments/run_scenario.py experiments/configs/scenario_3_retryguard.yaml
python experiments/run_scenario.py experiments/configs/scenario_4a_baseline.yaml
python experiments/run_scenario.py experiments/configs/scenario_4a_retryguard.yaml
python experiments/run_scenario.py experiments/configs/scenario_4b_baseline.yaml
python experiments/run_scenario.py experiments/configs/scenario_4b_retryguard.yaml
# Pull each with scp as shown in Tier 1, using the log_folder from each config.
```

> These 10 runs are a genuinely new 4th repeat for scenarios that already have 3 solid repeats — they don't replace or invalidate the existing run1–3 goodput/rejection data, they add a retry-count dimension the earlier 3 repeats can't have (they predate the collector). It's fine — and expected — for goodput numbers in this run4 to differ slightly from run1–3 due to Locust's inherent randomness; only use run4 for the retry-count analysis, keep using run1–3 (or run1-3 + run4 pooled) for goodput/latency/rejection.

---

## 4. Verifying each run actually produced what you need

**Immediately after each Tier 1 run — check for `OFF→ON`:**

```powershell
Get-Content "experiments\results\<log_folder>\retryguard.log" |
  Where-Object { $_ -match 'OFF→ON|ON→OFF' }
```

You want to see at least one `ON→OFF` (during 0–300s, expected — matches the existing matrix) **and at least one `OFF→ON`** (during 300–900s, this is the new signal Gap 1 was blocking on). If you see zero `OFF→ON` lines, the recovery phase didn't pull rejection under threshold for that config — see the note in §3 Tier 1.

**After every run (Tier 1 or 2) — check the Envoy CSVs are non-trivial:**

```powershell
python -c "
import csv, pathlib
p = pathlib.Path('experiments/results/<log_folder>')
for f in ['envoy_retries_frontend.csv', 'envoy_retries_checkoutservice.csv']:
    rows = list(csv.DictReader((p/f).open()))
    totals = [int(r['upstream_rq_total']) for r in rows]
    retries = [int(r['upstream_rq_retry']) for r in rows]
    print(f'{f}: {len(rows)} rows, max_total={max(totals) if totals else 0}, max_retry={max(retries) if retries else 0}')
"
```

`max_total` should be well above zero (confirms traffic was actually flowing through that caller during the run) once you substitute the real `<log_folder>` name. `max_retry` should also be non-zero for **baseline** runs under overload (Istio's default retries are on) and should visibly stay lower — or flatten out after the `ON→OFF` timestamp — in **RetryGuard** runs on the toggled service. If `max_total` is `0` across the whole run, the stats-inclusion fix (§1c) did not take effect for that pod — re-check §2 step 2 before trusting the run.

---

## 5. After all runs are pulled down

1. Update [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md): move Gap 1 and Gap 3 from "configs updated, not yet run" to closed, with the new run folder names and a summary of what the `OFF→ON` events / retry CSVs actually showed.
2. Update the "What remains answerable" table in that same doc — Scenario 5 should move from **None** to **Full** (or partial, if some interval configs still didn't recover); Scenario 6 should appear as the recovery-cycle pair. Scenario 2 stays **Partial** unless a later run shows re-enable under a *flat* hold.
3. Update `AGENTS.md` §4 "Current status" — the matrix is no longer "38 runs" once these land; note the new total and that it now includes recovery-phase and retry-count data.
4. Commit the new `experiments/results/<log_folder>/` folders the same way the original 38 were committed.

---

## 6. What stays open even after this (be upfront about it)

- **Layer 2 — CPU/Memory per pod.** Instrumented for new runs via `resource_usage_collector.py` → `resource_usage.csv`. Still absent from the existing 38 matrix folders. Replica-count time series remains N/A (all services fixed at 1 replica).
- **`num_agent.csv` still empty.** TopFull's internal admission state remains unrecorded; Controller Interaction stays "Partial" even after Gaps 1 & 3 close. `RPS` from the endpoint CSVs remains the best available proxy.
- **Shallow-topology caveat (slide 14) is unchanged** — S4A/S4B retry-count data will be genuinely useful, but the deck's own caveat about this being a small topology still applies to any conclusions drawn from it.

---

*Related: [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) (full gap analysis this runbook resolves), [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) (CSV formats, including the new Envoy files, §5), [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md) (runner internals), [HOW-TO-RUN-EXPERIMENTS.md](HOW-TO-RUN-EXPERIMENTS.md) (general run-and-read-results walkthrough).*
