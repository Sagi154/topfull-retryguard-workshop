# Phase 7 — Data Gaps in the Completed Matrix

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Scope:** Three gaps found on 2026-08-20 while auditing the finished 38-run matrix against the deliverables promised in [`context/Evaluating_RetryGuard_on_TopFull.md`](../context/Evaluating_RetryGuard_on_TopFull.md) (slides 8–9 open questions, slides 11–15 scenario objectives, slide 16 measurement layers).
>
> All 38 run folders are present locally and structurally valid — five endpoint CSVs, `total.csv`, `num_agent.csv`, `run_manifest.json`, plus `retryguard.log` on RetryGuard runs. See [PHASE5-PHASE6-RUNLIST.md](PHASE5-PHASE6-RUNLIST.md) for the inventory. The gaps below are about *which metrics those files contain*, not about missing folders.
>
> **Bottom line:** 30 of 38 runs support the analysis as designed. The 8 Scenario 5 runs do not. Two Layer 1 metrics named on slide 16 were never collected.

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

**Status (implementation):** The generic mechanism for this now exists — `experiments/run_scenario.py` supports an optional `locust.phases` list (see `PHASE5-EXPERIMENTS-GUIDE.md` §"YAML config schema") that changes offered load mid-run by killing and relaunching Locust at a new level. It is covered by unit tests in `experiments/test_run_scenario.py` and is fully backward compatible — no existing matrix config is affected. Applying it to the S5 configs (or S2) and actually re-running them on the VMs is a deliberate follow-up decision, not yet done. See `experiments/configs/scenario_5_interval_60s_recovery_example.yaml` for a worked (but not yet executed) example using the previously discussed parameters: hold the current overload level for 300s to trigger disable, then drop to ~25% of peak load for the remainder of a 900s run.

---

## Gap 2 — P99 latency was never collected

**What the data shows.** `Latency99` is `0.0` in **every row of every CSV across all 38 runs** (verified on `total.csv`, `postcheckout.csv`, `getproduct.csv`).

**Root cause.** Upstream in TopFull's `metric_collector.py`. Its Locust query returns three values, and the 99th percentile is hardcoded — the four-value unpack is commented out. Visible in the patch source at [`experiments/patch_metric_collector.py`](../experiments/patch_metric_collector.py) lines 27–29:

```python
# rps, fail, latency95, latency99 = metric[api]
rps, fail, latency95 = metric[api]
latency99 = 0
```

`total.csv` then averages that column, so it is zero there too. Our `patch_metric_collector.py` only wrapped the loop in try/except; it did not touch this.

**Impact.** Slide 16 lists "API latency" under Layer 1, and [WORKPLAN.md](WORKPLAN.md) names **P99 Latency (ms)** as a key metric. That specific number does not exist.

**Mitigation.** `Latency95` is real and responsive across the matrix — roughly 570–630 ms in normal operation up to ~3100 ms in the S4A bottleneck runs. It carries the same story. **The report and slides must say P95, not P99.** If true P99 is required, `metric_collector.py` needs the four-value unpack restored on master (check whether TopFull's Locust stats query exposes the 99th percentile at all) and the affected runs repeated.

---

## Gap 3 — No direct retry-storm evidence (retries per request)

**What the data shows.** There is no retry-count series anywhere in the results. The only retry information is the binary controller state in `retryguard.log`: `attempts=3` while ON, `attempts=0` while OFF.

**Impact.** Slide 16 lists "retries per request" under **Layer 1**, with the evidence column reading "Directly measures if RetryGuard reduces the retry storm." That is the headline hypothesis on slide 2, and the direct measurement for it is missing. It can only be supported indirectly, by showing goodput and rejection changing after a toggle timestamp.

**Remediation.** Envoy exposes retry counters per upstream cluster (`upstream_rq_retry`, `upstream_rq_retry_success` and related). Scraping those from the sidecars during a run would give a true retries-per-request series. This needs new runs.

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
| 2 — Sustained Overload | **Partial.** Goodput/rejection comparison and disable events are solid; no recover→re-enable cycle, no retry counts. |
| 3 — Targeted Bottleneck | **Full.** Per-endpoint goodput and rejection give bottleneck relief and upstream propagation. |
| 4A / 4B — Topology Position | **Full**, with the shallow-topology caveat the deck already states on slide 14. |
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
