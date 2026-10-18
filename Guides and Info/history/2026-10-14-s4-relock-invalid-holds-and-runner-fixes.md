# S4 relock matrix: why so many holds were INVALID, and what we changed

Date: 2026-10-14. Branch: `s4-relock-mode-matrix`. Run log: [2026-10-13-s4-relock-mode-matrix-run-log.md](../../docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md). Plan: [2026-10-13-s4-relock-mode-matrix.md](../../docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix.md).

## Why this doc exists

The S4 relock run log had 25 of its 34 gated launches marked INVALID (and 3 more launches that never reached the gate), many of them replayed once at the cost of another 12 minutes of VM time each. We checked what the gate was actually rejecting. Most of the rejections were not broken runs. This doc records what we found, what we changed, and what is still unknown.

## What was failing

The gate is `experiments/s3s4_mode_matrix_gate.py` plus the pass rules in the plan. Four distinct causes produced the INVALID lines.

| Cause | Holds affected | Real defect? |
|---|---|---|
| TopFull on, but `live5s_caps` was 0 | Every unconstrained TopFull-on hold (13–16, 19, 20), including all replays | No. Gate rule was wrong |
| Catalog `replica_count` 0 in a few samples | Many constrained holds (1, 2, 3, 5, 9, 10) | No. A readiness flap, not a failed run |
| Caps present while TopFull was off | Holds 7 and 8, both launches each | Yes. Leftover caps from an earlier hold |
| Locust rows outside 540–580 | Hold 3 replay (535 rows) | Yes, by the plan's own rule |

Hold 20's first launch is a separate one-off: `run_scenario.py` exited 1 after the hold because `mkdir` on master failed with "No space left on device".

### 1. TopFull never capped an unconstrained hold (gate bug)

The plan required `live5s_caps` of at least 1 whenever TopFull was on. In the unconstrained holds the catalog runs at 800m and is never the bottleneck. The detector shows catalog utilization peaking near 0.50 and `overloaded` stays 0, so TopFull correctly does nothing and every API sits at the unlimited sentinel 10000 for the whole run. Those holds are the reference for the constrained ones, so TopFull not acting is the expected result. By contrast the constrained holds show hundreds of `overloaded` samples on the catalog and the proxy thresholds move.

What proves TopFull was running is that its RL loop ran, not that it capped something. `deploy_rl.py` writes `num_agent.csv` only when it is on. That file exists in every TopFull-on hold, capped or not, and is absent in TopFull-off holds.

### 2. Catalog Not Ready flaps

`replica_count` in `resource_usage.csv` is the Deployment's `readyReplicas`, and Kubernetes omits that field when it is 0. So `replica_count` 0 means the pod was Not Ready. It does not mean the pod was deleted: the catalog pod showed 0 restarts after 8 hours.

The catalog readiness probe is an exec of `grpc_health_probe` with `timeoutSeconds: 1`, `periodSeconds: 10`, `failureThreshold: 3`. At a 100m limit the container is pinned at its limit (98–100m in the samples at the flap timestamps), so the probe process is throttled and can miss its 1 s deadline. Evidence for this is a correlation: the 800m catalog never flapped in the unconstrained run we checked, and the 100m catalog flapped in most constrained holds. The Kubernetes events from those windows had expired, so the cause is the likeliest one, not a verified one.

### 3. Leftover caps on TopFull-off holds

The four burst RetryGuard-only holds ran with `topfull_rl.enabled: false`. Their throttle files nonetheless show caps (`getproduct`, `getcart`, `postcheckout` at 10.0, `postcart` at 417.75316563183287, `emptycart` at 0.0) that match the final thresholds of hold 6, a TopFull-on hold that ended six minutes earlier, to the digit. The collector rows have `threshold_fresh=1`, so the proxy itself reported them, and the rows start at 10000 and switch to the caps one second later in hold 7.

The proxy starts every limiter at 10000 and also applies cap files from `proxy/rate_config/` when it receives SIGUSR1. The runner never cleared that directory and never checked the limits after starting the proxy. Earlier TopFull-off holds passed because no TopFull-on hold had run yet. Unconstrained holds 11 and 12 ran clean after hold 10 because hold 10 ended with almost no caps.

What we do not know is what applied hold 6's caps to a freshly started proxy. The directory was empty when we looked, and `deploy_rl.py` was not running in those holds. The fix below prevents the contamination from reaching a hold. It does not explain it.

### 4. Disk full on master

