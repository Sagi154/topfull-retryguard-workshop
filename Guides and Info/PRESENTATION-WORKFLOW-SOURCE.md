# Workflow slides — source material

Facts for the 4–5 "how we worked" slides in the final presentation. This is raw material, not slide text. Every dated item comes from [STATUS.md](../STATUS.md) unless it says "team input" (from the team, not written in the repo).

**Thesis for the section:** each fix exposed a deeper problem. The data was not enough, then we did not understand what we measured, then the load did not overload the system, then RetryGuard did not behave as intended, then TopFull and the measurement chain themselves had faults. The Sep 7 meeting is the turning point; most of the work and slide weight comes after it.

**Timeline anchors**

| Date | Event |
|---|---|
| 2026-06-02 | First commit |
| 2026-08-11 → 08-15 | 38-run matrix |
| 2026-08-20 | Results audit, three gaps |
| 2026-09-05 → 09-06 | 48-run campaign |
| **2026-09-07** | **Mentor meeting #1 (turning point)** |
| 2026-10-06 | Mentor meeting #2 (RetryGuard technical implementation, rpr) |
| 2026-10-13 | RetryGuard parameters and S1–S4 loads locked |
| 2026-10-16 → 10-17 | 60-hold pinned matrix, `final_runs_results/` |

---

## Slide 1 — Building and first results (Jun → Sep 7)

**Message:** we built the full pipeline fast and had results to show, but they were not yet trustworthy evidence.

- Phases 0–4: GCP VMs, kubeadm Kubernetes, Istio 1.17, Online Boutique with Envoy sidecars (done before August).
- Built the runner (`run_scenario.py`) and 16 scenario YAMLs (S1–S6), plus our own RetryGuard from the paper and the Istio VirtualService patching.
- Smoke validation passed 2026-08-07.
- **38-run matrix** (2026-08-11 → 08-15, about 7 h for the second part).
- **Audit 2026-08-20** ([PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md)): 30 of 38 runs usable. Three gaps:
  - zero `OFF→ON` events in all 23 RetryGuard runs, so S5 had no signal and S2 never completed disable → recover → re-enable;
  - `Latency99` was 0 in every row, so P99 was dropped and P95 reported;
  - no retries-per-request series, so the Envoy retry collector was built (`envoy_retry_collector.py`) plus the CPU/memory collector.
- **Scenario 6 introduced** (2026-09-01) to force a recovery phase, so re-enable could be seen. S2 stayed a flat 600 s hold.
- **48-run "paper-grade" campaign** (2026-09-04 chosen, 09-05 → 09-06 run): all collectors on, ×3 repeats, S5 included.
- Mentor update doc and charts prepared (`MENTOR-UPDATE.md`, 2026-09-06 → 09-07).

---

## Slide 2 — The Sep 7 meeting, and the understanding sprint (Sep 7 → ~Sep 20)

**Message:** the meeting showed that we had numbers but not an understanding of what they meant. We stopped producing runs and started explaining the system.

**The meeting (team input):**
- Mentors asked about each scenario and what we expect to see.
- Central question: "What story do the results tell us?" We could not answer it with the data we had.
- Result: we realized plenty of things were not properly understood and that the 48 runs were not enough.

**What we did afterwards (Sep 8 → 20):**
- **Full-mesh Envoy collector** (2026-09-08): per-service inbound/outbound edges for all 11 services (`service_edges.csv`, `service_inbound.csv`).
- **TopFull throttle collector** (2026-09-09): the real admission cap and admitted rate (`topfull_throttle.csv`, `topfull_detect.csv`).
- **TopFull quota ↔ K8s sync** (2026-09-10): paper CPU table applied to Kubernetes and to TopFull's detector, so both agree.
- **RetryGuard made paper-exact** (2026-09-10): raw 1 s samples, Algorithm 1 literally. `measure_value()` reads mesh inbound (`Δ5xx / Δtotal`).
- **perTryTimeout fix** (2026-09-14): `perTryTimeout: 500ms` on every VirtualService. Without it, retries never resolved, which explains the missing toggles.
  - Team input: this is why S6 was needed in the first place. We saw too few RetryGuard toggles and assumed we needed a recovery scenario. The real cause was our implementation and the missing perTryTimeout, not the scenario type.
