# Phase 7 — Data Gaps in the Completed Matrix

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Scope:** Three gaps found on 2026-08-20 while auditing the finished 38-run matrix against the deliverables promised in [`context/Evaluating_RetryGuard_on_TopFull.md`](../context/Evaluating_RetryGuard_on_TopFull.md) (slides 8–9 open questions, slides 11–15 scenario objectives, slide 16 measurement layers). Gap 2 was resolved the same day by dropping P99 as a target metric (see below) — it was a self-imposed target from `WORKPLAN.md`, not something either source paper or the deck actually requires. Gap 3's *collector* was built the same day (see below) but the existing 38 folders still lack retry-count series until scenarios are re-run with it.
>
> All 38 run folders are present locally and structurally valid — five endpoint CSVs, `total.csv`, `num_agent.csv`, `run_manifest.json`, plus `retryguard.log` on RetryGuard runs. See [PHASE5-PHASE6-RUNLIST.md](PHASE5-PHASE6-RUNLIST.md) for the inventory. The gaps below are about *which metrics those files contain*, not about missing folders.
>
> **Bottom line (2026-09-06):** Primary Phase 7 analysis uses the **48-run campaign** in `experiments/results/campaign_48/` — Gaps 1 and 3 are **closed** on that dataset (S6/S5 re-enabled; every folder has Envoy + `resource_usage.csv`). The August 38 in `experiments/results/august_38/` remains historical: 30 of 38 support goodput / P95 / rejection; its 8 Scenario 5 runs never re-enabled; it has no retries-per-request or CPU/memory series. P99 (Gap 2) is dropped; report P95.

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

**Configs (2026-09-01 split).** The 2026-08-20 edit put the 900s load-drop onto Scenario 2, which diverged from the deck's 10-minute hold. That is undone: **S2 is again a flat 600s peak** (same shape as matrix runs 1–3; `run_number: 4` is the next S2 repeat, with collectors on). The load-drop profile is **Scenario 6** (`scenario_6_recovery_{baseline,retryguard}.yaml`, `run_number: 1`) and all four S5 interval configs (already `run_number: 3`). S5 compares against **S6 baseline**, not S2. S3/S4 were never given a recovery phase.

**How to actually run these (decision 2026-09-04).** Paper-grade **48-run campaign** — new slots, all collectors on, ×3 repeats including S5 — not a replay of the August 38 and not a 16-run add-on. See [PHASE7-RESOLVE-GAPS-1-3.md](PHASE7-RESOLVE-GAPS-1-3.md). **Do not** use `run_all_scenarios.py`: `build_matrix()` is hardcoded to S2 `run1–3` / S5 `run1–2` and would overwrite finished matrix folders. S6 is not in that matrix at all.

**Pre-campaign gate (2026-09-04): PASSED on S6 run1.** `baseline_topfull_no_retryguard_forced_recovery_run1` and `run_topfull_retryguard_forced_recovery_run1` (now under `experiments/results/campaign_48/`) produced Locust time series, non-zero Envoy `upstream_rq_retry` under baseline traffic, `resource_usage.csv`, and — for the first time — 3× `OFF→ON` after the load drop (`cartservice`, `productcatalogservice`, then `checkoutservice`).

**Campaign outcome (2026-09-06): CLOSED for Gap 1 on the recovery load.** All 48 campaign folders are in `experiments/results/campaign_48/`. Toggle counts (`consecutive_high` / `consecutive_low`):

| Run group | Repeats | Disables per run | Re-enables per run |
|---|---|---|---|
| S6 Forced Recovery RG | 3 | 3 | **3** |
| S5 interval 20/30/60s | 9 | 3 | **3** |
| S5 interval 10s | 3 | 3, 3, **5** (run3 oscillated) | 3, 3, **5** |
| S2 / S3 / S4A RG (flat / CPU-limit hold) | 9 | 3 | **0** (expected) |
| S4B RG | 3 | 1, 1, 4 | 0, 0, **1** (run6 `cartservice`) |
| S1 RG (normal op) | 3 | **1** (checkout) | 0 |

August 38 (`august_38/`) is unchanged: 60 disables, zero re-enables. That remains a valid negative result under saturating flat overload. Scenario 5 is answerable **only** on campaign S5 vs S6 baseline — not on the August interval folders.

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

