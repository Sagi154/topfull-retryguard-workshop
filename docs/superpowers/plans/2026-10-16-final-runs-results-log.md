# Final runs results log

Re-run of the 60-hold matrix into `experiments/results/final_runs_results/`. Replica pin is a gate. The unpinned pass stays in [2026-10-16-analysis-runs-results-log.md](2026-10-16-analysis-runs-results-log.md).

`log_folder | exit | throttle | health | replicas | RetryGuard toggles`

- analysis_s2_rg_only_normal_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 6, 1→2 3, 2→3 2; checkout 0→1 5; frontend→recommendations ON→OFF 4, 1→2 3, 2→3 3; recommendations 0→1 4
- analysis_s2_both_normal_run1 | exit ok | throttle ok | health RL STALL (2 RL_RPS_TIMEOUT ProxyError at 11:00:41Z and 11:00:42Z, 6 s after load end 11:00:35Z) | replicas frontend=4 catalog=1 | frontend→recommendations ON→OFF 3, 1→2 3, 2→3 2; recommendations OFF→ON 3
- analysis_s2_tf_only_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_s2_rg_only_burst_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 10, 1→2 5, 2→3 4; checkout OFF→ON 9; frontend→recommendations ON→OFF 5; recommendations OFF→ON 5
- analysis_s2_both_burst_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 11, 1→2 6, 2→3 6; checkout OFF→ON 10; frontend→recommendations ON→OFF 5, 1→2 4, 2→3 4; recommendations OFF→ON 5
- analysis_s2_both_burst_run2 | exit failed | SSH to topfull-load timed out during banner exchange before Locust started (rc=255). Not pulled. Same slot re-run.
- analysis_s2_both_burst_run2 | exit ok (re-run) | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 5, 1→2 4, 2→3 4; checkout OFF→ON 5; frontend→recommendations ON→OFF 11, 1→2 3; recommendations OFF→ON 10
- analysis_s2_rg_only_burst_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 10, 1→2 4, 2→3 2; checkout OFF→ON 9; frontend→recommendations ON→OFF 8; recommendations OFF→ON 7
- analysis_s2_tf_only_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_s2_both_normal_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend→recommendations ON→OFF 1, 1→2 1, 2→3 1; recommendations OFF→ON 1
- analysis_s2_rg_only_normal_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 6, 1→2 4, 2→3 2; checkout OFF→ON 5; frontend→recommendations ON→OFF 5, 1→2 4; recommendations OFF→ON 5
- analysis_s3_rg_only_normal_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 1
- analysis_s3_both_normal_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s3_tf_only_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_s3_rg_only_burst_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 1
- analysis_s3_both_burst_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 3; checkout OFF→ON 2
- analysis_s3_both_burst_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 4; checkout OFF→ON 3
- analysis_s3_rg_only_burst_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 1
- analysis_s3_tf_only_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_s3_both_normal_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s3_rg_only_normal_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→checkout ON→OFF 1
- analysis_4a_constrained_rg_only_normal_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→catalog ON→OFF 5, 1→2 3, 2→3 2; catalog OFF→ON 5; recommendations→catalog ON→OFF 5, 1→2 3, 2→3 2; frontend→recommendations ON→OFF 1
- analysis_4a_constrained_both_normal_run1 | exit ok | throttle ok | health RL STALL (2 RL_RPS_TIMEOUT at 17:49:06Z) | replicas frontend=4 catalog=1 | frontend→catalog ON→OFF 3, 1→2 3, 2→3 3; catalog OFF→ON 3
- analysis_4a_constrained_tf_only_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_4a_constrained_rg_only_burst_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→catalog ON→OFF 4, 1→2 1, 2→3 1; catalog OFF→ON 3; recommendations→catalog ON→OFF 4, 1→2 1, 2→3 1; frontend→recommendations ON→OFF 1
- analysis_4a_constrained_both_burst_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend→catalog ON→OFF 8, 1→2 5, 2→3 3; catalog OFF→ON 7; frontend→recommendations ON→OFF 2, 1→2 2, 2→3 1; recommendations OFF→ON 2
- analysis_4a_constrained_both_burst_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend→catalog ON→OFF 1, 1→2 1, 2→3 1; catalog OFF→ON 1; recommendations→catalog ON→OFF 1, 1→2 1, 2→3 1; frontend→recommendations ON→OFF 7, 1→2 3, 2→3 2; recommendations OFF→ON 7
- analysis_4a_constrained_rg_only_burst_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→catalog ON→OFF 4; catalog OFF→ON 3; frontend→recommendations ON→OFF 1
- analysis_4a_constrained_tf_only_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_4a_constrained_both_normal_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend→recommendations ON→OFF 2, 1→2 2, 2→3 2; recommendations OFF→ON 2
- analysis_4a_constrained_rg_only_normal_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend→catalog ON→OFF 2; catalog OFF→ON 1; frontend→recommendations ON→OFF 1
- analysis_4a_unconstrained_rg_only_normal_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4a_unconstrained_both_normal_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4a_unconstrained_tf_only_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_4a_unconstrained_rg_only_burst_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4a_unconstrained_both_burst_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4a_unconstrained_both_burst_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4a_unconstrained_rg_only_burst_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4a_unconstrained_tf_only_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_4a_unconstrained_both_normal_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4a_unconstrained_rg_only_normal_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4b_rg_only_normal_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4b_both_normal_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4b_tf_only_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_4b_rg_only_burst_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4b_both_burst_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4b_both_burst_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4b_rg_only_burst_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4b_tf_only_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_4b_both_normal_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_4b_rg_only_normal_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s1_rg_only_normal_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s1_both_normal_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s1_tf_only_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_s1_rg_only_burst_run1 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s1_both_burst_run1 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s1_both_burst_run2 | exit ok | throttle FLAGGED (2 fetch failed at 04:26:45Z end-of-run Connection refused) | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s1_rg_only_burst_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s1_tf_only_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
- analysis_s1_both_normal_run2 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no toggles
- analysis_s1_rg_only_normal_run2 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | no toggles