- RetryGuard performance fix: append-only inbound tailer (2026-09-15).
- **ρ / μ estimator attempt, then removal** (2026-09-16 → 09-17): `rho_w` was shown to be structurally unable to match the paper's ρ, and was deleted.
- **Frozen-capacity μ calibration battery** (2026-09-19): calibration holds per service. Later superseded by locking Paper-C1 and the loads.
- Hardware: VMs resized to e2-standard-8, then worker to e2-standard-16 (2026-09-15).

---

## Slide 3 — Finding a load that actually overloads the system (Sep 18 → Oct 8)

**Message:** reproducing overload turned out to be the hardest experimental problem. About 160 TopFull-off, RetryGuard-off holds went into it.

- **Locust user scaling did not raise offered load** (2026-09-18): the generator is closed-loop, so more users did not mean more requests.
- **Ron Nezer setup audit** (2026-09-20): we had copied his VMs and cluster, not his experiment recipe. CPU/replica/HPA and load shape migrated onto our tree ([RON-NEZER-BASE-MIGRATION.md](RON-NEZER-BASE-MIGRATION.md)).
- **Long S2 search** (2026-09-23 → 10-04): pinned the frontend at 4 replicas, then tried CPU tables (Replica, Checkout-3/4, Pay-250, Recs-3, Hybrid, Paper-C1) and many user-count mixes. Almost none of them reproduced.
- **Retry latching found** (2026-09-26): checkout's overload is a threshold effect. If its completed-request time sits above the 500 ms perTryTimeout, its own retries multiply arrivals 2.3×–3× and pin CPU, whatever the load. Retries create the overload they are meant to survive.
- Latch-probe series (runs 108–153, 2026-10-03 → 10-05) and an escape-time rescoring script.
- Copied-cluster verification (2026-10-01): moved to Yoav's disk copy of the VMs.
- **Locks:** Paper-C1 CPU table; S2 mix 275/90/100/90/5 (2026-10-08) and S1 mix 175/30/70/90/5 (2026-10-08); S3, S4A, S4B loads (2026-10-13). ADR 0009.
- Cooling-off between holds fixed at 120 s (2026-10-11).

---

## Slide 4 — RetryGuard evolves (Oct 6 → Oct 13)

**Message:** the controller changed from a faithful port of the paper to a tuned, cost-aware design, and each change came from a specific observation.

**Meeting #2, Oct 6 (team input):**
- Technical discussion of the implementation and the need to operate on retries per request (rpr).
- Mentors clarified the goal of the paper: **minimize cost and protect against Denial of Wallet**, not just protect goodput. This changes what we should report (retries per request, cost-style metrics).

**Changes, in order:**
- **Edge mode** (`edge_rpr`, 2026-10-06): decisions per caller → callee edge, using retries per request (14 edges), with a rejection fallback while an edge is off.
- **Attempt ramp** (2026-10-07): instead of jumping from 0 back to 3 attempts, climb 0 → 1 → 2 → 3, each step with its own bar.
- **OFF-route timeout** (2026-10-07): the OFF rule also sets a route timeout, so the off state actually changes behaviour.
- **0 → 1 re-enable bar** (2026-10-07), later 0.25 (2026-10-10 → 10-11).
- `grpc_5xx` observation and per-callee gRPC `retryOn` (2026-10-07): the first hint that gRPC callees fail differently from HTTP ones.
- **Window of 20 s and S5 dropped** (team input): 20 s alone was not good enough for us, which led to the idea of burst mode, approved by the mentors. With a 20 s window plus burst mode, the S5 interval sweep was no longer needed.
- **Burst mode** (2026-10-12): a short 5 s window with a volume floor of 20 and a bar on rpr (first 1.5, then 2.0). The 1.5 bar was dropped.
- **Parameters locked** (2026-10-13, [ADR 0008](../docs/adr/0008-locked-retryguard-parameters.md)).
- Comparison structure: two RetryGuard modes (normal and burst), both with and without TopFull, 5 variants per scenario. S1–S4 copies in `final_configs/`.

