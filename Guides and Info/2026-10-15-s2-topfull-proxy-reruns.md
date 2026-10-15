# S2 TopFull proxy-log re-runs (2026-10-15)

**Status: partial.** Holds 1 and 2 of the plan ran. Holds 3 and 4 (`final_s2_tf_only_run4`, `final_s2_both_burst_run4`) were not run. Plan: [2026-10-15-s2-topfull-proxy-logs.md](../docs/superpowers/plans/2026-10-15-s2-topfull-proxy-logs.md). Run log: [2026-10-15-s2-topfull-proxy-logs-run-log.md](../docs/superpowers/plans/2026-10-15-s2-topfull-proxy-logs-run-log.md).

## 1. Why we did this

In the 2026-10-14 S2 mode matrix, TopFull had no usable cap for most of `final_s2_tf_only_run2` and `final_s2_both_burst_run2` (throttle FLAG, 280 s and 565 s stale). The runner did not keep the TopFull proxy or RL output, so we could not tell whether TopFull stopped working or only our collector stopped reading it. The plan: save both logs with UTC stamps, add a tool that dates a stall, and re-run the two blind cells.

## 2. What we built

| Change | Where |
|---|---|
| Runner pipes the Go proxy and `deploy_rl.py` stdout and stderr through a bash `stamp()` function (UTC second stamp per line) into `src/logs/topfull_proxy.log` and `src/logs/topfull_rl.log`; both are pulled with the run folder | `experiments/run_scenario.py`, `experiments/test_run_scenario.py` |
| `topfull_health.py <run_dir>` reads the two logs plus `topfull_throttle_collector.log` and prints a `proxy:` line (monitor ticks, longest gap, last cap apply) and an `rl:` line (longest silence) | `experiments/topfull_health.py`, `experiments/test_topfull_health.py` |
| Docs: file table rows and the post-hold check | [METRICS-GATHERED.md](METRICS-GATHERED.md), `AGENTS.md` §6 |
| Cluster pinned for the holds: frontend HPA min=max=4, catalog HPA min=max=1, sidecar `proxyCPU=90m`, `proxyCPULimit` unset | cluster, Task 3 |

Master's bash handles the `stamp()` function; the `current_rps` call in master's `overload_detection.py` has no `timeout=` (`requests.get(url, proxies=proxies)`, line 512), and `deploy_rl.py` calls it at lines 115 and 177.

## 3. Holds run

| Hold | Folder | Result | Locust rows | Throttle |
|---|---|---|---|---|
| 1 | `final_s2_tf_only_run3` | PASS | 554 | FLAG, 168 fetch warnings, first 13:23:35 |
| 2 | `final_s2_both_burst_run3` | PASS | 557 | FLAG, 224 fetch warnings, first 13:39:00 |
| 3 | `final_s2_tf_only_run4` | not run | | |
| 4 | `final_s2_both_burst_run4` | not run | | |

Both holds used Paper-C1, mix 275/90/100/90/5, VS attempts 3. Hold 2 had 2 RetryGuard toggles (1 off, 1 up, 0 burst).

## 4. What the logs show

**Did TopFull stop working? Yes, in both holds, and the logs date it.** The Go proxy ran out of file descriptors.

- Master's proxy process has `Max open files 1024 1048576` (soft 1024, hard 1,048,576).
- Hold 2, descriptors sampled every ~14 s: 5 until Locust started; 151 at 13:38:15; 609 at 13:38:44; **1024 from 13:38:58 to 13:48:03**; 4 after shutdown.
- The proxy log starts logging `http: Accept error: accept tcp [::]:8090: accept4: too many open files` at 13:38:55 (hold 2, 568 lines) and 13:23:32 (hold 1, 429 lines).
- The RL loop goes silent at the same moment: hold 1 longest silence **422 s** from 13:23:32; hold 2 **559 s** from 13:38:57. In hold 1 the RL loop's last line before the silence is `['recommendationservice']`, so it blocked in `clustering()` → `current_rps()`, a call with no timeout.
- The proxy's own once-a-second monitor kept ticking (727 and 757 ticks, no gap over 5 s). The proxy was alive; it just could not accept the admin calls.
- Hold 1's last cap apply while the hold ran was 13:23:31. The two applies at 13:30:35 came after shutdown unblocked the RL loop.

Chain: the descriptor limit saturates within about two minutes of load, admin calls to `/stats` and `/thresholds` stall, the throttle collector (0.8 s timeout) records stale values, and the RL loop blocks with no timeout, so no new caps are set.

## 5. What this changes in the earlier reading

The S2 `tf_only` and `both_burst` holds before this (run1, run2) were TopFull on in name but with TopFull blind for much of the hold. Cap and admitted-rate numbers on them stay carried, not measured. Goodput and P95 are valid as measured, but they describe a TopFull that stopped adjusting caps partway through, so the [controller activation](2026-10-15-s2-controller-activation-analysis.md) conclusions about what TopFull contributes should be read with that. Holds run3 are subject to the same stall and are flagged, so they do not fix this on their own.

## 6. Open

- The root cause is not fixed. Not applied: raise `ulimit -n` for the proxy launch, and add `timeout=` to `requests.get` in `current_rps()` / `clustering()`. Until one of those is done, every TopFull-on hold of this load will stall the same way, so re-running holds 3 and 4 as planned would reproduce it.
- Holds 3 and 4 were not run. Next free slot for `s2_tf_only.yaml` and `s2_both_burst.yaml` is run 4 (both YAMLs already say 4).
- The cluster restore (Task 5: frontend HPA 1–4, catalog HPA 1–2, sidecar `proxyCPU=100m`) was not recorded as done, and the VMs did not answer SSH afterwards. Check the live shape before the next hold.

## 7. Related

[METRICS-GATHERED.md](METRICS-GATHERED.md), [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md), [2026-10-14-s2-mode-matrix-abc.md](2026-10-14-s2-mode-matrix-abc.md), [2026-10-15-s2-controller-activation-analysis.md](2026-10-15-s2-controller-activation-analysis.md).
