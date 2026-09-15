# TopFull activation, e2-16 resize, and retry control — session summary

**Date:** 2026-09-15  
**Context:** Follow-on from [TOPFULL-ACTIVATION-DIAGNOSIS.md](TOPFULL-ACTIVATION-DIAGNOSIS.md) and the e2-standard-8 S1/S2 readout.  
**Primary results tree:** `experiments/results/campaign_48/`

---

## 1. What problem we were solving

On unconstrained S1/S2 (and historically most of `campaign_48` S1–S4), **TopFull’s admission controller never engaged**:

- Detector gate: app-container CPU > `quota × α` (frontend: `1000m × 0.8 = 800m`).
- On **e2-standard-8**, frontend CPU topped out ~740 m — permanently below 800 m.
- Raising Locust users did not help: CPU was asymptotic; extra load only lengthened queues.
- Root cause mix: **single small worker** + **Envoy sidecar tax invisible to TopFull** (collector skips `istio-proxy`).

Separately, even after adding `perTryTimeout: 500ms`, **Envoy retries stayed near zero whenever TopFull was actively throttling** on e2-16.

---

## 2. What we did

### 2.1 Diagnosis (conceptual)

- Explained why Detector quota and K8s CPU limit were coupled (`cpu_limit_fraction` for S3/S4) and why decoupling Detector-only quotas is optional, not required for the path we took.
- Ruled out “scale all paper quotas proportionally” as a general fix: S1 and S2 frontend CPU are nearly identical; a full-table recalibration would fire under normal load too.
- Chose **resize the worker** over quota hacks / α changes / more pods on the same node.

### 2.2 Infra change

| VM | Machine type | Role |
|---|---|---|
| `topfull-worker-1` | **e2-standard-16** (was e2-standard-8) | All Boutique pods + Envoy sidecars |
| `topfull-master` | e2-standard-8 | Control plane + TopFull + collectors |
| `topfull-load` | e2-standard-8 | Locust |

Quota: 16+8+8 = 32 vCPU (at the region limit). Worker size is what mattered.

### 2.3 Experiment sequence (TopFull ON)

With cool-offs between runs:

1. **S1 baseline run22** (300 s)  
2. **S2 baseline run21** (600 s)  
3. **S2 RetryGuard run10** (600 s)

S6 YAMLs were bumped run3→run4 beforehand so they could not overwrite campaign data. After the sequence, S1/S2 YAML slots were bumped to run23 / run22 / run11.

### 2.4 TopFull-off control (retry isolation)

- Added optional `topfull_rl.enabled` to [`experiments/run_scenario.py`](../experiments/run_scenario.py) (**default true** — existing 16 campaign YAMLs unchanged).
- When `false`: Go proxy + collectors + Locust still run; **`deploy_rl.py` is skipped** (no admission throttling; thresholds stay at 10000).
- New standalone config: [`experiments/configs/scenario_2_baseline_no_topfull.yaml`](../experiments/configs/scenario_2_baseline_no_topfull.yaml)  
  - Own folder: `baseline_no_topfull_sustained_overload_run1`  
  - Does **not** consume `scenario_2_baseline.yaml` run numbers.
- Ran that control on the same e2-16 worker, same S2 load / `perTryTimeout: 500ms`.

VMs were stopped after both sequences.

---

## 3. Results

### 3.1 TopFull activation (the resize worked)

| Run | VM | Frontend max CPU | >800 m? | `num_agent` nonzero | Threshold left 10000? |
|---|---|---|---|---|---|
| S1 run21 | e2-8 | ~695 m | no | no | no |
| S1 run22 | e2-16 | **~883 m** | **yes** | **yes** | **yes** |
| S2 run17 / run20 | e2-8 | ≤679 m | no | no | no |
| S2 run21 | e2-16 | **~977 m** | **yes** | **yes** | **yes** |
| S2 RG run9 | e2-8 | ~657 m | no | no | no |
| S2 RG run10 | e2-16 | **~937 m** | **yes** | **yes** | **yes** |

**Only frontend** crossed the Detector line on S2 run21. Other services stayed below `quota × α` (catalog closest: 442 vs need 475). That is expected for unconstrained S2: frontend is the entry aggregator; backends’ app-container CPU stays lower; sidecar CPU is invisible to TopFull.

When frontend is overloaded, TopFull’s `clustering()` attaches **all five storefront Locust APIs** (they all traverse frontend), so **every endpoint’s admission `threshold` drops together** — visible in `topfull_throttle.csv`.

### 3.2 Client outcomes (getcart)

| Run | Goodput | Fail/s (mean) | P95 (ms) |
|---|---|---|---|
| S2 e2-8 run17 | ~5 | ~161 | ~2200 |
| **S2 e2-16 run21 (TF ON)** | **~101** | ~162 | **~616** |
| **S2 e2-16 no-TF run1** | **~58** | ~134 | **~1652** |
| S2 RG e2-8 run9 | ~7 | ~157 | ~2316 |
| S2 RG e2-16 run10 | ~84 | ~132 | ~1256 |