---

## Slide 5 — Making the measurements trustworthy (Oct 9 → Oct 17)

**Message:** the last stage was finding where our data could mislead us, flagging it, and re-running on a fixed cluster state.

- **TopFull problems found and handled:**
  - Throttle data went stale when the proxy admin endpoints timed out. 27 holds were flagged (2026-10-13 → 10-15). The scorer now flags them, and graphs draw stale stretches in grey.
  - **Admission cap floor 0** (2026-10-15): TopFull's lowest cap was not 0, so it could not fully shed an API. Patch via a runner-time rewrite, not by editing the submodule. Not merged.
  - **Proxy file-descriptor exhaustion** (2026-10-16): the Go proxy hit its 1024 open-file limit and refused connections on every variant, which polluted goodput. Fix: raise the soft limit to the hard limit, plus an fd collector.
  - **RL stall** (2026-10-16): the RL loop could stall on `current_rps` timeouts. Patched on master (`RL_TIMEOUT_PATCH v1`), disclosed in [TOPFULL-UPSTREAM-DEVIATIONS.md](TOPFULL-UPSTREAM-DEVIATIONS.md), and flagged as a separate health check. Mentor sign-off is still open.
  - No-cap cutoff set at 9900 (2026-10-16).
- **Analysis tooling:** hold clock, `graphs_tool`, `multi_graphs_tool`, `analysis_score.py`, a fixed template ([ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)), and the scorer's rejection definition aligned with the controller's.
- **Unpinned run mistake** (2026-10-16): the first 20 holds of the matrix ran with an unpinned frontend HPA. They were set aside, and the replica pin was made a standing lock (frontend 4/4, catalog 1/1, sidecar `proxyCPU=90m`).
- **Final dataset:** 60-hold matrix (S1–S4B, 5 variants × 2 repeats) in `final_runs_results/`: 57 clean, 3 flagged and re-run clean (2026-10-17). Merged to main via PR #11.
- **Open:** mentor sign-off on the RL patch, and the re-run decision on 11 holds ([2026-10-16-proxy-fd-rerun-decisions.md](history/2026-10-16-proxy-fd-rerun-decisions.md)).

---

## Scenario changes to mention somewhere

| Scenario | What happened |
|---|---|
| S5 (interval tuning) | Dropped. Not copied to `final_configs/`. Reason (team input): window 20 + burst mode made the sweep unnecessary. |
| S6 (forced recovery) | Dropped. Introduced because RG toggles were rare. The cause was our implementation (missing perTryTimeout), not scenario type. Not copied to `final_configs/`. |
| S1–S4B | Kept, with mixes and CPU table locked in October. S4A re-locked (2026-10-13), S4B changed from paymentservice to emailservice (2026-10-09). |

## Gaps in the record (do not state as fact in slides without confirming)

- `STATUS.md` does not record the S5/S6 drop as a decision with a date. The reasons above are from the team. Confirm the date before putting one on a slide.
- Mentor meeting contents are from team recollection, not repo evidence.
- `STATUS.md` has no entry for who attended or what was assigned at either meeting.

## Numbers to reuse (verify before presenting)

- 870 commits, 2026-06-02 → 2026-10-17.
- 38 runs (August) → 48 runs (campaign) → 60 holds (pinned matrix) plus 3 re-runs.
- About 160 both-off S2 holds for the load search (run numbers reach ~160; this is a rough count, not a verified total).
- 27 throttle-flagged holds; 3 of 60 flagged in the final matrix.
