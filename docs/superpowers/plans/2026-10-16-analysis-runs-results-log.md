# Analysis-runs hold log

One line per finished hold. A flagged hold is recorded and the matrix continues.

`log_folder | exit | throttle | health | RG toggle counts`

analysis_s2_rg_only_normal_run1 | exit ok | throttle N/A TopFull off | health ok | RG toggles: no transition lines
analysis_s2_both_normal_run1 | exit ok | throttle ok | health ok | RG toggles: no transition lines
analysis_s2_tf_only_run1 | exit ok | throttle ok | health ok | RG off
analysis_s2_rg_only_burst_run1 | exit ok | throttle N/A TopFull off | health ok | RG toggles: frontend→checkout ON→OFF 3, 1→2 3, 2→3 2, burst 3; checkout 0→1 3
analysis_s2_both_burst_run1 | exit ok | throttle ok | health ok | RG toggles: frontend→checkout ON→OFF 4, 1→2 4, 2→3 4, burst 4; checkout 0→1 4