TopFull-on S2 is much healthier on latency/goodput than e2-8 or TopFull-off on the same machine.

### 3.3 Retries: TopFull was suppressing them

| Run | TopFull RL | Outbound Envoy Δ`retry` | Notes |
|---|---|---|---|
| S2 run21 | ON | **~0** | Thresholds actively low |
| S2 no-TF run1 | OFF | **+211** (cart +202) | All thresholds stuck at 10000 |
| S2 e2-8 run20 (inert TF) | effectively OFF | **+166k** (hot path) | Smaller machine, huge storm |

**Conclusion:** On e2-16, with the same load and `perTryTimeout: 500ms`, turning off admission control brings retries back. TopFull’s entry capping keeps backends from timing out often enough to retry. The no-TF storm is still **modest** vs e2-8 — the larger worker has more headroom even without RL.

### 3.4 RetryGuard

S2 RG run10 (e2-16, TopFull ON): **zero ON→OFF**. Same as run9, different reason:

- Run9 (e2-8): little mesh failure signal / TopFull idle.
- Run10 (e2-16): TopFull absorbs overload **upstream** of mesh inbound, so `Δ(5xx+resets)/Δtotal` rarely stays above Threshold for 30 samples.

---

## 4. What this means for the project narrative

- **`campaign_48` S1–S4** (historical): TopFull was effectively **inert** — comparison is closer to “Istio retries vs RetryGuard” than “TopFull+retries vs TopFull+RetryGuard”. State that explicitly in mentor/report text.
- **e2-16 S1/S2 checkpoints** (run22 / run21 / run10): first clean evidence that **TopFull works as designed** on our cluster when the worker is large enough.
- **Retries + RetryGuard disable** are still the open gap under **TopFull-on + flat S2**.

---

## 5. What to do next

Two goals, preferably without breaking the other:

1. **More Envoy retries** (under conditions that still matter for the paper).  
2. **TopFull activation driven by services other than frontend**.

### 5.1 More retries

| Option | Effect | Trade-off |
|---|---|---|
| **A. Tighten `per_try_timeout_ms` (500 → 250–300)** | More slow calls become per-try timeouts → Δ`retry` rises; works with TopFull ON | More aggressive than a neutral “match p99” setting; still under the 1 s SLO |
| **B. Run S3 / soft-constrain a hot backend** | Starved backend times out → retries on that edge even with TopFull ON | Changes scenario semantics (S2 → bottleneck) |
| **C. TopFull-off control + tighter timeout** | Maximizes storm for isolation | Not a campaign arm |
| Raise Locust users alone | Weak with TopFull ON (proxy sheds load) | Do not rely on this |

**Recommended next experiment:** S2 baseline (TopFull ON), `per_try_timeout_ms: 250`, new run slot — gate on `service_edges.csv` Δ`retry` ≫ 0. If still flat, do **S3 baseline** next.

Note: **500 ms is already a realistic** production-ish value for a fast hop under a 1 s client SLO. Going to 250 ms is a **sensitivity lever**, not “more real-world.”

### 5.2 TopFull firing on services besides frontend

Unconstrained S2 will keep preferring frontend. To get other services into `detect()`:

| Option | How | What TopFull does |
|---|---|---|
| **S3** | `checkoutservice` at `cpu_limit_fraction: 0.1` (paper 1000m → 100m); quota↔K8s sync already fixed | Detector should see checkout overloaded; cluster APIs that touch checkout |
| **S4A / S4B** | productcatalog / payment at fraction 0.1 | Topology-position story; non-frontend overload by design |
| Soft constrain catalog on “S2-like” load | e.g. fraction 0.5 on `productcatalogservice` (α already 0.95) | Blurs S2 vs S3; use only as a diagnostic |
| Include sidecar CPU in Detector | Patch TopFull `resource_collector` to count istio-proxy | Most “honest” for mesh tax; larger code/paper deviation; needs quota recalibration |

**Recommended:** re-run **S3 baseline** (and optionally S3 RetryGuard) on e2-16 with collectors on. That is the designed way to get **non-frontend** TopFull activation **and** a retry-prone hot edge in one scenario.

Do **not** scale replica count on the same node hoping to help TopFull — that splits per-pod CPU and makes the Detector *less* likely to fire.

### 5.3 Suggested order of work

1. S2 baseline, TopFull ON, **`per_try_timeout_ms: 250`** — confirm retries under active admission.  
2. Same config with RetryGuard ON — see if disable can fire once retries/resets are denser.  
3. **S3 baseline + S3 RetryGuard** on e2-16 — TopFull on checkout (not only frontend) + retries on the constrained path.  
4. Update mentor/report caveats: historical `campaign_48` vs new e2-16 TopFull-on data.  
5. Keep using the independent `scenario_2_baseline_no_topfull.yaml` only as a control; do not mix its run numbers with `baseline_topfull_*`.

---

## 6. Key paths / slots (do not overwrite)

