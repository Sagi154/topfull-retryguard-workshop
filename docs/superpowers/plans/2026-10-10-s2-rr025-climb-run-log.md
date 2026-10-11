# S2 re-enable 0.25 and tighter climb — run log

One line per hold, including a failed hold and any single replay.

`hold N | log_folder | PASS or INVALID | locust rows | START reenable and climb values | note`

hold 1 | study3_s2_rr025_rgtf0 | PASS | 562 | reenable_rejection=0.25 climb_rpr_1_to_2=0.17 climb_rpr_2_to_3=0.33 | frontend 4 on 139/139; TF off live thresholds all 10000 (165 fresh, 0 real caps); VS attempts 3, no route timeout; no PATCH_FAIL or traceback
hold 2 | study3_s2_rr025_rgtf1 | PASS | 564 | reenable_rejection=0.25 climb_rpr_1_to_2=0.17 climb_rpr_2_to_3=0.33 | frontend 4 on 140/140; TF on 152 live caps below 10000; VS attempts 3, no route timeout; no PATCH_FAIL or traceback
hold 3 | study3_s2_rr025_c1025_rgtf0 | PASS | 565 | reenable_rejection=0.25 climb_rpr_1_to_2=0.10 climb_rpr_2_to_3=0.25 | frontend 4 on 139/139; TF off live thresholds all 10000 (120 fresh, 0 real caps); VS attempts 3, no route timeout; no PATCH_FAIL or traceback
hold 4 | study3_s2_rr025_c1025_rgtf1 | PASS | 561 | reenable_rejection=0.25 climb_rpr_1_to_2=0.10 climb_rpr_2_to_3=0.25 | frontend 4 on 139/139; TF on 294 live caps below 10000; VS attempts 3, no route timeout; no PATCH_FAIL or traceback
hold 5 | study3_s2_rr020_c1025_rgtf0 | PASS | 566 | reenable_rejection=0.20 climb_rpr_1_to_2=0.10 climb_rpr_2_to_3=0.25 | frontend 4 on 139/139; TF off live thresholds all 10000 (110 fresh, 0 real caps); VS attempts 3, no route timeout; no PATCH_FAIL or traceback
hold 6 | study3_s2_rr020_c1025_rgtf1 | PASS | 562 | reenable_rejection=0.20 climb_rpr_1_to_2=0.10 climb_rpr_2_to_3=0.25 | frontend 4 on 139/139; TF on 1133 live caps below 10000; VS attempts 3, no route timeout; no PATCH_FAIL or traceback

