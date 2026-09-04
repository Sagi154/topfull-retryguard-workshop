# Resolving Gaps 1 and 3 — What to Run Now

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Purpose:** A runbook for closing [Gap 1](PHASE7-DATA-GAPS.md#gap-1--no-re-enable-events-in-any-run-blocks-scenario-5) (no re-enable events, blocks Scenario 5) and [Gap 3](PHASE7-DATA-GAPS.md#gap-3--no-direct-retry-storm-evidence-retries-per-request) (no retries-per-request evidence) — the two gaps in [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) that still require **new scenario runs** (Gap 2/P99 was resolved by dropping the metric, no runs needed). This doc assumes the mechanisms for both gaps are already built and tested (recovery-phase `locust.phases`, `envoy_retry_collector.py`) — it's the "what to actually execute" checklist.
>
> **Decision (2026-09-04): paper-grade single campaign — 48 new runs, all collectors on, 3 repeats.** Do **not** replay the old 38 (eight of those slots are flat-hold S5, which cannot answer interval sensitivity). Do **not** bolt collectors onto a 16-run add-on and mix August goodput with September retries. Primary Phase 7 analysis uses this campaign; the August 38 folders stay in git as historical data. See §3.
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
| **Layer 1** — Retries per request | ❌ Missing in all 38 runs | ✅ **Closed** for the 48-run campaign (§3) | ❌ Stays missing — headline hypothesis (slide 2) has no direct evidence |
| **Layer 2** — CPU/Memory limits | ❌ Missing in all 38 runs | ✅ **Closed** for the 48-run campaign (collector enabled by default) | ❌ Stays missing |
| **Layer 2** — Pod instance counts | N/A by design (all services fixed at 1 replica, slide 6) | N/A | N/A |
| **Layer 3** — Per-service toggle timing | ✅ Have it (`retryguard.log` `ON→OFF`/`OFF→ON`) | ✅ Same | ✅ Same |
| **Layer 3** — Time-to-recovery intervals | ❌ No `OFF→ON` events exist to measure from | ✅ **Closed** for S6/S5 (§3) | ❌ Stays missing |

**Layer 2 (CPU/Memory) is now instrumented for new runs.** `resource_usage_collector.py` writes `resource_usage.csv` (CPU millicores + memory working set per service). The existing 38 matrix folders still lack it — same pattern as Gap 3. Pod replica counts in the CSV will be flat at `1` (fixed-replica design); autoscaling/over-scaling charts remain N/A.

### 1b. Slides 8–9 open questions

| Open question | Status today (August 38) | Status after the 48-run campaign (§3) |
|---|---|---|
| System-Level Gains | Answerable (goodput, P95, rejection) | Same, now with direct retry + CPU/memory evidence from the **same** runs |
| Topology Beneficiaries | Answerable (per-endpoint) | Enriched — retry counts per service, not just goodput |
| Chain Propagation | Answerable, coarse (5 Locust endpoints only) | Enriched — Envoy CSVs show retries at `checkoutservice`'s *own* outbound calls |
| Controller Interaction | Partial (`RPS` proxy; `num_agent.csv` empty — **stays partial**, out of scope) | Partial, but now has recovery-cycle data for **S6** (load drop). Flat S2 still will not re-enable under continued overload |
| Topology Position Sensitivity | Answerable (S4A vs S4B goodput/rejection) | Enriched — retry-count comparison between shallow (S4A) and deep (S4B) bottlenecks |
| Interval Parameter Sensitivity | **Blocked** (Gap 1 — zero `OFF→ON` events) | **Unblocked** — S6 + S5 on the recovery load, 3 repeats |
| Combined Equilibrium | Weakened (no recovery phase ever reached under continued overload) | Answerable for **S6** — disable→recover→re-enable after a Locust load drop |

**Conclusion:** the 48-run campaign in §3 is the chosen close-out. It unblocks Interval Parameter Sensitivity and Combined Equilibrium (via Scenario 6's load-drop, **not** by changing Scenario 2), and it puts every Layer 1–2 series on the same runs as goodput / P95 / rejection so overlays are honest. Scenario 2 stays the deck's 10-minute flat hold. An earlier draft of this runbook split the work into a 6-run "Tier 1" plus a 10-run "Tier 2" add-on; that is **superseded** (2026-09-04).

### 1c. A blocking issue was found and fixed while verifying this (2026-08-20)

Live validation against the actual cluster (not just unit tests) found that **Istio's default stats reduction hides `upstream_rq_retry*` counters** from the Envoy admin `/stats` endpoint — confirmed by `kubectl exec`-ing into `frontend`'s sidecar and finding zero `cluster.outbound.*` stat lines at all, even though the clusters were correctly configured (visible via `/clusters`). Without a fix, `envoy_retry_collector.py` would have run for the full duration of every campaign run and produced **syntactically valid but permanently all-zero CSVs** — a silent failure that would only have been caught after burning VM-hours.

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

# 3. Collectors — the runner copies retryguard.py / envoy_retry_collector.py /
#    resource_usage_collector.py from this repo onto master at the start of
#    each run. No manual scp. Confirm the local files exist:
#      experiments/retryguard.py
#      experiments/envoy_retry_collector.py
#      experiments/resource_usage_collector.py
#    If deploy fails with Permission denied, the dest file is owned by another
#    user and passwordless sudo is missing — see AGENTS.md §7.

# 4. Local test suite still green (sanity check before spending VM time)
python experiments/test_run_scenario.py
python experiments/test_envoy_retry_collector.py
```

If the VMs were stopped, remember IPs are ephemeral — refresh `~/.ssh/config` per [CONNECT-VMS.md](CONNECT-VMS.md) before anything above will work.

---

## 3. Paper-grade campaign (48 runs) — this is the plan of record

**Chosen 2026-09-04.** One new campaign, all collectors on, three repeats, so every metric (goodput, P95, rejection, retries-per-request, CPU/memory, toggle timing, time-to-recovery) comes from the **same** runs. Locust is non-deterministic; three repeats give interval sensitivity the same noise treatment as S1–S4.

This is **not** a replay of the August 38:

- Eight of those slots are Scenario 5 on a **flat** overload (3 disables, 0 re-enables). Repeating them with collectors still cannot answer interval sensitivity.
- Scenario 6 did not exist in that matrix. Recovery lives on S6 + S5-with-S6-load; S2 stays the deck's flat 600s hold.
- The Envoy stats-inclusion annotation (see §1c) was applied after the August 38. New runs carry it; mixing August goodput with a later retry series would also split those overlays across two Istio-stats configs.

Keep the August 38 folders in git. Do not delete them and do not overwrite them. Primary Phase 7 writeup uses **this** campaign. The old S5 runs remain a valid negative result: under saturating flat overload, re-enable never fired.

**Never use `run_all_scenarios.py` for any of the runs below.** Its `build_matrix()` targets hardcoded slots (`run1–3` for most scenarios, `run1–2` for S5) and `patch_config()` rewrites `run_number`/`log_folder` back to those slots before each run — that would silently overwrite the finished August matrix. Run each YAML individually:

```powershell
python experiments/run_scenario.py experiments/configs/<file>.yaml
```

Pull after each run (the runner prints the exact command):

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/<log_folder> experiments/results/
```

Then bump `run_number` and `log_folder` in that YAML **before** the next repeat of the same config.

### 3a. Matrix — 48 new folders on the next free slots

| Scenario | Configs | New slots | Repeats | Duration | Count |
|---|---|---|---|---|---|
| 6 Forced Recovery | `scenario_6_recovery_{baseline,retryguard}.yaml` | run1–3 (never existed) | ×3 both arms | 900s | 6 |
| 5 Interval Tuning | `scenario_5_interval_{10,20,30,60}s.yaml` | run3–5 (run1–2 are the old flat S5 — do not reuse) | ×3, RetryGuard only | 900s | 12 |
| 1 Normal Operation | `scenario_1_{baseline,retryguard}.yaml` | run4–6 (**bump from run3 before the first S1 run**) | ×3 both arms | 300s | 6 |
| 2 Sustained Overload | `scenario_2_{baseline,retryguard}.yaml` | run4–6 (YAML already at run4) | ×3 both arms | 600s | 6 |
| 3 Targeted Bottleneck | `scenario_3_{baseline,retryguard}.yaml` | run4–6 (YAML already at run4) | ×3 both arms | 600s | 6 |
| 4A Topology A | `scenario_4a_{baseline,retryguard}.yaml` | run4–6 (YAML already at run4) | ×3 both arms | 600s | 6 |
| 4B Topology B | `scenario_4b_{baseline,retryguard}.yaml` | run4–6 (YAML already at run4) | ×3 both arms | 600s | 6 |

**Total: 48 runs** (S1 + S2 + S3 + S4A + S4B + S6 = 6 two-arm shapes × 2 × 3 = 36; S5 = 4 intervals × 3 = 12). Sequential VM time ≈ **10–11 hours** (startup overhead ~90s on top of `duration_seconds`). S5 compares against **S6 baseline**, not S2.

YAML state as of 2026-09-04: S1 still points at last-completed `run3` — bump both S1 files to `run4` before touching them. S2/S3/S4 already point at `run4`. S5 already points at `run3`. S6 already points at `run1`.

```yaml
# experiments/configs/scenario_1_baseline.yaml  — do this before any S1 campaign run
run_number: 4
log_folder: baseline_topfull_no_retryguard_normal_op_run4

# experiments/configs/scenario_1_retryguard.yaml
run_number: 4
log_folder: run_topfull_retryguard_normal_op_run4
```

### 3b. Execution order (gate on `OFF→ON` before burning S5)

1. **S6 baseline run1, then S6 RetryGuard run1.** Verify §4 immediately on the RetryGuard folder.
2. **If `OFF→ON` did not fire** during the 300–900s recovery window: **stop.** Do not run the remaining 46. Re-read [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 1 remediation option 2 (soften the recovery-phase load) rather than repeating a profile that cannot exercise re-enable.
3. **If it did fire:** finish S6 (both arms, run2–3), then S5 (four intervals × run3–5), then S1–S4 (each arm × run4–6). After every run: pull, §4 checks, bump YAML.

Example for the first two (repeat the pattern; substitute the `log_folder` from the YAML you just ran):

```powershell
python experiments/run_scenario.py experiments/configs/scenario_6_recovery_baseline.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_forced_recovery_run1 experiments/results/

python experiments/run_scenario.py experiments/configs/scenario_6_recovery_retryguard.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_forced_recovery_run1 experiments/results/
```

> The recovery phase drops load to ~25% of peak, which *should* pull rejection under RetryGuard's 20% threshold. Real system behavior can surprise you — that is why step 2 is a hard gate, not a note at the end.

---

## 4. Verifying each run actually produced what you need

**Immediately after each S6 / S5 RetryGuard run — check for `OFF→ON`:**

```powershell
Get-Content "experiments\results\<log_folder>\retryguard.log" |
  Where-Object { $_ -match 'OFF→ON|ON→OFF' }
```

You want at least one `ON→OFF` (during 0–300s, expected) **and at least one `OFF→ON`** (during 300–900s — this is the Gap 1 signal). If you see zero `OFF→ON` lines, the recovery phase did not pull rejection under threshold — see §3b step 2.

**After every run — check the Envoy CSVs are non-trivial:**

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

`max_total` should be well above zero (traffic actually flowed through that caller). `max_retry` should be non-zero for **baseline** runs under overload (Istio's default retries are on) and should stay lower — or flatten after the `ON→OFF` timestamp — in **RetryGuard** runs on the toggled service. If `max_total` is `0` across the whole run, the stats-inclusion fix (§1c) did not take effect — re-check §2 step 2 before trusting the run.

**After every run — confirm `resource_usage.csv` exists and has rows** (`cpu_millicores` / `memory_working_set_bytes` per service). `replica_count` will be `1` everywhere (fixed-replica design).

---

## 5. After all runs are pulled down

1. Update [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md): move Gap 1 and Gap 3 from "configs updated, not yet run" to closed, with the new run folder names and a summary of what the `OFF→ON` events / retry CSVs actually showed.
2. Update the "What remains answerable" table in that same doc — Scenario 5 should move from **None** to **Full** (or partial, if some interval configs still didn't recover); Scenario 6 should appear as the recovery-cycle pair. Scenario 2 stays **Partial** on re-enable-under-flat-hold unless a later run shows it (not expected; not a campaign goal).
3. Update `AGENTS.md` §4 "Current status" — note the 48-run campaign is in, that Phase 7 analysis uses it as the primary dataset, and that the August 38 remains historical.
4. Commit the new `experiments/results/<log_folder>/` folders the same way the original 38 were committed. Do not replace or delete the August folders.

---

## 6. What stays open even after this (be upfront about it)

- **August 38 still lack Envoy / resource CSVs.** That is expected. Do not back-fill them; the campaign replaces them as the analysis dataset.
- **Layer 2 — pod instance counts.** Replica-count time series remains N/A (all services fixed at 1 replica).
- **`num_agent.csv` still empty.** TopFull's internal admission state remains unrecorded; Controller Interaction stays "Partial" even after Gaps 1 & 3 close. `RPS` from the endpoint CSVs remains the best available proxy.
- **Shallow-topology caveat (slide 14) is unchanged** — S4A/S4B retry-count data will be genuinely useful, but the deck's own caveat about this being a small topology still applies to any conclusions drawn from it.

---

*Related: [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) (full gap analysis this runbook resolves), [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) (CSV formats, including the new Envoy files, §5), [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md) (runner internals), [HOW-TO-RUN-EXPERIMENTS.md](HOW-TO-RUN-EXPERIMENTS.md) (general run-and-read-results walkthrough).*