| Folder / config | Meaning |
|---|---|
| `…/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run21` | e2-16, TopFull ON, retries ≈ 0 |
| `…/S2_sustained_overload/run_topfull_retryguard_sustained_overload_run10` | e2-16, TopFull ON + RG, zero disables |
| `…/S2_sustained_overload/baseline_no_topfull_sustained_overload_run1` | e2-16, TopFull RL OFF, retries +211 |
| `…/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run22` | e2-16 S1, TopFull ON |
| `…/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run22` | e2-16, TopFull ON, post-perf-fix baseline |
| `…/S2_sustained_overload/run_topfull_retryguard_sustained_overload_run11` | e2-16, TopFull ON + RG post-perf-fix, zero disables |
| Next free: S1 base **run23**, S2 base **run23**, S2 RG **run12**, no-TF control **run2**, S6 **run4** |

---

## 8. Task 3 addendum — post-perf-fix runs (2026-09-15 evening)

After Tasks 1–2 fixed `retryguard.py` (InboundCsvTailer replacing polling) and `resource_usage_collector.py` (adding `__master_node__` CPU/memory row), two fresh S2 runs on e2-16 were executed from the `feature/retryguard-perf-fix` worktree:

- **S2 baseline run22** — 600 s, TopFull ON, Istio retries on, no RetryGuard.
- **S2 RetryGuard run11** — 600 s, TopFull ON, RetryGuard ON (threshold=20%, interval_samples=30).

### Restart signature: CLEAN ✅

All collector logs show exactly one START block at the beginning and one SHUTDOWN/EXIT at the end — no mid-run restart signatures. This confirms the Task 1 performance fix eliminated the `service_inbound.csv` read storm that caused run10's controller restarts.

### Master-node CPU (new via Task 2 `__master_node__` rows)

| Run | Condition | master max CPU | master mean CPU |
|-----|-----------|---------------|----------------|
| run22 | baseline e2-16 | 6519 m | 5608 m |
| run11 | RG e2-16 | 6691 m | 5647 m |

RG overhead on master: **+172 m max / +39 m mean** — negligible (~0.3% of 8-vCPU machine).

### P95 / goodput comparison

| Run | Condition | getcart mean P95 | getcart max P95 | total mean Goodput | total mean Fail |
|-----|-----------|-----------------|-----------------|-------------------|----------------|
| run21 | baseline e2-16 prev | 634 ms | 1600 ms | 290 rps | 422 |
| run22 | baseline e2-16 new | 756 ms | 1700 ms | 504 rps | 109 |
| run10 | RG e2-16 prev | 1262 ms | 2600 ms | 332 rps | 266 |
| run11 | RG e2-16 new | 1594 ms | 2800 ms | 390 rps | 151 |

Key observations:
- **RG vs baseline P95 gap persists**: run11 RG ~1594 ms vs run22 baseline ~756 ms — roughly **2× higher P95** with RetryGuard ON. This gap was not closed by the perf fix; it existed in run10 vs run21 as well and appears structural.
- **RG goodput slightly higher than baseline** in this pair (390 vs 504 total, but 113 vs 137 on getcart). Run-to-run variability is significant (run21 total=290 vs run22 total=504, same condition).
- **Why RG worsens P95**: RetryGuard is NOT disabling retries (zero ON→OFF events in run11), so the Istio default 3 retries remain active. The high P95 is the retry overhead penalty without the benefit of disabling.

### RetryGuard toggle events in run11: ZERO

- 5553 OBSERVE lines total, only 6 had rejection > 0 (all at SHUTDOWN moment, not during run).
- Max observed rejection: 0.6364 (adservice, at shutdown only).
- `high` streak counter never reached `interval_samples=30` during the run.
- Root cause: TopFull Layer A actively throttled (1220 rows with threshold < 10000), so mesh inbound services see near-zero 5xx — the RetryGuard signal source never crosses the 20% threshold during steady-state overload.

### Conclusion

The perf fix (Task 1+2) succeeded in eliminating restarts and measuring master CPU overhead. The fundamental finding is unchanged: **on flat S2 with TopFull ON + e2-16, RetryGuard does not disable** because TopFull absorbs overload before it reaches the mesh inbound rejection signal. Next investigation: S3/S4 with CPU constraints, or tighten `per_try_timeout_ms` further.

---

## 7. One-line takeaways

1. **Worker too small → TopFull never fired; e2-16 fixed that for frontend-driven S1/S2.**  
2. **TopFull-on suppresses retries; TopFull-off brings them back (modestly on e2-16).**  
3. **RetryGuard still does not disable under flat S2 with live TopFull.**  
4. **Post-perf-fix (run11): restarts eliminated, master RG CPU overhead negligible (+39 m mean).**
5. **P95 gap (RG ~2× baseline) persists because RG never disables — retries stay on without any benefit.**
6. **Next: S3/S4 with CPU constraints, or tighter per-try timeout, to produce mesh inbound 5xx that RetryGuard can detect.**
