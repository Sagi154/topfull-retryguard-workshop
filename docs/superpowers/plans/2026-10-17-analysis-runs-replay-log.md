# Analysis-runs replay log

One line per finished hold. A flagged hold is recorded and the campaign continues. These holds do not replace run 1 or run 2. `analysis_s2_both_normal_run4` does not replace `analysis_s2_both_normal_run3`.

`log_folder | exit | throttle | health | replicas | RetryGuard toggles`

analysis_s2_rg_only_normal_run3 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | frontend->recommendationservice ON->OFF 1, 1->2 1, 2->3 1; recommendationservice OFF->ON 1; frontend->checkoutservice ON->OFF 6, 1->2 1, 2->3 1; checkoutservice OFF->ON 6
analysis_s2_both_normal_run4 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | no transition lines
analysis_s2_tf_only_run3 | exit ok | throttle ok | health ok | replicas frontend=4 catalog=1 | RG off
analysis_s2_rg_only_burst_run3 | exit ok | throttle N/A TopFull off | health ok | replicas frontend=4 catalog=1 | checkoutservice OFF->ON 14; frontend->checkoutservice ON->OFF 15; frontend->checkoutservice burst 15
