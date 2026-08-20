# Phase 7 — Data Gaps in the Completed Matrix

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Scope:** Three gaps found on 2026-08-20 while auditing the finished 38-run matrix against the deliverables promised in [`context/Evaluating_RetryGuard_on_TopFull.md`](../context/Evaluating_RetryGuard_on_TopFull.md) (slides 8–9 open questions, slides 11–15 scenario objectives, slide 16 measurement layers). Gap 2 was resolved the same day by dropping P99 as a target metric (see below) — it was a self-imposed target from `WORKPLAN.md`, not something either source paper or the deck actually requires. Gap 3's *collector* was built the same day (see below) but the existing 38 folders still lack retry-count series until scenarios are re-run with it.
>
> All 38 run folders are present locally and structurally valid — five endpoint CSVs, `total.csv`, `num_agent.csv`, `run_manifest.json`, plus `retryguard.log` on RetryGuard runs. See [PHASE5-PHASE6-RUNLIST.md](PHASE5-PHASE6-RUNLIST.md) for the inventory. The gaps below are about *which metrics those files contain*, not about missing folders.
>
> **Bottom line:** 30 of 38 runs support the analysis as designed for goodput / P95 / rejection. The 8 Scenario 5 runs do not (Gap 1). Retries-per-request (Gap 3) is instrumented going forward but absent from the existing matrix; P99 latency (Gap 2) is no longer considered required.

---

## Gap 1 — No re-enable events in any run (blocks Scenario 5)

**What the data shows.** Across all 23 RetryGuard runs there are **60 disable events (`ON→OFF`) and zero re-enable events (`OFF→ON`)**.

| Run group | Runs | Disables per run | Re-enables per run |
|---|---|---|---|
| S1 RetryGuard (normal op) | 3 | 0 | 0 |
| S2 / S3 / S4A / S4B RetryGuard | 12 | 3 | 0 |
| S5 interval sweep (10/20/30/60s) | 8 | 3 | 0 |

Every overload run has the same shape: `cartservice`, `checkoutservice` and `productcatalogservice` all cross the 20% threshold and get disabled within the first 1–3 minutes, then stay `OFF` until `SHUTDOWN`. Rejection never falls back under the threshold — the final `OBSERVE` window of each run still reports 0.75–1.00 rejection with `low=0`.

Example (`run_topfull_retryguard_interval_60s_run1`):

```
18:51:03Z  checkoutservice        ON→OFF  rejection=0.88  consecutive_high=2
18:51:33Z  cartservice            ON→OFF  rejection=0.80  consecutive_high=2
18:51:33Z  productcatalogservice  ON→OFF  rejection=0.71  consecutive_high=2
...
19:00:04Z  OBSERVE  checkoutservice  rejection=1.0000  low=0 high=20  state=OFF
19:00:34Z  SHUTDOWN  signal=15
```

**Impact.**

- **Scenario 5 is unanswerable.** Its objective is to find the optimal *re-enable* interval, and `re_enable_windows` only governs the `OFF→ON` transition. All four interval configs produced byte-identical controller behavior (3 disables, 0 re-enables), so there is nothing to compare. "Interval Parameter Sensitivity" (slide 9) has no signal.
- **Scenario 2's objective is partly unmet.** Slide 12 claims the long hold "allows the complete **disable → recover → re-enable** cycle to fire." The disable half fired; recover and re-enable did not.
- **"Combined Equilibrium" (slide 9) is weakened.** The question of whether TopFull re-admitting traffic undoes RetryGuard's gains needs a recovery phase that was never reached.

**Why.** Not a plumbing bug. The offered overload was deep enough that suppressing retries could not pull rejection under 20% — TopFull keeps throttling, rejection stays ~80–100%, and RetryGuard's `consecutive_low` counter never advances. This was already visible during readiness (2026-08-07, Step 6: "OFF→ON did not fire under sustained 100m overload") and was not treated as blocking at the time.

**Remediation (requires new runs — no collector fix helps).** Options, roughly in order of cost:

1. **Add a recovery phase** to the S5 load profile: hold ρ>1 long enough to trigger disable, then drop load back under capacity so rejection falls and the interval parameter actually gets exercised. This is the closest match to the paper's intent and to slide 15.
2. **Soften the overload** for S5 only (lower peak RPS, or a looser CPU limit) so rejection oscillates around the 20% threshold instead of saturating.
3. **Reframe the deliverable** — report Scenario 5 as a negative result: under sustained saturating overload alongside TopFull, the re-enable interval is inert because recovery never occurs. Honest and defensible, but does not answer the original question.

