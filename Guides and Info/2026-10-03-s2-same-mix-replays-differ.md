# S2 Paper-C1: why same-mix replays look so different

Both-off holds, 600 s, `spawn_rate` 50, Paper-C1 table (frontend 1150 m × 4, checkout 800 m × 1, recommendations 1150 m × 1, others × 1), sidecar request 100 m. Run tables: [2026-10-02-s2-paper-c1-run89-handoff.md](2026-10-02-s2-paper-c1-run89-handoff.md), [2026-10-03-s2-paper-c1-runs-99-107.md](2026-10-03-s2-paper-c1-runs-99-107.md). Escape-time rescore: [2026-10-05-s2-latch-escape-time-rescore.md](2026-10-05-s2-latch-escape-time-rescore.md). Labels: **(v)** = verified in the repo this session, **(p)** = taken from the earlier analysis and not re-derived here, **(i)** = inference.

## Short answer

Each hold ends in one of two modes. The mix does not pick the mode.

- **Sticky checkout latch.** Checkout trips first (~116–155 s) (p). Its sojourn sits on Istio's 500 ms `perTryTimeout`, about half the attempts time out, `attempts: 3` multiplies traffic ~3×, CPU pegs, and the loop sustains itself (frontend→checkout retries 53k–63k). Recommendations stays cold (~360–420 req/s, 66–99 ms, no retries) (p).
- **Release into a recommendations storm (blend).** Recommendations crosses ~560–620 req/s within 10–50 s of checkout tripping and starts its own retry storm (217k–238k retries). Frontend slows (~1.5 s pages), the Locust closed loop (`constant_throughput(1)`) offers less, checkout's input drops below what sustains its loop, and it releases (p; the closed-loop and release steps are (i)).

Same mix, same table, different mode:

| Mix | Original cluster | Disk copy |
|---|---|---|
| 275/90/100/90/5 | run89 blend, run92 leaf missed (both released) | run99 blend, run100 miss, run101 blend (verdicts (v) from the 99–107 guide) |
| 275/80/100/90/5 | run86 blend, run88 blend | run102–104 all miss |

Run94, 95, 96 (disk copy, mix 275/90) were three sticky latches in a row (v: handoff table). Verdicts 94–96, 102–104, 106–107 cluster by time (v).

**What matches across clusters:** steady states inside a mode (p). Every recorded config item: Paper-C1 limits, frontend 4 replicas, TopFull/RG off, spawn 50, `perTryTimeout` 500, sampling (p; the handoff states the same pin (v)).

**What does not explain it:** the mix itself; long VM stops; the predecessor hold (p).

**Honest uncertainty:** sticky 0/4 on the original cluster vs 7/11 on the disk copy gives Fisher p≈0.08 (p). That is suggestive, not established. Small counts also mean a mix effect of a few user counts is not ruled out.

**Not stored in any run folder (p; consistent with what `collect_results` pulls (i)):** pod node, restart count, pod age, kernel, live sidecar annotation. These are the candidate hidden differences.

## What the runner resets between holds (v, `experiments/run_scenario.py`)