**Status (implementation):** The collector exists — [`experiments/envoy_retry_collector.py`](../experiments/envoy_retry_collector.py). It scrapes `frontend` and `checkoutservice` sidecars via `kubectl exec … -c istio-proxy -- curl localhost:15000/stats` every `poll_interval_seconds` (default 5), extracts outbound counters for `cartservice` / `checkoutservice` / `productcatalogservice` / `paymentservice`, and writes `envoy_retries_{caller}.csv` into the same `record_path` that `collect_results()` already copies. Covered by unit tests in `experiments/test_envoy_retry_collector.py` and mocked-SSH wiring tests in `experiments/test_run_scenario.py`. Wired into `run_scenario.py` as tmux session `envoyretry` (independent of RetryGuard — both arms). All 16 scenario YAMLs enable it by default. Schema and file layout documented in [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md) and [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) §5.

**Blocking issue found and fixed during live validation (2026-08-20).** Istio's default `proxyStatsMatcher` strips detailed per-cluster counters (including all `upstream_rq_retry*` stats) from the Envoy admin `/stats` endpoint to reduce memory overhead — confirmed live: `kubectl exec frontend-… -c istio-proxy -- curl localhost:15000/stats` returned zero `cluster.outbound.*` lines at all (only `cluster.xds-grpc`), even though `/clusters` showed the outbound clusters were correctly configured. Without a fix, `envoy_retry_collector.py` would run forever and produce syntactically valid but **permanently all-zero** CSVs — a silent failure mode that unit tests alone could not catch (they mock the kubectl layer). Fix: patch the `frontend` and `checkoutservice` Deployments' pod template with annotation `sidecar.istio.io/statsInclusionRegexps: cluster\.outbound.*upstream_rq.*`, which triggers one rollout restart and thereafter exposes the counters. Verified live end-to-end on `topfull-master`/`topfull-worker1`: after patching, `upstream_rq_retry`/`upstream_rq_total` lines appear for `cartservice`, `productcatalogservice`, `checkoutservice` (from `frontend`) and `paymentservice` (from `checkoutservice`); a direct smoke run of `envoy_retry_collector.py` on master wrote correctly-formatted `envoy_retries_{frontend,checkoutservice}.csv` rows.

This is now **self-healing**: `run_scenario.py`'s `start_envoy_retry_collector()` calls a new `ensure_envoy_stats_enabled()` before every run, which applies this same patch idempotently (a no-op, no restart, once already applied) so a future cluster rebuild or fresh Online Boutique deploy doesn't silently reintroduce all-zero data. Covered by unit tests (`test_ensure_envoy_stats_enabled_patches_each_caller`, `test_ensure_envoy_stats_enabled_warns_but_continues_on_patch_failure` in `experiments/test_run_scenario.py`). The live patch has also already been applied directly to the cluster's `frontend`/`checkoutservice` Deployments as of 2026-08-20, so it does not need to be reapplied for the very next run — `run_scenario.py` will simply no-op it.

**Configs updated (2026-08-20), collector live-validated; runner now deploys the `.py` each run.** `run_scenario.py` copies `experiments/envoy_retry_collector.py` to `infra.envoy_retry_collector_script` before starting the tmux session. The existing 38 result folders still predate the collector and the stats fix — only a fresh scenario run produces `envoy_retries_*.csv`. The chosen close-out is the 48-run campaign in [PHASE7-RESOLVE-GAPS-1-3.md](PHASE7-RESOLVE-GAPS-1-3.md), not a bolt-on 4th repeat mixed with August goodput.

**First live-with-traffic Envoy + resource CSVs (2026-09-04):** S6 baseline/RetryGuard run1. Baseline frontend `max_retry=120` (stats-inclusion confirmed under load).

**Campaign outcome (2026-09-06): CLOSED for Gap 3 on `campaign_48/`.** All 48 folders have `envoy_retries_frontend.csv`, `envoy_retries_checkoutservice.csv`, and `resource_usage.csv`. Frontend `max_retry > 0` on baseline overload runs (stats-inclusion proof). Checkout sidecar `max_retry` is often 0 (few outbound retries on that caller). Counters are **cumulative across the campaign** on the cluster — differencing within a run is the analysis method, not comparing raw `max_total` across folders. August 38 (`august_38/`) still has no Envoy / resource series.

### Related series also absent (already known)

These were documented before this audit and are listed here so the Layer 1–3 picture is in one place:

- **Layer 2 — CPU/memory per pod.** `resource_usage_collector.py` is wired into `run_scenario.py` and enabled in all 14 configs (writes `resource_usage.csv` via kubelet `stats/summary`). The existing 38 matrix folders predate it — only new runs get CPU/memory series. TopFull's in-memory `resource_collector.py` is unchanged. Pod replica counts in the CSV document the fixed-replica design (`1` everywhere); autoscaling charts remain N/A.
- **Pod instance counts (`num_instances.csv`).** Moot by design: slide 6 fixes replicas in both arms, all services ran at 1 replica, and S3/S4 constrain via CPU limit. "Prevents over-scaling" was never measurable in this setup.
- **`num_agent.csv` is effectively empty.** Present in all 38 folders but all zeros, apart from a single non-zero row in a few runs and 287 in `baseline_topfull_no_retryguard_topology_position_B_run3`. TopFull's internal admission state is therefore not recorded; use `RPS` from the endpoint CSVs as a proxy for admitted load when discussing controller interaction.