## Matrix summary (Task 6)

Folder count under experiments/results/final_runs_results/: **60** (layout check: each group has rg_only x2 per mode, both x2 per mode, tf_only x2 under normal only; S4A constrained+unconstrained share the S4A tree so those variant folders have 4 each).

Throttle audit (python experiments/throttle_flags.py audit --root experiments/results/final_runs_results): runs=60 flagged=1 topfull_on_flagged=1 — only analysis_s1_both_burst_run2.

| Count | Status |
| --- | ---: |
| Finished holds | 60 |
| Clean | 57 |
| Flagged (finished) | 3 |
| Aborted then same-slot re-run (clean) | 1 (analysis_s2_both_burst_run2) |

### Flagged holds (user re-run decision)

| log_folder | Flag | Reason |
| --- | --- | --- |
| analysis_s2_both_normal_run1 | RL STALL | 2 RL_RPS_TIMEOUT ProxyError at 11:00:41Z and 11:00:42Z (6 s after load end 11:00:35Z) |
| analysis_4a_constrained_both_normal_run1 | RL STALL | 2 RL_RPS_TIMEOUT at 17:49:06Z |
| analysis_s1_both_burst_run2 | throttle FLAGGED | 2 fetch failed at 04:26:45Z end-of-run Connection refused |

Every committed hold had frontend replicas **4** and catalog replicas **1** for the whole run (replica pin gate). The unpinned 20 in analysis_runs_results/ are not this matrix.

## Re-runs (run3)

`log_folder | exit | throttle | health | replicas | RetryGuard toggles | replaces`

- analysis_s2_both_normal_run3 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend?recommendations ON?OFF 3, 1?2 2, 2?3 2; recommendations OFF?ON 2 | replaces analysis_s2_both_normal_run1- analysis_4a_constrained_both_normal_run3 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | frontend?recommendations ON?OFF 3, 1?2 3, 2?3 3; recommendations OFF?ON 3 | replaces analysis_4a_constrained_both_normal_run1
