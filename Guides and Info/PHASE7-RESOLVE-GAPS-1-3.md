# Resolving Gaps 1 and 3 — What to Run Now

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Purpose:** Runbook for closing [Gap 1](PHASE7-DATA-GAPS.md#gap-1--no-re-enable-events-in-any-run-blocks-scenario-5) and [Gap 3](PHASE7-DATA-GAPS.md#gap-3--no-direct-retry-storm-evidence-retries-per-request). **The campaign is complete (48/48, 2026-09-06)** — this file is now the record of what was run, how to verify a folder, and what stays open. Analysis uses `experiments/results/campaign_48/`.
>
> **Decision (2026-09-04): paper-grade single campaign — 48 new runs, all collectors on, 3 repeats.** Do **not** replay the old 38 (eight of those slots are flat-hold S5, which cannot answer interval sensitivity). Do **not** bolt collectors onto a 16-run add-on and mix August goodput with September retries. Primary Phase 7 analysis uses this campaign (`experiments/results/campaign_48/`); the August 38 folders stay as `experiments/results/august_38/`. **Campaign COMPLETE 2026-09-06 (48/48).** See §3c.
>
> **Post-campaign reorg (2026-09-06):** all 48 run folders below were later nested one level deeper, into a scenario subfolder each (`S1_normal_op/`, `S2_sustained_overload/`, `S3_targeted_bottleneck/`, `S4A_topology_position_A/`, `S4B_topology_position_B/`, `S5_interval_tuning/`, `S6_forced_recovery/`). The `scp` commands and paths quoted in this runbook predate that move — when following them today, add the matching scenario subfolder to the local destination (e.g. `experiments/results/campaign_48/S6_forced_recovery/`). See [experiments/results/campaign_48/README.md](../experiments/results/campaign_48/README.md) for the full map.
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

Pull after each run (the runner prints the exact command). Locally, campaign folders live under `experiments/results/campaign_48/`:

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/<log_folder> experiments/results/campaign_48/
```

Then bump `run_number` and `log_folder` in that YAML **before** the next repeat of the same config.

### 3a. Matrix — 48 new folders on the next free slots — **COMPLETE (2026-09-06)**

| Scenario | Configs | Slots used | Repeats | Duration | Count | Status |
|---|---|---|---|---|---|---|
| 6 Forced Recovery | `scenario_6_recovery_{baseline,retryguard}.yaml` | run1–3 | ×3 both arms | 900s | 6 | Done |
| 5 Interval Tuning | `scenario_5_interval_{10,20,30,60}s.yaml` | run3–5 (run1–2 are the old flat S5 in `august_38/`) | ×3, RetryGuard only | 900s | 12 | Done |
| 1 Normal Operation | `scenario_1_{baseline,retryguard}.yaml` | run4–6 | ×3 both arms | 300s | 6 | Done |
| 2 Sustained Overload | `scenario_2_{baseline,retryguard}.yaml` | run4–6 | ×3 both arms | 600s | 6 | Done |
| 3 Targeted Bottleneck | `scenario_3_{baseline,retryguard}.yaml` | run4–6 | ×3 both arms | 600s | 6 | Done |
| 4A Topology A | `scenario_4a_{baseline,retryguard}.yaml` | run4–6 | ×3 both arms | 600s | 6 | Done |
| 4B Topology B | `scenario_4b_{baseline,retryguard}.yaml` | run4–6 | ×3 both arms | 600s | 6 | Done |

**Total: 48 / 48.** All folders local under `experiments/results/campaign_48/`. S5 compares against **S6 baseline**, not S2.

**YAML state as of 2026-09-06:** S1–S4 point at run7; S5 at run6. **S6 YAMLs still point at completed run3** — bump both S6 files to run4 before any extra S6 run, or they will overwrite on master.

```yaml
# experiments/configs/scenario_6_recovery_baseline.yaml  — bump before any extra S6 run
run_number: 4
log_folder: baseline_topfull_no_retryguard_forced_recovery_run4
```

### 3b. Pre-campaign metric verification (do this before the other 46)

These two S6 `run1` folders are the **first two of the 48**, not extra smoke. They are the only two-run set that exercises every old metric and every new collector, including `OFF→ON`.

**Do not substitute other scenarios for this gate:**

- **Not Scenario 1.** Under normal load retries are near zero, so all-zero Envoy CSVs look exactly like the Istio stats-inclusion bug (§1c) — a silent false pass.
- **Not Scenario 2.** Flat overload can show retries, but it will not produce `OFF→ON`. That leaves Gap 1 unchecked.

**Procedure:**

1. Complete §2 (cluster healthy, stats-inclusion annotation present, local unit tests green). Refresh SSH `HostName` if the VMs were restarted.
2. Run **S6 baseline run1** only:

```powershell
python experiments/run_scenario.py experiments/configs/scenario_6_recovery_baseline.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_forced_recovery_run1 experiments/results/campaign_48/
```

3. Immediately run §4 on that folder: Locust CSVs populated; `envoy_retries_*.csv` with `max_total` **and** `max_retry` well above zero (Istio retries stay on in baseline — this proves the stats fix under traffic); `resource_usage.csv` has rows.
4. Run **S6 RetryGuard run1**:

```powershell
python experiments/run_scenario.py experiments/configs/scenario_6_recovery_retryguard.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_forced_recovery_run1 experiments/results/campaign_48/
```

5. Immediately run §4 on that folder: at least one `ON→OFF` (0–300s) **and** at least one `OFF→ON` (300–900s); Envoy + resource files present.
6. **If step 5 has no `OFF→ON`: stop.** Do not run the remaining 46. Soften the recovery-phase load ([PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 1 remediation option 2). Document the failure before burning more VM time.
7. **If both runs pass:** the campaign metrics path is live. Continue with S6 run2–3, then S5, then S1–S4 (§3a). After every later run: pull, §4, bump YAML.

> The recovery phase drops load to ~25% of peak, which *should* pull rejection under RetryGuard's 20% threshold. Real system behavior can surprise you — that is why step 6 is a hard gate, not a note at the end.

**Gate outcome (2026-09-04): PASSED.** Folders `baseline_topfull_no_retryguard_forced_recovery_run1` and `run_topfull_retryguard_forced_recovery_run1` are local under `experiments/results/campaign_48/`.

- Baseline: Locust ~810 rows/endpoint; `envoy_retries_frontend.csv` `max_total=739010`, `max_retry=120` (stats-inclusion live under traffic); `resource_usage.csv` ~1964 rows.
- RetryGuard: 3× `ON→OFF` (cart / checkout / productcatalog during peak) then 3× `OFF→ON` after the load drop (`cartservice` and `productcatalogservice` first, `checkoutservice` later once rejection hit 0); Envoy + resource CSVs present. Campaign metrics path is live. Campaign later finished through run3; **S6 YAMLs were left at run3** — bump to run4 before any extra S6 run (§3a).

### 3c. Campaign complete (2026-09-06)

**Progress: 48 / 48.** Gate §3b stayed closed; every later run was pulled into `experiments/results/campaign_48/` and §4-verified.

Do not re-run this matrix. Next work is Phase 7 analysis on `campaign_48/` (see §5). Extra runs, if any, must use the next free YAML slots (S1–S4 run7, S5 run6; **bump S6 off run3 first**).

## 4. Verifying each run actually produced what you need

**Immediately after each S6 / S5 RetryGuard run — check for `OFF→ON`:**

```powershell
Get-Content "experiments\results\campaign_48\<log_folder>\retryguard.log" |
  Where-Object { $_ -match 'OFF→ON|ON→OFF' }
```

You want at least one `ON→OFF` (during 0–300s, expected) **and at least one `OFF→ON`** (during 300–900s — this is the Gap 1 signal). If you see zero `OFF→ON` lines, the recovery phase did not pull rejection under threshold — see §3b step 6.

**After every run — check the Envoy CSVs are non-trivial:**

```powershell
python -c "
import csv, pathlib
p = pathlib.Path('experiments/results/campaign_48/<log_folder>')
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

1. ~~Update [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md): move Gap 1 and Gap 3 to closed~~ **Done (2026-09-06).** Campaign `OFF→ON` / Envoy summary is in that doc.
2. ~~Update the "What remains answerable" table~~ **Done.** S5 is Full on the campaign (recovery load); S6 is Full ×3; S2 stays Partial on re-enable-under-flat-hold.
3. ~~Update `AGENTS.md` §4~~ **Done.** Campaign is the primary dataset; August 38 is `august_38/`.
4. **Still open:** commit `experiments/results/campaign_48/` (and the `git mv` of August folders into `august_38/`) the same way the original 38 were committed. Do not replace or delete `august_38/`.

---

## 6. What stays open even after this (be upfront about it)

- **August 38 still lack Envoy / resource CSVs.** That is expected. They live under `experiments/results/august_38/`. Do not back-fill them; `campaign_48/` is the analysis dataset.
- **Layer 2 — pod instance counts.** Replica-count time series remains N/A (all services fixed at 1 replica).
- **`num_agent.csv` still empty.** TopFull's internal admission state remains unrecorded; Controller Interaction stays "Partial" even after Gaps 1 & 3 close. `RPS` from the endpoint CSVs remains the best available proxy.
- **Shallow-topology caveat (slide 14) is unchanged** — S4A/S4B retry-count data will be genuinely useful, but the deck's own caveat about this being a small topology still applies to any conclusions drawn from it.

---

*Related: [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) (full gap analysis this runbook resolves), [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) (CSV formats, including the new Envoy files, §5), [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md) (runner internals), [HOW-TO-RUN-EXPERIMENTS.md](HOW-TO-RUN-EXPERIMENTS.md) (general run-and-read-results walkthrough).*