**Status (implementation):** The generic mechanism exists — `experiments/run_scenario.py` supports an optional `locust.phases` list (see `PHASE5-EXPERIMENTS-GUIDE.md` §"YAML config schema") that changes offered load mid-run by killing and relaunching Locust at a new level. It is covered by unit tests in `experiments/test_run_scenario.py`.

**Configs updated (2026-08-20), not yet run.** `scenario_2_baseline.yaml`, `scenario_2_retryguard.yaml`, and all four `scenario_5_interval_{10,20,30,60}s.yaml` now carry an identical two-phase load profile — hold the original peak load for 300s (long enough to trigger disable, per the matrix data), then drop to ~25% of peak for the remaining 600s of an extended 900s run (`duration_seconds: 600 → 900`) so rejection can fall under threshold and `re_enable_windows` gets exercised. The phase schedule is byte-identical across all six files (S3/S4 were left untouched — their objectives per `Evaluating_RetryGuard_on_TopFull.md` slides 13–14 don't depend on a recover→re-enable cycle). `retryguard:` block settings (threshold, `disable_windows`, per-config `re_enable_windows`) are unchanged so the four S5 configs stay comparable and S2's baseline/RetryGuard pair stays comparable.

**How to actually run these.** `scenario_2_baseline.yaml`/`scenario_2_retryguard.yaml` were bumped to `run_number: 4` (runs 1–3 already exist on disk); the four S5 configs stayed at `run_number: 3` (their next unused slot). Run each manually — `python experiments/run_scenario.py experiments/configs/scenario_2_baseline.yaml` etc. — **do not** invoke these six via `run_all_scenarios.py`'s batch matrix: `build_matrix()` is hardcoded to target `run1–3` (S2) / `run1–2` (S5) and `patch_config()` rewrites `run_number`/`log_folder` back to those slots before each run, which would silently overwrite the already-collected flat-overload data at those slots with the new 900s/recovery-phase data under the same folder names.

---

## Gap 2 — P99 latency was never collected (RESOLVED — dropped, P95 is the metric of record)

**What the data shows.** `Latency99` is `0.0` in **every row of every CSV across all 38 runs** (verified on `total.csv`, `postcheckout.csv`, `getproduct.csv`).

**Root cause.** Upstream in TopFull's `metric_collector.py`. Its Locust query returns three values, and the 99th percentile is hardcoded — the four-value unpack is commented out. Visible in the patch source at [`experiments/patch_metric_collector.py`](../experiments/patch_metric_collector.py) lines 27–29:

```python
# rps, fail, latency95, latency99 = metric[api]
rps, fail, latency95 = metric[api]
latency99 = 0
```

`total.csv` then averages that column, so it is zero there too. Our `patch_metric_collector.py` only wrapped the loop in try/except; it did not touch this.

**Resolution (2026-08-20): P99 is dropped as a target metric — it was never actually required.** Checked against all three source-of-truth documents:

- **Neither source paper reports a latency percentile at all.** RetryGuard's evaluation (Section 6, Table 1, Figs. 9–12) is built entirely on **average/mean latency** ("average latency dropped to 4.02 seconds," Sec. 6.2) — no percentile of any kind appears in the paper. TopFull uses the phrase "percentile latency" only as an internal RL state feature / SLO-violation signal (Sec. 4.3, Eq. 3) — it never names a specific percentile and never plots one as a reported evaluation result; TopFull's headline metric is goodput.
- **The eval deck** (`context/Evaluating_RetryGuard_on_TopFull.md`, slide 16, Layer 1) only requires generic **"API latency"** — no percentile specified.
- "P99" as a specific target came from this workshop's own internal planning docs (`WORKPLAN.md`), not from either paper or the deck — it was a self-imposed target, not a derived requirement.

So `Latency95` — which is real and responsive across the matrix (roughly 570–630 ms in normal operation up to ~3100 ms in the S4A bottleneck runs) — fully satisfies both papers' methodology and the deck's stated requirement. All docs that previously named "P99 Latency" as a metric to collect have been updated to say P95 instead (`WORKPLAN.md`, `SETUP-GUIDE.md`, `SCENARIOS-GUIDE.md`, `PHASE5-EXPERIMENTS-GUIDE.md`, the workplan canvas). The `Latency99` CSV column itself is left alone (it's written by TopFull's unmodified `metric_collector.py`) but is documented as always-zero/unused in `METRICS-COLLECTION-GUIDE.md` and `HOW-TO-RUN-EXPERIMENTS.md` — no re-run or collector fix is needed.

---

## Gap 3 — No direct retry-storm evidence (retries per request)

**What the data shows.** There is no retry-count series anywhere in the **existing** 38-run matrix. The only retry information in those folders is the binary controller state in `retryguard.log`: `attempts=3` while ON, `attempts=0` while OFF.

**Impact.** Slide 16 lists "retries per request" under **Layer 1**, with the evidence column reading "Directly measures if RetryGuard reduces the retry storm." That is the headline hypothesis on slide 2, and the direct measurement for it is missing from the finished matrix. It can only be supported indirectly on that data, by showing goodput and rejection changing after a toggle timestamp.

**Remediation.** Envoy exposes retry counters per upstream cluster (`upstream_rq_retry`, `upstream_rq_retry_success` and related) on the *caller's* outbound stats. Scraping those from the sidecars during a run gives a true retries-per-request series (derived at analysis time by differencing consecutive cumulative rows). This needs new runs.

**Status (implementation):** The collector exists — [`experiments/envoy_retry_collector.py`](../experiments/envoy_retry_collector.py). It scrapes `frontend` and `checkoutservice` sidecars via `kubectl exec … -c istio-proxy -- curl localhost:15000/stats` every `poll_interval_seconds` (default 5), extracts outbound counters for `cartservice` / `checkoutservice` / `productcatalogservice` / `paymentservice`, and writes `envoy_retries_{caller}.csv` into the same `record_path` that `collect_results()` already copies. Covered by unit tests in `experiments/test_envoy_retry_collector.py` and mocked-SSH wiring tests in `experiments/test_run_scenario.py`. Wired into `run_scenario.py` as tmux session `envoyretry` (independent of RetryGuard — both arms). All 14 scenario YAMLs enable it by default. Schema and file layout documented in [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md) and [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) §5.

**Blocking issue found and fixed during live validation (2026-08-20).** Istio's default `proxyStatsMatcher` strips detailed per-cluster counters (including all `upstream_rq_retry*` stats) from the Envoy admin `/stats` endpoint to reduce memory overhead — confirmed live: `kubectl exec frontend-… -c istio-proxy -- curl localhost:15000/stats` returned zero `cluster.outbound.*` lines at all (only `cluster.xds-grpc`), even though `/clusters` showed the outbound clusters were correctly configured. Without a fix, `envoy_retry_collector.py` would run forever and produce syntactically valid but **permanently all-zero** CSVs — a silent failure mode that unit tests alone could not catch (they mock the kubectl layer). Fix: patch the `frontend` and `checkoutservice` Deployments' pod template with annotation `sidecar.istio.io/statsInclusionRegexps: cluster\.outbound.*upstream_rq.*`, which triggers one rollout restart and thereafter exposes the counters. Verified live end-to-end on `topfull-master`/`topfull-worker1`: after patching, `upstream_rq_retry`/`upstream_rq_total` lines appear for `cartservice`, `productcatalogservice`, `checkoutservice` (from `frontend`) and `paymentservice` (from `checkoutservice`); a direct smoke run of `envoy_retry_collector.py` on master wrote correctly-formatted `envoy_retries_{frontend,checkoutservice}.csv` rows.

This is now **self-healing**: `run_scenario.py`'s `start_envoy_retry_collector()` calls a new `ensure_envoy_stats_enabled()` before every run, which applies this same patch idempotently (a no-op, no restart, once already applied) so a future cluster rebuild or fresh Online Boutique deploy doesn't silently reintroduce all-zero data. Covered by unit tests (`test_ensure_envoy_stats_enabled_patches_each_caller`, `test_ensure_envoy_stats_enabled_warns_but_continues_on_patch_failure` in `experiments/test_run_scenario.py`). The live patch has also already been applied directly to the cluster's `frontend`/`checkoutservice` Deployments as of 2026-08-20, so it does not need to be reapplied for the very next run — `run_scenario.py` will simply no-op it.

**Configs updated (2026-08-20), collector deployed and live-validated, no scenario run yet.** `envoy_retry_collector.py` has been `scp`'d to master at `/home/idozacharia/experiments/envoy_retry_collector.py` (matches `infra.envoy_retry_collector_script` default in all 14 configs). The existing 38 result folders still predate the collector and the stats fix — only a fresh scenario run produces `envoy_retries_*.csv`. See [PHASE7-RESOLVE-GAPS-1-3.md](PHASE7-RESOLVE-GAPS-1-3.md) for the exact runbook.

### Related series also absent (already known)

These were documented before this audit and are listed here so the Layer 1–3 picture is in one place:

- **Layer 2 — CPU/memory per pod.** `resource_collector.py` feeds the RL loop in memory and never writes per-run CSVs. See [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) §1 and [EXPERIMENT-READINESS-WORKPLAN.md](EXPERIMENT-READINESS-WORKPLAN.md) Step 8. Needed only for the "resource utilization" half of the slide 2 hypothesis and the slide 16 Layer 2 row — **no scenario objective and no open question depends on it.**
- **Pod instance counts (`num_instances.csv`).** Moot by design: slide 6 fixes replicas in both arms, all services ran at 1 replica, and S3/S4 constrain via CPU limit. "Prevents over-scaling" was never measurable in this setup.
- **`num_agent.csv` is effectively empty.** Present in all 38 folders but all zeros, apart from a single non-zero row in a few runs and 287 in `baseline_topfull_no_retryguard_topology_position_B_run3`. TopFull's internal admission state is therefore not recorded; use `RPS` from the endpoint CSVs as a proxy for admitted load when discussing controller interaction.

---

## What remains answerable

| Scenario | Status |
|---|---|
| 1 — Normal Operation | **Full.** Zero toggles in all 3 RetryGuard runs, `Fail=0`. Sanity check passes. |
| 2 — Sustained Overload | **Partial.** Goodput/rejection comparison and disable events are solid; no recover→re-enable cycle in the existing flat-overload runs (Gap 1 configs updated, not yet re-run); no retry counts in the existing matrix (Gap 3 collector built, not yet re-run). |
| 3 — Targeted Bottleneck | **Full** for goodput/rejection. Retry counts available only after re-runs with the Envoy collector. |
| 4A / 4B — Topology Position | **Full** for goodput/rejection, with the shallow-topology caveat the deck already states on slide 14. Retry counts after re-runs. |
| 5 — Interval Tuning | **None.** See Gap 1. |

| Open question (slides 8–9) | Status |
|---|---|
| System-Level Gains | Answerable — goodput, P95, rejection rate |
| Topology Beneficiaries | Answerable — per-endpoint breakdown |
| Chain Propagation | Answerable, coarse — only 5 Locust endpoints as observation points |
| Controller Interaction | Partial — admitted `RPS` as proxy; no `num_agent` state |
| Topology Position Sensitivity | Answerable — S4A vs S4B |
| Interval Parameter Sensitivity | Blocked — see Gap 1 |

**Usable for Phase 7 analysis: 30 of 38 runs** (all but the 8 Scenario 5 runs, which document only that overload was too deep for recovery to occur).

---

## Reproducing this audit

```powershell
# Gap 1 — disable vs re-enable event counts per run
Get-ChildItem experiments\results -Directory | ForEach-Object {
  $log = Join-Path $_.FullName 'retryguard.log'
  if (Test-Path $log) {
    $c = Get-Content $log -Encoding UTF8
    [pscustomobject]@{
      Run       = $_.Name
      Disables  = @($c | Select-String -SimpleMatch 'consecutive_high').Count
      Reenables = @($c | Select-String -SimpleMatch 'consecutive_low').Count
    }
  }
} | Format-Table -AutoSize

# Gap 2 — count non-zero Latency99 rows (expect 0 everywhere)
Get-ChildItem experiments\results -Directory | ForEach-Object {
  $v = @(Import-Csv (Join-Path $_.FullName 'total.csv') | ForEach-Object { [double]$_.Latency99 })
  "{0}: {1} non-zero of {2}" -f $_.Name, @($v | Where-Object { $_ -gt 0 }).Count, $v.Count
}
```

> Note on encoding: `retryguard.log` uses the `→` character in `ON→OFF` / `OFF→ON`. Match on `consecutive_high` / `consecutive_low` instead of the arrow — a naive regex can silently count zero.

---

*Related: [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) (what each run produces), [PHASE5-PHASE6-RUNLIST.md](PHASE5-PHASE6-RUNLIST.md) (run inventory), [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md) (controller algorithm + log format), [EXPERIMENT-READINESS-WORKPLAN.md](EXPERIMENT-READINESS-WORKPLAN.md) Step 8 (earliest sighting of the Layer 2 gap).*
