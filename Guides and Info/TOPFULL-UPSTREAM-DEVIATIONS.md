# Deviations from upstream TopFull in the live copy

The repo's `TopFull/` submodule is upstream (kaist-ina/TopFull) and is not edited. The live copy on master (`/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/`) already differs from it by path rewrites and Ron's local edits ([RON-NEZER-SETUP-VS-WORKSHOP.md](RON-NEZER-SETUP-VS-WORKSHOP.md)). This file lists changes **we** made to TopFull's code, so a paper reader can tell what ran.

## 1. RL loop proxy timeout and log lines (2026-10-16, plan [2026-10-16-proxy-fd-limit-and-rl-stall-flag.md](../docs/superpowers/plans/2026-10-16-proxy-fd-limit-and-rl-stall-flag.md))

| File on master | Change | Why |
|---|---|---|
| `overload_detection.py` | `Detector.current_rps()` calls `requests.get(..., timeout=2.0)`; on failure raises `ProxyStatsUnavailable`. `Detector.__init__` catches that timeout, prints `RL_SKIP where=init`, and uses an empty dict so each API's initial threshold stays 10000 for that startup. New `RL_RPS_*` and `RL_CAP_APPLY` print lines | Upstream has no timeout. When the proxy ran out of file descriptors on 2026-10-15 the call blocked the RL loop for 422 s and 559 s ([evidence](history/2026-10-15-proxy-fd-evidence-flagged-holds.md)). A timeout during construction used to exit `deploy_rl.py` with no next tick |
| `deploy_rl.py` | `Agent.run()`, `Agent.add_apis()` and the main loop catch `ProxyStatsUnavailable` and skip that tick. New `RL_LOOP_START` and `RL_SKIP` print lines | The skipped tick retries on the next one (every 1-2 s). Detector construction is a separate catch: it keeps threshold 10000 for that startup |

Applied by `experiments/patch_rl_timeout.py` (marker `RL_TIMEOUT_PATCH v1`); the runner refuses a TopFull-on hold if the marker is missing. Originals are kept as `*.orig-<timestamp>` next to the files on master.

**Behavior.** When the proxy answers, the data, the decisions, and the caps are identical to upstream. On a `/stats` timeout, `current_rps()` waits 2 s and raises `ProxyStatsUnavailable` (`RL_RPS_TIMEOUT` is already printed there). `Agent.run()`, `Agent.add_apis()`, and the main loop catch that and skip the tick, which retries on the next one (every 1-2 s). Detector construction also catches the timeout and uses threshold 10000 for that startup. Upstream waits until the proxy answers (or forever). That is a robustness fix, not a change to the control algorithm when the proxy answers. It is still a change to TopFull's code.

**Open decision (user and mentors):** do the mentors accept a modified TopFull for the paper, with this table as the disclosure? If not, the alternative is to leave TopFull untouched and rely only on the descriptor fix: with the limit raised the stall should not occur, and the `RL STALL` flag would then mark any hold where it still does. Until answered, holds run with the patch are labelled by this file, not silently.
