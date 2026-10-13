# S3 and S4 mode matrix — run log

One line per launch, including a failed launch and its single replay.

`hold N | log_folder | PASS or INVALID | locust rows | note`

hold 1 | final_s3_rg_only_normal_run1 | INVALID | 682 | Paper-C1; checkout 200m; users 175/30/70/90/5; normal; TopFull off; toggles 1 (off 1, up 0, burst 0); frontend 4 on 171/171; TF live5s_10000=830 live5s_caps=0 live5s_zero=0 other=0; VS attempts 3; locust_rows=682 outside 540-580
hold 1 | final_s3_rg_only_normal_run1_r2 | PASS | 571 | Paper-C1; checkout 200m; users 175/30/70/90/5; normal; TopFull off; toggles 1 (off 1, up 0, burst 0); frontend 4 on 148/148; TF live5s_10000=710 live5s_caps=0 live5s_zero=0 other=0; VS attempts 3; START ok
hold 2 | final_s3_rg_only_normal_run2 | PASS | 572 | Paper-C1; checkout 200m; users 175/30/70/90/5; normal; TopFull off; toggles 1 (off 1, up 0, burst 0); frontend 4 on 149/149; TF live5s_10000=715 live5s_caps=0 live5s_zero=0 other=0; VS attempts 3; START ok
hold 3 | final_s3_both_normal_run1 | PASS | 566 | Paper-C1; checkout 200m; users 175/30/70/90/5; normal; TopFull on; toggles 1 (off 1, up 0, burst 0); frontend 4 on 149/149; TF live5s_10000=596 live5s_caps=151 live5s_zero=128 other=0; VS attempts 3; START ok
hold 4 | final_s3_both_normal_run2 | PASS | 567 | Paper-C1; checkout 200m; users 175/30/70/90/5; normal; TopFull on; toggles 1 (off 1, up 0, burst 0); frontend 4 on 149/149; TF live5s_10000=595 live5s_caps=155 live5s_zero=140 other=0; VS attempts 3; START ok
hold 5 | final_s3_tf_only_run1 | PASS | 568 | Paper-C1; checkout 200m; users 175/30/70/90/5; tf; TopFull on; toggles n/a; frontend 4 on 144/144; TF live5s_10000=565 live5s_caps=163 live5s_zero=172 other=0; VS attempts 3; START ok
hold 6 | final_s3_tf_only_run2 | PASS | 566 | Paper-C1; checkout 200m; users 175/30/70/90/5; tf; TopFull on; toggles n/a; frontend 4 on 144/144; TF live5s_10000=544 live5s_caps=186 live5s_zero=160 other=0; VS attempts 3; START ok
hold 7 | final_s3_rg_only_burst_run1 | PASS | 572 | Paper-C1; checkout 200m; users 175/30/70/90/5; burst_rpr 2.0; TopFull off; toggles 1 (off 1, up 0, burst 0); frontend 4 on 148/148; TF live5s_10000=710 live5s_caps=0 live5s_zero=0 other=0; VS attempts 3; START ok
hold 8 | final_s3_rg_only_burst_run2 | PASS | 571 | Paper-C1; checkout 200m; users 175/30/70/90/5; burst_rpr 2.0; TopFull off; toggles 1 (off 1, up 0, burst 0); frontend 4 on 149/149; TF live5s_10000=715 live5s_caps=0 live5s_zero=0 other=0; VS attempts 3; START ok
hold 9 | final_s3_both_burst_run1 | PASS | 565 | Paper-C1; checkout 200m; users 175/30/70/90/5; burst_rpr 2.0; TopFull on; toggles 1 (off 1, up 0, burst 0); frontend 4 on 149/149; TF live5s_10000=595 live5s_caps=153 live5s_zero=132 other=0; VS attempts 3; START ok
hold 10 | final_s3_both_burst_run2 | PASS | 566 | Paper-C1; checkout 200m; users 175/30/70/90/5; burst_rpr 2.0; TopFull on; toggles 1 (off 1, up 0, burst 0); frontend 4 on 172/172; TF live5s_10000=596 live5s_caps=149 live5s_zero=120 other=0; VS attempts 3; START ok