| Reset every hold | Not reset |
|---|---|
| Locust (`tmux kill-server`, `pkill locust`, relaunch with `RATE`) | Boutique pods, Envoy sidecars, pod age, Go runtime state |
| TopFull proxy, RL, collectors, RetryGuard (`pkill`, `tmux kill-server`) | gRPC connections between pods (idle ones survive; Locust's die with Locust) (i) |
| `perTryTimeout` VirtualService patch | HPA state (the frontend pin is manual; `run_scenario.py` has no HPA code) |
| CPU patches only if the live value differs (`already at …; skipping patch`) | `paper_cpu_reconcile: false` on these YAMLs, so no reconcile patch |

An identical `kubectl patch` does not change the pod template, so no rollout happens (i, standard Kubernetes behaviour). A pod restart is therefore **not** already done. 300–360 s cool-off lets queues drain but does nothing to process state.

## Cheap checks (all post-hoc or passive; none changes the load)

Save everything into the run folder on master: `/home/idozacharia/experiments/results/<log_folder>/state/`, so `scp -r` of the folder brings it back.

### 1. Cluster state snapshot at t=0
- **Capture:** pod node, restarts, age, kernel, sidecar annotations.
- **Where/when:** manual ssh on master just before `run_scenario.py` (the folder name is the YAML's `log_folder`). Optional hook: a `snapshot_cluster_state()` call right after `apply_per_try_timeout(cfg)` in `run()`.
- **Commands:**
```powershell
$L = "/home/idozacharia/experiments/results/<log_folder>/state"
ssh topfull-master "mkdir -p $L; kubectl get pods -n default -o wide > $L/pods_t0.txt; kubectl get nodes -o wide > $L/nodes_t0.txt; kubectl get deploy -n default -o jsonpath='{range .items[*]}{.metadata.name}{\"\t\"}{.spec.template.metadata.annotations}{\"\n\"}{end}' > $L/annotations_t0.txt; kubectl get hpa -n default > $L/hpa_t0.txt"
ssh topfull-worker-1 "uname -r; uptime -s; nproc" > state_worker.txt
```
- **Confirms** a hidden-state hypothesis if sticky holds share a pattern the released ones lack (checkout or recommendations on a different node, higher RESTARTS, much older pods, different kernel). **Refutes** it if all 11+ holds are identical on those fields. With ~8 holds expect weak power; this mainly rules things out.

### 2. Checkout sojourn in the 90–150 s window (the latch predictor)
- **Capture:** per-tick checkout inbound mean sojourn from `service_inbound.csv` (`rq_time_sum_ms` / `rq_time_count` deltas; `rq_time_buckets` for the share above 500 ms (v: columns documented in AGENTS.md and used by the 99–107 guide)).
- **Where/when:** offline, on already-pulled folders, including runs 86–107. No new hold needed.
- **Prediction (i):** sticky holds show checkout sojourn > 500 ms from the trip until the end; released holds drop below 500 ms within seconds of recommendations' storm starting.
- **Confirms** the threshold mechanism if the sojourn separates the two modes cleanly on every existing hold. **Refutes** it if some released holds never exceed 500 ms, or some latched holds sit below it.
- **Also record** the gap (checkout trip time → recommendations first tick above ~560 req/s). The blend hypothesis predicts a gap of 10–50 s on every blend and no crossing on a sticky hold before ~250 s.

### 3. Score every hold sticky vs released
- **Rule (i, proposed):** sticky = checkout streak ≥ 400 and recommendations streak = 0; released = recommendations retry delta ≥ 100k. Anything else is "other". Store the score in the next results guide.
- **Why:** the current verdicts (blend / miss) hide the sticky vs released split.

### 4. Latch-rate estimation
- A 50/50 rate needs about 8 holds of one mix to separate it from 25% or 75% (rough binomial reasoning (i)). The disk copy already has 3 + 3 + 3 holds across three mixes; if the three mixes are pooled (a mix effect of 5 users is assumed small, (i)) that is 9 + earlier.
- Plan ≈ 8 more holds with a single mix, in the interleaved order below.

## Controls to apply

### A. Restart checkout and recommendations before each hold
Not done today (see the table). Do it as a **treatment**, alternating with no-restart holds, so it is a test and not another confound.
- **Commands:**
```powershell
ssh topfull-master "kubectl rollout restart deployment/checkoutservice deployment/recommendationservice -n default; kubectl rollout status deployment/checkoutservice -n default --timeout=180s; kubectl rollout status deployment/recommendationservice -n default --timeout=180s"
```
- **Hook point if automated:** an optional YAML key such as `restart_before_hold: [checkoutservice, recommendationservice]`, handled in `run()` after `apply_constraints(cfg)` and **before** `start_envoy_retry_collector(cfg)`. The collector seeds pod IPs via `discover_service_pod_ips`, and a restart changes them (v).
- Add a 60 s settle after rollout. The new pods start cold (JIT, caches, connection pools), which is exactly the effect under test.
- **Confirms** carry-over state if restarted holds latch at a clearly different rate than un-restarted ones. **Refutes** it if rates match.

### B. Interleave
Mixes A = 275/80, B = 275/85, C = 275/90 (post 100/90/5). Instead of AAA BBB CCC, use a fixed shuffled order, e.g. **B C A C A B A B C**, with restart on/off alternating within each mix. Timing, cluster age, and cool-off then spread across mixes and the mode no longer rides on order. Randomise with a recorded seed.

### C. Record, do not pin, the rest
Keep the Paper-C1 pin. Add the t=0 snapshot (check 1) and a post-hold `kubectl get pods -o wide` (`pods_end.txt`) to show whether any pod restarted mid-hold.

## Probe result

Runs 108–126 carried the restart, interleave, and t=0 snapshot checks described above; the table is in [2026-10-03-s2-latch-probe-results.md](2026-10-03-s2-latch-probe-results.md). Run116 failed the sampling gate, and run127 did not run. A restart does not explain the cluster difference: run108 is released and a blend, and run124, the second restart, is sticky. Hidden pod state in `state/t0.txt` does not explain it either. Run123 (released) and run124's pre-restart snapshot (sticky after the roll) share checkout pod `76zdj`, recommendations pod `jwsxh`, `topfull-worker1`, kernel `5.4.0-216-generic`, and worker boot `2026-10-04 06:49:12`.

## v2 probe result (runs 132–153)

Scores: [2026-10-04-s2-latch-probe-v2-results.md](2026-10-04-s2-latch-probe-v2-results.md). Re-read of the raw state files and CSVs:

- **Hidden state is ruled out as the cause (m).** On runs 108–153 checkout and recommendations sit on `topfull-worker1` with the same twelve co-tenant pods and kernel `5.4.0-216-generic`, and no pod is Pending at t=0. In the v2 series both pods were rolled before every hold (restart 0, age 7–17 min), and the untouched control still split: 132, 134, 151 released, 139 and 147 sticky, 143 other. Worker uptime has no threshold on the 2026-10-04 10:05 boot, which holds both classes from its first hour. Steal overlaps (sticky 0.05–0.10 on the worker, released 0.06–0.18).
- **No carry-over (m).** The classes of the 20 scored holds in order are R R R R R S R O S O S R R S S S R R O R. The previous hold's class does not predict the next (Fisher p = 1.0, runs test p ≈ 0.83). Hour of day does not either: 139 (sticky) and 140 (released) are both about 17:00 UTC.
- **Rates (m).** Untouched controls (111, 121, 129, 131, 132, 134, 139, 143, 147, 151): 4 sticky, 5 released, 1 other, P(sticky) 0.40, Wilson 95% 0.17–0.69. All base-mix holds (n = 19): 8 sticky, 10 released, 1 other. Both include 50%.
- **Original vs copy is untested (m).** The tally is 0/2 vs 8/17 sticky (Fisher p ≈ 0.49). v2 ran only on the copy. Do not claim a cluster difference from this data.
- **"Other" is a latch (m).** Runs 141, 143, and 152 are the sticky loop with a short streak break, see [2026-10-04-s2-checkout-latch.md](2026-10-04-s2-checkout-latch.md).
- **Reading (i).** The base mix behaves like a coin flip on a bistable system. Small timing noise decides which loop wins, and released holds can escape a latch late (runs 134, 135, 146, 153). The time clustering in runs 94–107 is not explained by pod state, previous hold, or hour. It may be chance.
- **Next checks (done 2026-10-05).** Escape-time rescore and Little's-law frontend concurrency: [2026-10-05-s2-latch-escape-time-rescore.md](2026-10-05-s2-latch-escape-time-rescore.md). Escape time agrees with sticky/released; "other" is `never`; late escapes are a duration class. Frontend L rises ~30 s before escape but does not separate escapers from sticky holds by level. More controls only for shrinking the rate CI; a direct queue gauge is optional if the trigger question stays open.