The failing `mkdir` was on `topfull-master`'s root disk (30G, 84% used when checked). It holds 565 run folders (3.8G) under `/home/idozacharia/experiments/results/` that the runner writes to and nothing prunes. Other large users are `/home/user` (6.7G), `/var` (4.7G) and `/tmp` (491M). Inodes were fine (12%). We could not see what filled the disk at the moment of failure, and 4.7G was free at inspection. We did not delete anything.

## What we changed

### Runner: proxy starts clean or the run aborts

In `experiments/run_scenario.py`:

- `kill_stale_master_processes` now ends by clearing `proxy/rate_config/`, and the proxy start clears it again just before launching.
- After the proxy's 5 s init, `ensure_proxy_uncapped` reads `/thresholds` the same way the throttle collector does (a proxied GET to `proxy_url` from master's `global_config.json`, loopback as the HTTP proxy). If any API is not 10000, or the read is empty, it restarts the proxy with `rate_config` cleared, up to two times, then raises. The error is re-raised before Locust starts.
- With TopFull off, the same check runs again just before Locust.
- On a failed check it prints the `rate_config` listing and any `deploy_rl`/Ray processes, to help find the source if it happens again.

### Runner: catalog probe tolerance

In `experiments/topfull_cpu_quotas.py`, `probe_settings_for` returns a tolerant probe (`timeoutSeconds` 5, `failureThreshold` 6) when the config's catalog CPU limit is below the Paper-C1 value, and the manifest default (1, 3) otherwise or on restore. `reconcile_paper_cpu_limits` patches both the readiness and the liveness probe with it. The start-of-run reconcile applies it. The end-of-run reconcile passes `restore_default_probes=True`, so the cluster returns to the manifest values after each hold. The CPU limit under test is unchanged.

The live Deployment was not patched by hand. It takes the new probe at the next constrained hold's preflight.

### Gate and plan: what counts as INVALID

`s3s4_mode_matrix_gate.py` now prints:

- `catalog_not_ready=N` with the timestamps of every Not Ready sample.
- `topfull_rl_ran=yes|no`, from a non-empty `num_agent.csv`.

The plan's pass rules changed to match, in all three sections (4A constrained, 4A unconstrained, 4B):

- TopFull on requires `topfull_rl_ran=yes`. `live5s_caps` is recorded and may be 0.
- A catalog `replica_count` 0 is recorded as `catalog_not_ready=N`. It is not a gate and never starts a replay. A `replica_count` above 1 is still a fail.
- A new rule near the top of the plan states that INVALID means a broken run: wrong config or CPU limits, a collector or RetryGuard that did not run, Locust rows outside 540–580, a TopFull-off hold whose proxy reported caps, or a route `timeout`. Not capping, Not Ready samples, a throttle FLAG and zero toggles are never INVALID and never start a replay.

### Run log: re-gated launches

Twenty launches changed from INVALID to PASS. Each line keeps its original reason, prefixed with `re-gated 2026-10-14` and a note that the reason is recorded, not a gate. A script checked that each reason was one of the two non-failures before flipping it. Five launches stay INVALID: holds 7 and 8 (both launches of each) and hold 3's replay. At the re-gate the S4A slice read 29 PASS, 5 INVALID and 3 not gated. The finished log, including the S4B lines and hold 28's pre-Locust not-gated line, reads 39 PASS, 5 INVALID and 4 not gated.

Holds 7 and 8 need to be run again under the new cleanup. For the guide columns, the first-launch folders of re-gated holds now qualify, so some replay folders are redundant. Which folder each column uses was left open.

### Tests

`experiments/test_run_scenario_proxy_guard.py` covers threshold parsing, cap detection, the restart-then-pass and abort-after-two-restarts paths, and the probe selection. Two existing mocked-ssh test classes in `test_run_scenario.py` now stub `ensure_proxy_uncapped`, since they only check start ordering. The experiments suite ran 602 passed and 1 failed. The failure is `test_steal_stat.py::test_script_has_no_carriage_returns`, a line-endings check on a shell script this work did not touch.

## Still open

- **Cause of the leftover caps.** The guard blocks it. If `ensure_proxy_uncapped` ever fires, its diagnostic output is the lead.
- **Live test of the guard.** Master had no proxy running when we finished, so the threshold read was not exercised end to end. The URL and port extraction was checked on master. The first hold under the new runner is the real test; a false abort would stop before Locust.
- **Probe fix unconfirmed.** The next constrained hold shows whether the Not Ready flaps stop. `catalog_not_ready` in the gate output is the check.
- **Disk.** Old pulled folders on master are still there.
- **Committed.** This doc, the runner, the gate, the quotas module, the tests, the plan, and the run log are on `s4-relock-mode-matrix`. The 4b YAML bumps are in `6930ec0`. The VM stop, push, and local merge are still ahead in Task 9.
