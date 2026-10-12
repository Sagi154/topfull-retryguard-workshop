# S3 checkout 200 m then 100 m, both on — run log

One line per hold, including a failed hold and any single replay.

`hold N | log_folder | PASS or INVALID | locust rows | note`

hold 1 | s3_ck200_rgtf1 | PASS | 562 | checkout 200m; users 175/30/70/90/5; normal; RetryGuard on; TopFull on; toggles 1 (off 1, up 0); frontend 4 on 149/149; capacity checkout 200m; TF live5s_10000=597 live5s_caps=147 live5s_zero=116 other=0; VS attempts 3; START ok
hold 2 | s3_ck100_rgtf1 | PASS | 563 | checkout 100m; users 175/30/70/90/5; normal; RetryGuard on; TopFull on; toggles 1 (off 1, up 0); frontend 4 on 149/149; capacity checkout 100m; TF live5s_10000=594 live5s_caps=162 live5s_zero=164 other=0; VS attempts 3; START ok