---

## What remains answerable

Primary dataset: `experiments/results/campaign_48/`. August figures below are historical (`august_38/`).

| Scenario | Status |
|---|---|
| 1 — Normal Operation | **Full**, with a finding: August RG runs had zero toggles; **campaign RG run4–6 each had one checkout `ON→OFF`** (no re-enable). Sanity check is no longer “silent S1”. |
| 2 — Sustained Overload | **Partial** on re-enable-under-flat-hold (campaign run4–6: 3× disable, 0× re-enable — same shape as August). Goodput / P95 / rejection / retries / CPU are complete on the campaign. Forced recovery is Scenario 6, not S2. |
| 3 — Targeted Bottleneck | **Full** on the campaign (goodput / P95 / rejection / retries / CPU). Flat-hold re-enable did not fire (3× disable, 0× re-enable). |
| 4A / 4B — Topology Position | **Full** on the campaign, with the shallow-topology caveat on slide 14. S4A: 3× disable, 0× re-enable. S4B: often checkout-only disable; run6 also had one cart `OFF→ON`. |
| 5 — Interval Tuning | **Full** on campaign run3–5 (all 12 recovered). Compare against **S6 baseline**, not S2. August’s 8 flat S5 runs stay a negative result (never re-enabled). 10s run3 oscillated (5 disable / 5 re-enable). |
| 6 — Forced Recovery | **Full** (run1–3 both arms). Every RG repeat: 3× `ON→OFF` then 3× `OFF→ON`. |

| Open question (slides 8–9) | Status |
|---|---|
| System-Level Gains | Answerable — goodput, P95, rejection, plus same-run retries and CPU/memory on the campaign |
| Topology Beneficiaries | Answerable — per-endpoint + Envoy retry counts |
| Chain Propagation | Answerable, coarse — 5 Locust endpoints; Envoy adds checkout outbound retries |
| Controller Interaction | Partial — admitted `RPS` as proxy; no `num_agent` state. S6 has a full disable→recover→re-enable cycle |
| Topology Position Sensitivity | Answerable — S4A vs S4B on the campaign |
| Interval Parameter Sensitivity | **Answerable** — campaign S5 ×3 on the recovery load |

**Usable for Phase 7 analysis: all 48 campaign runs** in `campaign_48/`. The August 38 in `august_38/` stays historical (30 usable for goodput/P95/rejection; 8 flat S5 as negative evidence). See [PHASE7-RESOLVE-GAPS-1-3.md](PHASE7-RESOLVE-GAPS-1-3.md).

---

## Reproducing this audit

```powershell
# Gap 1 — disable vs re-enable event counts per run (campaign = primary)
Get-ChildItem experiments\results\campaign_48, experiments\results\august_38 -Directory | ForEach-Object {
  $log = Join-Path $_.FullName 'retryguard.log'
  if (Test-Path $log) {
    $c = Get-Content $log -Encoding UTF8
    [pscustomobject]@{
      Set       = $_.Parent.Name
      Run       = $_.Name
      Disables  = @($c | Select-String -SimpleMatch 'consecutive_high').Count
      Reenables = @($c | Select-String -SimpleMatch 'consecutive_low').Count
    }
  }
} | Format-Table -AutoSize

# Gap 2 — count non-zero Latency99 rows (expect 0 everywhere)
Get-ChildItem experiments\results\campaign_48, experiments\results\august_38 -Directory | ForEach-Object {
  $v = @(Import-Csv (Join-Path $_.FullName 'total.csv') | ForEach-Object { [double]$_.Latency99 })
  "{0}/{1}: {2} non-zero of {3}" -f $_.Parent.Name, $_.Name, @($v | Where-Object { $_ -gt 0 }).Count, $v.Count
}
```

> Note on encoding: `retryguard.log` uses the `→` character in `ON→OFF` / `OFF→ON`. Match on `consecutive_high` / `consecutive_low` instead of the arrow — a naive regex can silently count zero.

---

*Related: [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) (what each run produces), [PHASE5-PHASE6-RUNLIST.md](PHASE5-PHASE6-RUNLIST.md) (run inventory), [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md) (controller algorithm + log format), [EXPERIMENT-READINESS-WORKPLAN.md](EXPERIMENT-READINESS-WORKPLAN.md) Step 8 (earliest sighting of the Layer 2 gap).*
