# TopFull throttle data-quality audit

Audit date 2026-10-15. Every leaf run folder under `experiments/results/final results/` is included. `campaign_48/`, `august_38/`, and other `experiments/results/` trees are not.

Status uses `analysis_score.throttle_quality`, the same function that prints the `Throttle data quality` table. A hold is **FLAGGED** when `topfull_throttle_collector.log` contains any `fetch failed` WARNING, or when any API goes longer than 30 s with no fresh threshold read or no fresh admitted read. The normal Layer A poll is 5 s, so a 5–6 s hole is expected. A missing or empty `topfull_throttle.csv` is **N/A** (no throttle data), including when TopFull was off or the hold predates the collector. N/A is not a flag.

The longest gap is `analysis_score._longest_gap`: time from the first CSV row to the first fresh read, between fresh reads, and from the last fresh read to the last row. The percent stale is the share of that API's first-to-last span that sits inside stretches longer than 30 s. The table shows the worst API for each signal. A live threshold of 10000 is no cap. A live 0 is an empty read. Fresh admitted rates use `admitted_fresh==1` only.

## 1. Summary

144 run folders scanned: **50 FLAGGED**, **94 CLEAN**, **0 N/A**.

TopFull on means the variant folder is `both` or `tf_only`. TopFull off means `rg_only` or `both_off`.

| Scenario | Mode | Variant | TopFull | Runs | Flagged | Clean | N/A |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| S1 | normal | both | on | 6 | 0 | 6 | 0 |
| S1 | normal | tf_only | on | 6 | 0 | 6 | 0 |
| S1 | normal | rg_only | off | 4 | 0 | 4 | 0 |
| S1 | burst | both | on | 6 | 0 | 6 | 0 |
| S1 | burst | rg_only | off | 4 | 0 | 4 | 0 |
| S2 | normal | both | on | 12 | 3 | 9 | 0 |
| S2 | normal | tf_only | on | 3 | 1 | 2 | 0 |
| S2 | normal | rg_only | off | 8 | 2 | 6 | 0 |
| S2 | burst | both | on | 3 | 2 | 1 | 0 |
| S2 | burst | rg_only | off | 3 | 2 | 1 | 0 |
| S3 | normal | both | on | 5 | 0 | 5 | 0 |
| S3 | normal | tf_only | on | 4 | 0 | 4 | 0 |
| S3 | normal | rg_only | off | 5 | 1 | 4 | 0 |
| S3 | burst | both | on | 4 | 0 | 4 | 0 |
| S3 | burst | rg_only | off | 4 | 0 | 4 | 0 |
| S4A | normal | both | on | 11 | 5 | 6 | 0 |
| S4A | normal | tf_only | on | 11 | 6 | 5 | 0 |
| S4A | normal | rg_only | off | 10 | 9 | 1 | 0 |
| S4A | burst | both | on | 12 | 8 | 4 | 0 |
| S4A | burst | rg_only | off | 13 | 11 | 2 | 0 |
| S4B | normal | both | on | 2 | 0 | 2 | 0 |
| S4B | normal | tf_only | on | 2 | 0 | 2 | 0 |
| S4B | normal | rg_only | off | 2 | 0 | 2 | 0 |
| S4B | burst | both | on | 2 | 0 | 2 | 0 |
| S4B | burst | rg_only | off | 2 | 0 | 2 | 0 |
| **All** | | | | **144** | **50** | **94** | **0** |

Of the flagged holds, 25 have TopFull on and 25 have TopFull off. S4A accounts for 39 of the 50 flags (19 with TopFull on). S1 and S4B are clean on every hold. S2 has 10 flags. S3 has 1 flag.

## 2. Every scanned run

Path is relative to `experiments/results/final results/`. Per-API gaps are `threshold seconds / admitted seconds`. The percent column is the worst API: `threshold % / admitted %` of the span that falls in a hole longer than 30 s. A FLAGGED row can still show 0% when the only cause is a `fetch failed` warning that recovered inside 30 s.

| Path | Variant | TopFull | Status | Fetch-failed warnings | Longest stale gap per API (threshold s / admitted s) | % of span stale (threshold / admitted) |
| --- | --- | --- | --- | ---: | --- | --- |
| `S1_normal_operation_burst/both/final_s1_both_burst_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_burst/both/final_s1_both_burst_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_burst/both/s1_burst20_rgtf1_rep1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_burst/both/s1_burst20_rgtf1_rep1_r2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_burst/both/s1_burst20_rgtf1_rep2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_burst/both/s1_burst20_rgtf1_rep2_r2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_burst/rg_only/s1_burst20_rgtf0_rep1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_burst/rg_only/s1_burst20_rgtf0_rep2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/both/final_s1_both_normal_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/both/final_s1_both_normal_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/both/s1_normal_rgtf1_rep1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/both/s1_normal_rgtf1_rep1_r2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/both/s1_normal_rgtf1_rep2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/both/s1_normal_rgtf1_rep2_r2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/rg_only/s1_normal_rgtf0_rep1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/rg_only/s1_normal_rgtf0_rep2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/tf_only/final_s1_tf_only_run1` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/tf_only/final_s1_tf_only_run2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/tf_only/s1_normal_tf1rg0_rep1` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/tf_only/s1_normal_tf1rg0_rep1_r2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/tf_only/s1_normal_tf1rg0_rep2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S1_normal_operation_normal/tf_only/s1_normal_tf1rg0_rep2_r2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_burst/both/final_s2_both_burst_run1` | both | on | FLAGGED | 196 | getproduct 494/494; postcheckout 494/494; getcart 494/494; postcart 494/494; emptycart 494/494 | 69.1% / 69.1% |
| `S2_sustained_overload_burst/both/final_s2_both_burst_run2` | both | on | FLAGGED | 224 | getproduct 565/565; postcheckout 565/565; getcart 565/565; postcart 565/565; emptycart 565/565 | 79.0% / 79.0% |
| `S2_sustained_overload_burst/both/s2_burst20_rgtf1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run2` | rg_only | off | FLAGGED | 16 | getproduct 45/45; postcheckout 45/45; getcart 45/45; postcart 45/45; emptycart 45/45 | 6.3% / 6.3% |
| `S2_sustained_overload_burst/rg_only/s2_burst20_rgtf0` | rg_only | off | FLAGGED | 220 | getproduct 555/555; postcheckout 555/555; getcart 555/555; postcart 555/555; emptycart 555/555 | 77.8% / 77.8% |
| `S2_sustained_overload_normal/both/final_s2_both_normal_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/both/final_s2_both_normal_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/both/s2_normal_rgtf1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/both/study4_s2_tune_rgtf1_rep1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/both/study4_s2_tune_rgtf1_rep2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/both/study4_s2_tune_rgtf1_rep3` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/both/study4_s2_tune_rgtf1_rep4` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep1` | both | on | FLAGGED | 204 | getproduct 513/513; postcheckout 513/513; getcart 513/513; postcart 513/513; emptycart 513/513 | 71.7% / 71.7% |
| `S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep2` | both | on | FLAGGED | 218 | getproduct 5/550; postcheckout 5/550; getcart 5/550; postcart 5/550; emptycart 5/550 | 0.0% / 76.8% |
| `S2_sustained_overload_normal/both/study7_s2_normal_rgtf1_rep1` | both | on | FLAGGED | 40 | getproduct 5/105; postcheckout 5/105; getcart 5/105; postcart 5/105; emptycart 5/105 | 0.0% / 14.7% |
| `S2_sustained_overload_normal/both/study7_s2_normal_rgtf1_rep2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/both/study7_s2_normal_rgtf1_rep3` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/rg_only/s2_normal_rgtf0` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/rg_only/study4_s2_tune_rgtf0_rep1` | rg_only | off | CLEAN | 0 | getproduct 1/5; postcheckout 1/5; getcart 1/5; postcart 1/5; emptycart 1/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/rg_only/study4_s2_tune_rgtf0_rep1_r2` | rg_only | off | CLEAN | 0 | getproduct 1/5; postcheckout 1/5; getcart 1/5; postcart 1/5; emptycart 1/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/rg_only/study4_s2_tune_rgtf0_rep2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep1` | rg_only | off | FLAGGED | 224 | getproduct 565/565; postcheckout 565/565; getcart 565/565; postcart 565/565; emptycart 565/565 | 79.1% / 79.1% |
| `S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep2` | rg_only | off | FLAGGED | 216 | getproduct 545/545; postcheckout 545/545; getcart 545/545; postcart 545/545; emptycart 545/545 | 76.3% / 76.3% |
| `S2_sustained_overload_normal/tf_only/final_s2_tf_only_run1` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2` | tf_only | on | FLAGGED | 110 | getproduct 280/280; postcheckout 280/280; getcart 280/280; postcart 280/280; emptycart 280/280 | 40.5% / 40.5% |
| `S2_sustained_overload_normal/tf_only/s2_normal_tf1rg0` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_burst/both/final_s3_both_burst_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_burst/both/final_s3_both_burst_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_burst/both/final_s3_both_burst_run3` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_burst/both/final_s3_both_burst_run4` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run3` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run4` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/both/final_s3_both_normal_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/both/final_s3_both_normal_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/both/final_s3_both_normal_run3` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/both/final_s3_both_normal_run4` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/both/s3_ck200_rgtf1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1` | rg_only | off | FLAGGED | 0 | getproduct 55/55; postcheckout 55/55; getcart 55/55; postcart 55/55; emptycart 55/55 | 6.3% / 6.3% |
| `S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1_r2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run3` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run4` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run1` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run3` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run4` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run1_r2` | both | on | FLAGGED | 226 | getproduct 5/570; postcheckout 5/570; getcart 5/570; postcart 5/570; emptycart 5/570 | 0.0% / 79.9% |
| `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2` | both | on | FLAGGED | 228 | getproduct 575/575; postcheckout 575/575; getcart 575/575; postcart 575/575; emptycart 575/575 | 80.6% / 80.6% |
| `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2_r2` | both | on | FLAGGED | 224 | getproduct 562/565; postcheckout 562/565; getcart 562/565; postcart 562/565; emptycart 562/565 | 78.8% / 79.2% |
| `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3` | both | on | FLAGGED | 226 | getproduct 5/568; postcheckout 5/568; getcart 5/568; postcart 5/568; emptycart 5/568 | 0.0% / 78.9% |
| `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3_r2` | both | on | FLAGGED | 222 | getproduct 558/560; postcheckout 558/560; getcart 558/560; postcart 558/560; emptycart 558/560 | 77.1% / 77.3% |
| `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4` | both | on | FLAGGED | 226 | getproduct 570/570; postcheckout 570/570; getcart 570/570; postcart 570/570; emptycart 570/570 | 78.8% / 78.8% |
| `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4_r2` | both | on | FLAGGED | 228 | getproduct 572/574; postcheckout 572/574; getcart 572/574; postcart 572/574; emptycart 572/574 | 78.8% / 79.1% |
| `S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run1_r2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run2_r2` | both | on | FLAGGED | 216 | getproduct 545/545; postcheckout 545/545; getcart 545/545; postcart 545/545; emptycart 545/545 | 76.1% / 76.1% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1` | rg_only | off | FLAGGED | 228 | getproduct 574/574; postcheckout 574/574; getcart 574/574; postcart 574/574; emptycart 574/574 | 81.0% / 81.0% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1_r2` | rg_only | off | FLAGGED | 226 | getproduct 569/569; postcheckout 569/569; getcart 569/569; postcart 569/569; emptycart 569/569 | 80.1% / 80.1% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2` | rg_only | off | FLAGGED | 230 | getproduct 578/578; postcheckout 578/578; getcart 578/578; postcart 578/578; emptycart 578/578 | 81.0% / 81.0% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2_r2` | rg_only | off | FLAGGED | 230 | getproduct 577/577; postcheckout 577/577; getcart 577/577; postcart 577/577; emptycart 577/577 | 81.3% / 81.3% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3` | rg_only | off | FLAGGED | 226 | getproduct 1/570; postcheckout 1/570; getcart 1/570; postcart 1/570; emptycart 1/570 | 0.0% / 78.9% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3_r2` | rg_only | off | FLAGGED | 230 | getproduct 1/579; postcheckout 1/579; getcart 1/579; postcart 1/579; emptycart 1/579 | 0.0% / 80.2% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4` | rg_only | off | FLAGGED | 228 | getproduct 2/580; postcheckout 2/580; getcart 2/580; postcart 2/580; emptycart 2/580 | 0.0% / 80.6% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4_r2` | rg_only | off | FLAGGED | 230 | getproduct 1/577; postcheckout 1/577; getcart 1/577; postcart 1/577; emptycart 1/577 | 0.0% / 80.1% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run5` | rg_only | off | FLAGGED | 226 | getproduct 570/570; postcheckout 570/570; getcart 570/570; postcart 570/570; emptycart 570/570 | 79.8% / 79.8% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run5_r2` | rg_only | off | FLAGGED | 228 | getproduct 575/575; postcheckout 575/575; getcart 575/575; postcart 575/575; emptycart 575/575 | 80.0% / 80.0% |
| `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run6` | rg_only | off | FLAGGED | 228 | getproduct 575/575; postcheckout 575/575; getcart 575/575; postcart 575/575; emptycart 575/575 | 80.4% / 80.4% |
| `S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run1_r2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run2_r2` | both | on | FLAGGED | 192 | getproduct 5/483; postcheckout 5/483; getcart 5/483; postcart 5/483; emptycart 5/483 | 0.0% / 67.7% |
| `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3` | both | on | FLAGGED | 226 | getproduct 5/570; postcheckout 5/570; getcart 5/570; postcart 5/570; emptycart 5/570 | 0.0% / 78.5% |
| `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3_r2` | both | on | FLAGGED | 224 | getproduct 5/564; postcheckout 5/564; getcart 5/564; postcart 5/564; emptycart 5/564 | 0.0% / 78.1% |
| `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run4` | both | on | FLAGGED | 226 | getproduct 5/568; postcheckout 5/568; getcart 5/568; postcart 5/568; emptycart 5/568 | 0.0% / 78.7% |
| `S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run1_r2` | both | on | FLAGGED | 200 | getproduct 505/505; postcheckout 505/505; getcart 505/505; postcart 505/505; emptycart 505/505 | 70.3% / 70.3% |
| `S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run2_r2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1` | rg_only | off | FLAGGED | 228 | getproduct 575/575; postcheckout 575/575; getcart 575/575; postcart 575/575; emptycart 575/575 | 80.9% / 80.9% |
| `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1_r2` | rg_only | off | FLAGGED | 228 | getproduct 575/575; postcheckout 575/575; getcart 575/575; postcart 575/575; emptycart 575/575 | 80.4% / 80.4% |
| `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2` | rg_only | off | FLAGGED | 228 | getproduct 575/575; postcheckout 575/575; getcart 575/575; postcart 575/575; emptycart 575/575 | 81.0% / 81.0% |
| `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2_r2` | rg_only | off | FLAGGED | 230 | getproduct 578/578; postcheckout 578/578; getcart 578/578; postcart 578/578; emptycart 578/578 | 81.4% / 81.4% |
| `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3` | rg_only | off | FLAGGED | 228 | getproduct 575/575; postcheckout 575/575; getcart 575/575; postcart 575/575; emptycart 575/575 | 79.8% / 79.8% |
| `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3_r2` | rg_only | off | FLAGGED | 228 | getproduct 575/575; postcheckout 575/575; getcart 575/575; postcart 575/575; emptycart 575/575 | 79.3% / 79.3% |
| `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4` | rg_only | off | FLAGGED | 230 | getproduct 578/578; postcheckout 578/578; getcart 578/578; postcart 578/578; emptycart 578/578 | 80.1% / 80.1% |
| `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4_r2` | rg_only | off | FLAGGED | 230 | getproduct 580/580; postcheckout 580/580; getcart 580/580; postcart 580/580; emptycart 580/580 | 80.3% / 80.3% |
| `S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run2` | rg_only | off | FLAGGED | 144 | getproduct 365/365; postcheckout 365/365; getcart 365/365; postcart 365/365; emptycart 365/365 | 49.2% / 49.2% |
| `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1` | tf_only | on | FLAGGED | 228 | getproduct 4/575; postcheckout 4/575; getcart 4/575; postcart 4/575; emptycart 4/575 | 0.0% / 83.6% |
| `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1_r2` | tf_only | on | FLAGGED | 200 | getproduct 504/504; postcheckout 504/504; getcart 504/504; postcart 504/504; emptycart 504/504 | 73.3% / 73.3% |
| `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2` | tf_only | on | FLAGGED | 226 | getproduct 5/567; postcheckout 5/567; getcart 5/567; postcart 5/567; emptycart 5/567 | 0.0% / 82.5% |
| `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2_r2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3` | tf_only | on | FLAGGED | 228 | getproduct 5/575; postcheckout 5/575; getcart 5/575; postcart 5/575; emptycart 5/575 | 0.0% / 82.7% |
| `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3_r2` | tf_only | on | FLAGGED | 224 | getproduct 5/565; postcheckout 5/565; getcart 5/565; postcart 5/565; emptycart 5/565 | 0.0% / 80.1% |
| `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run4` | tf_only | on | FLAGGED | 224 | getproduct 5/565; postcheckout 5/565; getcart 5/565; postcart 5/565; emptycart 5/565 | 0.0% / 81.2% |
| `S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run1` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run1_r2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run2_r2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_burst/both/final_4b_both_burst_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_burst/both/final_4b_both_burst_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_normal/both/final_4b_both_normal_run1` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_normal/both/final_4b_both_normal_run2` | both | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run2` | rg_only | off | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_normal/tf_only/final_4b_tf_only_run1` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |
| `S4B_topology_position_normal/tf_only/final_4b_tf_only_run2` | tf_only | on | CLEAN | 0 | getproduct 5/5; postcheckout 5/5; getcart 5/5; postcart 5/5; emptycart 5/5 | 0.0% / 0.0% |

## 3. Flagged runs

### `S2_sustained_overload_burst/both/final_s2_both_burst_run1`

`S2_sustained_overload_burst/both/final_s2_both_burst_run1` is FLAGGED with TopFull on. The collector log has 196 `fetch failed` warnings (thresholds fetch failed ×98, stats fetch failed ×98), from 2026-10-14T12:58:40Z → 2026-10-14T13:06:45Z. Reason text: 194× timed out; 2× <urlopen error timed out>. The CSV covers 715 s (2026-10-14T12:54:54Z → 2026-10-14T13:06:49Z). Threshold reads went stale on all five APIs for 494 s (69.1% of the span). Admitted-rate reads went stale on all five APIs for 494 s (69.1% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 716 | 55 | 661 | 45 | 671 | 494 | 494 | 69.1% | 69.1% | caps 109.636×1, 112.2×1, 199.4×1, 201×1, 217.6×1, 234×2, 302.5×1; no-cap (10000) ×39; empty read (0) ×8 | min 0 / median 42 / mean 110.2 / max 275 (n=45 fresh) |
| postcheckout | 716 | 55 | 661 | 45 | 671 | 494 | 494 | 69.1% | 69.1% | caps min 11.9 / median 47.2 / max 83.6148 / 21 distinct / 21 fresh reads; no-cap (10000) ×28; empty read (0) ×6 | min 0 / median 14 / mean 36.0 / max 90 (n=45 fresh) |
| getcart | 716 | 55 | 661 | 45 | 671 | 494 | 494 | 69.1% | 69.1% | caps 34.9×1, 74×1, 74.4303×1, 76×1, 82×1, 101.984×1, 102×1, 110×1; no-cap (10000) ×41; empty read (0) ×6 | min 0 / median 17 / mean 40.4 / max 100 (n=45 fresh) |
| postcart | 716 | 55 | 661 | 45 | 671 | 494 | 494 | 69.1% | 69.1% | no-cap (10000) ×45; empty read (0) ×10 | min 0 / median 15 / mean 38.3 / max 90 (n=45 fresh) |
| emptycart | 716 | 55 | 661 | 45 | 671 | 494 | 494 | 69.1% | 69.1% | no-cap (10000) ×45; empty read (0) ×10 | min 0 / median 1 / mean 2.2 / max 5 (n=45 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 10 live-cap changes (see fresh-threshold counts)
- postcheckout: 24 live-cap changes (see fresh-threshold counts)
- getcart: 11 live-cap changes (see fresh-threshold counts)
- postcart: no cap 12:54:55–12:58:35
- emptycart: no cap 12:54:55–12:58:35

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 716 | 1150 | 0.8 | 0.261 | 0.35 | 0 | 0.0% |
| checkoutservice | 716 | 800 | 0.8 | 0.715 | 1.012 | 443 | 61.9% |
| recommendationservice | 716 | 1150 | 0.8 | 0.594 | 0.981 | 75 | 10.5% |
| paymentservice | 716 | 155 | 0.8 | 0.236 | 0.516 | 0 | 0.0% |
| emailservice | 716 | 120 | 0.8 | 0.591 | 1.05 | 119 | 16.6% |
| productcatalogservice | 716 | 800 | 0.95 | 0.418 | 0.609 | 0 | 0.0% |
| cartservice | 716 | 800 | 0.95 | 0.384 | 0.576 | 0 | 0.0% |
| currencyservice | 716 | 770 | 0.8 | 0.42 | 0.666 | 0 | 0.0% |
| shippingservice | 716 | 770 | 0.8 | 0.104 | 0.174 | 0 | 0.0% |
| adservice | 716 | 1150 | 0.8 | 0.095 | 0.149 | 0 | 0.0% |
| redis-cart | 716 | 540 | 0.8 | 0.072 | 0.365 | 0 | 0.0% |

### `S2_sustained_overload_burst/both/final_s2_both_burst_run2`

`S2_sustained_overload_burst/both/final_s2_both_burst_run2` is FLAGGED with TopFull on. The collector log has 224 `fetch failed` warnings (thresholds fetch failed ×112, stats fetch failed ×112), from 2026-10-14T13:15:30Z → 2026-10-14T13:24:45Z. Reason text: 224× timed out. The CSV covers 715 s (2026-10-14T13:12:56Z → 2026-10-14T13:24:51Z). Threshold reads went stale on all five APIs for 565 s (79.0% of the span). Admitted-rate reads went stale on all five APIs for 565 s (79.0% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 716 | 32 | 684 | 31 | 685 | 565 | 565 | 79.0% | 79.0% | caps 272×1; no-cap (10000) ×30; empty read (0) ×1 | min 0 / median 0 / mean 47.8 / max 248 (n=31 fresh) |
| postcheckout | 716 | 32 | 684 | 31 | 685 | 565 | 565 | 79.0% | 79.0% | caps 41.6×1, 52.8×1, 61×1, 71.4×1; no-cap (10000) ×28 | min 0 / median 0 / mean 15.4 / max 81 (n=31 fresh) |
| getcart | 716 | 32 | 684 | 31 | 685 | 565 | 565 | 79.0% | 79.0% | caps 100×1; no-cap (10000) ×30; empty read (0) ×1 | min 0 / median 0 / mean 18.2 / max 93 (n=31 fresh) |
| postcart | 716 | 32 | 684 | 31 | 685 | 565 | 565 | 79.0% | 79.0% | no-cap (10000) ×31; empty read (0) ×1 | min 0 / median 0 / mean 16.0 / max 82 (n=31 fresh) |
| emptycart | 716 | 32 | 684 | 31 | 685 | 565 | 565 | 79.0% | 79.0% | no-cap (10000) ×31; empty read (0) ×1 | min 0 / median 0 / mean 1.1 / max 5 (n=31 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 13:13:00–13:15:25; 272 at 13:24:50
- postcheckout: 7 live-cap changes (see fresh-threshold counts)
- getcart: no cap 13:13:00–13:15:25; 100 at 13:24:50
- postcart: no cap 13:13:00–13:24:50
- emptycart: no cap 13:13:00–13:24:50

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 716 | 1150 | 0.8 | 0.266 | 0.35 | 0 | 0.0% |
| checkoutservice | 716 | 800 | 0.8 | 0.667 | 1.006 | 377 | 52.7% |
| recommendationservice | 716 | 1150 | 0.8 | 0.557 | 0.955 | 65 | 9.1% |
| paymentservice | 716 | 155 | 0.8 | 0.208 | 0.497 | 0 | 0.0% |
| emailservice | 716 | 120 | 0.8 | 0.501 | 0.967 | 20 | 2.8% |
| productcatalogservice | 716 | 800 | 0.95 | 0.423 | 0.583 | 0 | 0.0% |
| cartservice | 716 | 800 | 0.95 | 0.412 | 0.7 | 0 | 0.0% |
| currencyservice | 716 | 770 | 0.8 | 0.419 | 0.612 | 0 | 0.0% |
| shippingservice | 716 | 770 | 0.8 | 0.107 | 0.175 | 0 | 0.0% |
| adservice | 716 | 1150 | 0.8 | 0.111 | 0.211 | 0 | 0.0% |
| redis-cart | 716 | 540 | 0.8 | 0.071 | 0.304 | 0 | 0.0% |

### `S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run2`

`S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run2` is FLAGGED with TopFull off. The collector log has 16 `fetch failed` warnings (thresholds fetch failed ×8, stats fetch failed ×8), from 2026-10-14T12:48:05Z → 2026-10-14T12:48:40Z. Reason text: 16× timed out. The CSV covers 713 s (2026-10-14T12:36:53Z → 2026-10-14T12:48:46Z). Threshold reads went stale on all five APIs for 45 s (6.3% of the span). Admitted-rate reads went stale on all five APIs for 45 s (6.3% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 714 | 135 | 579 | 135 | 579 | 45 | 45 | 6.3% | 6.3% | no-cap (10000) ×135 | min 0 / median 275 / mean 219.0 / max 275 (n=135 fresh) |
| postcheckout | 714 | 135 | 579 | 135 | 579 | 45 | 45 | 6.3% | 6.3% | no-cap (10000) ×135 | min 0 / median 89 / mean 71.3 / max 90 (n=135 fresh) |
| getcart | 714 | 135 | 579 | 135 | 579 | 45 | 45 | 6.3% | 6.3% | no-cap (10000) ×135 | min 0 / median 100 / mean 80.1 / max 101 (n=135 fresh) |
| postcart | 714 | 135 | 579 | 135 | 579 | 45 | 45 | 6.3% | 6.3% | no-cap (10000) ×135 | min 0 / median 90 / mean 73.1 / max 90 (n=135 fresh) |
| emptycart | 714 | 135 | 579 | 135 | 579 | 45 | 45 | 6.3% | 6.3% | no-cap (10000) ×135 | min 0 / median 5 / mean 4.1 / max 5 (n=135 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 12:36:55–12:48:45
- postcheckout: no cap 12:36:55–12:48:45
- getcart: no cap 12:36:55–12:48:45
- postcart: no cap 12:36:55–12:48:45
- emptycart: no cap 12:36:55–12:48:45

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 714 | 1150 | 0.8 | 0.266 | 0.346 | 0 | 0.0% |
| checkoutservice | 714 | 800 | 0.8 | 0.793 | 1.036 | 556 | 77.9% |
| recommendationservice | 714 | 1150 | 0.8 | 0.587 | 0.958 | 36 | 5.0% |
| paymentservice | 714 | 155 | 0.8 | 0.272 | 0.581 | 0 | 0.0% |
| emailservice | 714 | 120 | 0.8 | 0.677 | 1 | 311 | 43.6% |
| productcatalogservice | 714 | 800 | 0.95 | 0.416 | 0.557 | 0 | 0.0% |
| cartservice | 714 | 800 | 0.95 | 0.402 | 0.64 | 0 | 0.0% |
| currencyservice | 714 | 770 | 0.8 | 0.429 | 0.605 | 0 | 0.0% |
| shippingservice | 714 | 770 | 0.8 | 0.111 | 0.179 | 0 | 0.0% |
| adservice | 714 | 1150 | 0.8 | 0.095 | 0.148 | 0 | 0.0% |
| redis-cart | 714 | 540 | 0.8 | 0.071 | 0.331 | 0 | 0.0% |

### `S2_sustained_overload_burst/rg_only/s2_burst20_rgtf0`

`S2_sustained_overload_burst/rg_only/s2_burst20_rgtf0` is FLAGGED with TopFull off. The collector log has 220 `fetch failed` warnings (thresholds fetch failed ×110, stats fetch failed ×110), from 2026-10-12T14:50:10Z → 2026-10-12T14:59:15Z. Reason text: 220× timed out. The CSV covers 713 s (2026-10-12T14:47:28Z → 2026-10-12T14:59:21Z). Threshold reads went stale on all five APIs for 555 s (77.8% of the span). Admitted-rate reads went stale on all five APIs for 555 s (77.8% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 714 | 33 | 681 | 33 | 681 | 555 | 555 | 77.8% | 77.8% | no-cap (10000) ×33 | min 0 / median 0 / mean 61.2 / max 275 (n=33 fresh) |
| postcheckout | 714 | 33 | 681 | 33 | 681 | 555 | 555 | 77.8% | 77.8% | no-cap (10000) ×33 | min 0 / median 0 / mean 18.7 / max 86 (n=33 fresh) |
| getcart | 714 | 33 | 681 | 33 | 681 | 555 | 555 | 77.8% | 77.8% | no-cap (10000) ×33 | min 0 / median 0 / mean 22.8 / max 100 (n=33 fresh) |
| postcart | 714 | 33 | 681 | 33 | 681 | 555 | 555 | 77.8% | 77.8% | no-cap (10000) ×33 | min 0 / median 0 / mean 20.5 / max 90 (n=33 fresh) |
| emptycart | 714 | 33 | 681 | 33 | 681 | 555 | 555 | 77.8% | 77.8% | no-cap (10000) ×33 | min 0 / median 0 / mean 1.3 / max 5 (n=33 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 14:47:30–14:59:20
- postcheckout: no cap 14:47:30–14:59:20
- getcart: no cap 14:47:30–14:59:20
- postcart: no cap 14:47:30–14:59:20
- emptycart: no cap 14:47:30–14:59:20

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 714 | 1150 | 0.8 | 0.286 | 0.367 | 0 | 0.0% |
| checkoutservice | 714 | 800 | 0.8 | 0.822 | 1.054 | 581 | 81.4% |
| recommendationservice | 714 | 1150 | 0.8 | 0.572 | 1.009 | 9 | 1.3% |
| paymentservice | 714 | 155 | 0.8 | 0.35 | 0.697 | 0 | 0.0% |
| emailservice | 714 | 120 | 0.8 | 0.718 | 1.075 | 498 | 69.7% |
| productcatalogservice | 714 | 800 | 0.95 | 0.525 | 0.682 | 0 | 0.0% |
| cartservice | 714 | 800 | 0.95 | 0.403 | 0.686 | 0 | 0.0% |
| currencyservice | 714 | 770 | 0.8 | 0.449 | 0.744 | 0 | 0.0% |
| shippingservice | 714 | 770 | 0.8 | 0.125 | 0.182 | 0 | 0.0% |
| adservice | 714 | 1150 | 0.8 | 0.116 | 0.163 | 0 | 0.0% |
| redis-cart | 714 | 540 | 0.8 | 0.065 | 0.109 | 0 | 0.0% |

### `S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep1`

`S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep1` is FLAGGED with TopFull on. The collector log has 204 `fetch failed` warnings (thresholds fetch failed ×102, stats fetch failed ×102), from 2026-10-12T01:10:05Z → 2026-10-12T01:18:30Z. Reason text: 202× timed out; 2× <urlopen error timed out>. The CSV covers 715 s (2026-10-12T01:06:38Z → 2026-10-12T01:18:33Z). Threshold reads went stale on all five APIs for 513 s (71.7% of the span). Admitted-rate reads went stale on all five APIs for 513 s (71.7% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 716 | 47 | 669 | 41 | 675 | 513 | 513 | 71.7% | 71.7% | caps 212×1, 216.3×1, 225.6×1, 298.7×1; no-cap (10000) ×38; empty read (0) ×5 | min 0 / median 0 / mean 98.0 / max 275 (n=41 fresh) |
| postcheckout | 716 | 47 | 669 | 41 | 675 | 513 | 513 | 71.7% | 71.7% | caps min 10 / median 37.105 / max 79 / 20 distinct / 20 fresh reads; no-cap (10000) ×24; empty read (0) ×3 | min 0 / median 0 / mean 31.8 / max 90 (n=41 fresh) |
| getcart | 716 | 47 | 669 | 41 | 675 | 513 | 513 | 71.7% | 71.7% | caps 78.967×1, 79×2, 83.3×1, 92.6×1, 110×1; no-cap (10000) ×37; empty read (0) ×4 | min 0 / median 0 / mean 35.9 / max 100 (n=41 fresh) |
| postcart | 716 | 47 | 669 | 41 | 675 | 513 | 513 | 71.7% | 71.7% | no-cap (10000) ×41; empty read (0) ×6 | min 0 / median 0 / mean 33.7 / max 90 (n=41 fresh) |
| emptycart | 716 | 47 | 669 | 41 | 675 | 513 | 513 | 71.7% | 71.7% | no-cap (10000) ×41; empty read (0) ×6 | min 0 / median 0 / mean 2.0 / max 5 (n=41 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 01:06:40–01:09:30; 225.6 at 01:09:35; 216.3 at 01:09:40; 212 at 01:09:45; 298.7 at 01:09:50; no cap 01:09:53–01:10:00
- postcheckout: 21 live-cap changes (see fresh-threshold counts)
- getcart: 8 live-cap changes (see fresh-threshold counts)
- postcart: no cap 01:06:40–01:10:00
- emptycart: no cap 01:06:40–01:10:00

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 716 | 1150 | 0.8 | 0.274 | 0.366 | 0 | 0.0% |
| checkoutservice | 716 | 800 | 0.8 | 0.697 | 1.024 | 400 | 55.9% |
| recommendationservice | 716 | 1150 | 0.8 | 0.658 | 1.012 | 201 | 28.1% |
| paymentservice | 716 | 155 | 0.8 | 0.261 | 0.6 | 0 | 0.0% |
| emailservice | 716 | 120 | 0.8 | 0.614 | 1.033 | 289 | 40.4% |
| productcatalogservice | 716 | 800 | 0.95 | 0.496 | 0.691 | 0 | 0.0% |
| cartservice | 716 | 800 | 0.95 | 0.411 | 0.657 | 0 | 0.0% |
| currencyservice | 716 | 770 | 0.8 | 0.454 | 0.649 | 0 | 0.0% |
| shippingservice | 716 | 770 | 0.8 | 0.109 | 0.199 | 0 | 0.0% |
| adservice | 716 | 1150 | 0.8 | 0.113 | 0.276 | 0 | 0.0% |
| redis-cart | 716 | 540 | 0.8 | 0.074 | 0.35 | 0 | 0.0% |

### `S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep2`

`S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep2` is FLAGGED with TopFull on. The collector log has 218 `fetch failed` warnings (thresholds fetch failed ×109, stats fetch failed ×109), from 2026-10-12T01:27:15Z → 2026-10-12T01:36:15Z. Reason text: 215× timed out; 3× <urlopen error timed out>. The CSV covers 716 s (2026-10-12T01:24:24Z → 2026-10-12T01:36:20Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 550 s (76.8% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 717 | 582 | 135 | 35 | 682 | 5 | 550 | 0.0% | 76.8% | caps 275×1; no-cap (10000) ×34; empty read (0) ×547 | min 0 / median 0 / mean 65.8 / max 275 (n=35 fresh) |
| postcheckout | 717 | 582 | 135 | 35 | 682 | 5 | 550 | 0.0% | 76.8% | caps min 10 / median 46.7526 / max 66 / 11 distinct / 554 fresh reads; no-cap (10000) ×28 | min 0 / median 0 / mean 20.0 / max 90 (n=35 fresh) |
| getcart | 717 | 582 | 135 | 35 | 682 | 5 | 550 | 0.0% | 76.8% | caps 100×1; no-cap (10000) ×34; empty read (0) ×547 | min 0 / median 0 / mean 24.4 / max 100 (n=35 fresh) |
| postcart | 717 | 582 | 135 | 35 | 682 | 5 | 550 | 0.0% | 76.8% | no-cap (10000) ×35; empty read (0) ×547 | min 0 / median 0 / mean 21.8 / max 90 (n=35 fresh) |
| emptycart | 717 | 582 | 135 | 35 | 682 | 5 | 550 | 0.0% | 76.8% | no-cap (10000) ×35; empty read (0) ×547 | min 0 / median 0 / mean 1.3 / max 5 (n=35 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 01:24:25–01:27:10; 275 at 01:36:20
- postcheckout: 13 live-cap changes (see fresh-threshold counts)
- getcart: no cap 01:24:25–01:27:10; 100 at 01:36:20
- postcart: no cap 01:24:25–01:36:20
- emptycart: no cap 01:24:25–01:36:20

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 717 | 1150 | 0.8 | 0.283 | 0.378 | 0 | 0.0% |
| checkoutservice | 717 | 800 | 0.8 | 0.723 | 1.016 | 484 | 67.5% |
| recommendationservice | 717 | 1150 | 0.8 | 0.667 | 1 | 318 | 44.4% |
| paymentservice | 717 | 155 | 0.8 | 0.265 | 0.581 | 0 | 0.0% |
| emailservice | 717 | 120 | 0.8 | 0.64 | 1.033 | 229 | 31.9% |
| productcatalogservice | 717 | 800 | 0.95 | 0.495 | 0.703 | 0 | 0.0% |
| cartservice | 717 | 800 | 0.95 | 0.423 | 0.593 | 0 | 0.0% |
| currencyservice | 717 | 770 | 0.8 | 0.478 | 0.664 | 0 | 0.0% |
| shippingservice | 717 | 770 | 0.8 | 0.11 | 0.182 | 0 | 0.0% |
| adservice | 717 | 1150 | 0.8 | 0.106 | 0.196 | 0 | 0.0% |
| redis-cart | 717 | 540 | 0.8 | 0.078 | 0.287 | 0 | 0.0% |

### `S2_sustained_overload_normal/both/study7_s2_normal_rgtf1_rep1`

`S2_sustained_overload_normal/both/study7_s2_normal_rgtf1_rep1` is FLAGGED with TopFull on. The collector log has 40 `fetch failed` warnings (thresholds fetch failed ×20, stats fetch failed ×20), from 2026-10-12T08:40:40Z → 2026-10-12T08:42:15Z. Reason text: 40× timed out. The CSV covers 716 s (2026-10-12T08:30:24Z → 2026-10-12T08:42:20Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 105 s (14.7% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 717 | 351 | 366 | 124 | 593 | 5 | 105 | 0.0% | 14.7% | caps 238×1; no-cap (10000) ×123; empty read (0) ×227 | min 0 / median 275 / mean 215.8 / max 275 (n=124 fresh) |
| postcheckout | 717 | 351 | 366 | 124 | 593 | 5 | 105 | 0.0% | 14.7% | caps min 10 / median 47.1 / max 99 / 103 distinct / 321 fresh reads; no-cap (10000) ×30 | min 0 / median 79.5 / mean 62.5 / max 90 (n=124 fresh) |
| getcart | 717 | 351 | 366 | 124 | 593 | 5 | 105 | 0.0% | 14.7% | caps 84×1; no-cap (10000) ×123; empty read (0) ×227 | min 0 / median 100 / mean 78.8 / max 114 (n=124 fresh) |
| postcart | 717 | 351 | 366 | 124 | 593 | 5 | 105 | 0.0% | 14.7% | no-cap (10000) ×124; empty read (0) ×227 | min 0 / median 90 / mean 70.7 / max 90 (n=124 fresh) |
| emptycart | 717 | 351 | 366 | 124 | 593 | 5 | 105 | 0.0% | 14.7% | no-cap (10000) ×124; empty read (0) ×227 | min 0 / median 5 / mean 4.0 / max 5 (n=124 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 08:30:25–08:40:35; 238 at 08:42:20
- postcheckout: 175 live-cap changes (see fresh-threshold counts)
- getcart: no cap 08:30:25–08:40:35; 84 at 08:42:20
- postcart: no cap 08:30:25–08:42:20
- emptycart: no cap 08:30:25–08:42:20

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 717 | 1150 | 0.8 | 0.276 | 0.369 | 0 | 0.0% |
| checkoutservice | 717 | 800 | 0.8 | 0.68 | 1.042 | 387 | 54.0% |
| recommendationservice | 717 | 1150 | 0.8 | 0.543 | 0.955 | 22 | 3.1% |
| paymentservice | 717 | 155 | 0.8 | 0.303 | 0.948 | 4 | 0.6% |
| emailservice | 717 | 120 | 0.8 | 0.444 | 1.025 | 153 | 21.3% |
| productcatalogservice | 717 | 800 | 0.95 | 0.538 | 0.728 | 0 | 0.0% |
| cartservice | 717 | 800 | 0.95 | 0.375 | 0.547 | 0 | 0.0% |
| currencyservice | 717 | 770 | 0.8 | 0.431 | 0.631 | 0 | 0.0% |
| shippingservice | 717 | 770 | 0.8 | 0.105 | 0.195 | 0 | 0.0% |
| adservice | 717 | 1150 | 0.8 | 0.137 | 0.923 | 1 | 0.1% |
| redis-cart | 717 | 540 | 0.8 | 0.063 | 0.085 | 0 | 0.0% |

### `S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep1`

`S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep1` is FLAGGED with TopFull off. The collector log has 224 `fetch failed` warnings (thresholds fetch failed ×112, stats fetch failed ×112), from 2026-10-12T00:33:30Z → 2026-10-12T00:42:45Z. Reason text: 220× timed out; 4× <urlopen error timed out>. The CSV covers 714 s (2026-10-12T00:30:56Z → 2026-10-12T00:42:50Z). Threshold reads went stale on all five APIs for 565 s (79.1% of the span). Admitted-rate reads went stale on all five APIs for 565 s (79.1% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 715 | 31 | 684 | 31 | 684 | 565 | 565 | 79.1% | 79.1% | no-cap (10000) ×31 | min 0 / median 0 / mean 47.5 / max 258 (n=31 fresh) |
| postcheckout | 715 | 31 | 684 | 31 | 684 | 565 | 565 | 79.1% | 79.1% | no-cap (10000) ×31 | min 0 / median 0 / mean 12.4 / max 56 (n=31 fresh) |
| getcart | 715 | 31 | 684 | 31 | 684 | 565 | 565 | 79.1% | 79.1% | no-cap (10000) ×31 | min 0 / median 0 / mean 17.7 / max 95 (n=31 fresh) |
| postcart | 715 | 31 | 684 | 31 | 684 | 565 | 565 | 79.1% | 79.1% | no-cap (10000) ×31 | min 0 / median 0 / mean 16.2 / max 86 (n=31 fresh) |
| emptycart | 715 | 31 | 684 | 31 | 684 | 565 | 565 | 79.1% | 79.1% | no-cap (10000) ×31 | min 0 / median 0 / mean 1.0 / max 5 (n=31 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 00:31:00–00:42:50
- postcheckout: no cap 00:31:00–00:42:50
- getcart: no cap 00:31:00–00:42:50
- postcart: no cap 00:31:00–00:42:50
- emptycart: no cap 00:31:00–00:42:50

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 715 | 1150 | 0.8 | 0.282 | 0.362 | 0 | 0.0% |
| checkoutservice | 715 | 800 | 0.8 | 0.663 | 1.055 | 330 | 46.2% |
| recommendationservice | 715 | 1150 | 0.8 | 0.703 | 1.02 | 518 | 72.4% |
| paymentservice | 715 | 155 | 0.8 | 0.248 | 0.6 | 0 | 0.0% |
| emailservice | 715 | 120 | 0.8 | 0.583 | 1.083 | 159 | 22.2% |
| productcatalogservice | 715 | 800 | 0.95 | 0.489 | 0.66 | 0 | 0.0% |
| cartservice | 715 | 800 | 0.95 | 0.439 | 0.64 | 0 | 0.0% |
| currencyservice | 715 | 770 | 0.8 | 0.477 | 0.71 | 0 | 0.0% |
| shippingservice | 715 | 770 | 0.8 | 0.083 | 0.168 | 0 | 0.0% |
| adservice | 715 | 1150 | 0.8 | 0.101 | 0.417 | 0 | 0.0% |
| redis-cart | 715 | 540 | 0.8 | 0.08 | 0.306 | 0 | 0.0% |

### `S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep2`

`S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep2` is FLAGGED with TopFull off. The collector log has 216 `fetch failed` warnings (thresholds fetch failed ×108, stats fetch failed ×108), from 2026-10-12T00:51:50Z → 2026-10-12T01:00:45Z. Reason text: 214× timed out; 2× <urlopen error timed out>. The CSV covers 714 s (2026-10-12T00:48:57Z → 2026-10-12T01:00:51Z). Threshold reads went stale on all five APIs for 545 s (76.3% of the span). Admitted-rate reads went stale on all five APIs for 545 s (76.3% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 715 | 35 | 680 | 35 | 680 | 545 | 545 | 76.3% | 76.3% | no-cap (10000) ×35 | min 0 / median 0 / mean 73.5 / max 275 (n=35 fresh) |
| postcheckout | 715 | 35 | 680 | 35 | 680 | 545 | 545 | 76.3% | 76.3% | no-cap (10000) ×35 | min 0 / median 0 / mean 18.7 / max 84 (n=35 fresh) |
| getcart | 715 | 35 | 680 | 35 | 680 | 545 | 545 | 76.3% | 76.3% | no-cap (10000) ×35 | min 0 / median 0 / mean 27.3 / max 100 (n=35 fresh) |
| postcart | 715 | 35 | 680 | 35 | 680 | 545 | 545 | 76.3% | 76.3% | no-cap (10000) ×35 | min 0 / median 0 / mean 24.7 / max 90 (n=35 fresh) |
| emptycart | 715 | 35 | 680 | 35 | 680 | 545 | 545 | 76.3% | 76.3% | no-cap (10000) ×35 | min 0 / median 0 / mean 1.5 / max 5 (n=35 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 00:49:00–01:00:50
- postcheckout: no cap 00:49:00–01:00:50
- getcart: no cap 00:49:00–01:00:50
- postcart: no cap 00:49:00–01:00:50
- emptycart: no cap 00:49:00–01:00:50

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 715 | 1150 | 0.8 | 0.282 | 0.36 | 0 | 0.0% |
| checkoutservice | 715 | 800 | 0.8 | 0.754 | 1.064 | 532 | 74.4% |
| recommendationservice | 715 | 1150 | 0.8 | 0.673 | 1 | 378 | 52.9% |
| paymentservice | 715 | 155 | 0.8 | 0.282 | 0.781 | 0 | 0.0% |
| emailservice | 715 | 120 | 0.8 | 0.644 | 1.075 | 272 | 38.0% |
| productcatalogservice | 715 | 800 | 0.95 | 0.494 | 0.686 | 0 | 0.0% |
| cartservice | 715 | 800 | 0.95 | 0.431 | 0.613 | 0 | 0.0% |
| currencyservice | 715 | 770 | 0.8 | 0.477 | 0.674 | 0 | 0.0% |
| shippingservice | 715 | 770 | 0.8 | 0.106 | 0.177 | 0 | 0.0% |
| adservice | 715 | 1150 | 0.8 | 0.101 | 0.174 | 0 | 0.0% |
| redis-cart | 715 | 540 | 0.8 | 0.078 | 0.311 | 0 | 0.0% |

### `S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2`

`S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2` is FLAGGED with TopFull on. The collector log has 110 `fetch failed` warnings (thresholds fetch failed ×55, stats fetch failed ×55), from 2026-10-14T12:08:35Z → 2026-10-14T12:13:05Z. Reason text: 110× timed out. The CSV covers 691 s (2026-10-14T12:01:39Z → 2026-10-14T12:13:10Z). Threshold reads went stale on all five APIs for 280 s (40.5% of the span). Admitted-rate reads went stale on all five APIs for 280 s (40.5% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 692 | 112 | 580 | 84 | 608 | 280 | 280 | 40.5% | 40.5% | caps min 142 / median 212 / max 301.4 / 22 distinct / 25 fresh reads; no-cap (10000) ×64; empty read (0) ×23 | min 0 / median 240 / mean 190.9 / max 275 (n=84 fresh) |
| postcheckout | 692 | 112 | 580 | 84 | 608 | 280 | 280 | 40.5% | 40.5% | caps min 13.1 / median 44.55 / max 98.3 / 67 distinct / 74 fresh reads; no-cap (10000) ×31; empty read (0) ×7 | min 0 / median 76 / mean 61.5 / max 90 (n=84 fresh) |
| getcart | 692 | 112 | 580 | 84 | 608 | 280 | 280 | 40.5% | 40.5% | caps min 48 / median 75.1 / max 110 / 20 distinct / 24 fresh reads; no-cap (10000) ×63; empty read (0) ×25 | min 0 / median 87.5 / mean 69.7 / max 100 (n=84 fresh) |
| postcart | 692 | 112 | 580 | 84 | 608 | 280 | 280 | 40.5% | 40.5% | no-cap (10000) ×84; empty read (0) ×28 | min 0 / median 90 / mean 67.0 / max 90 (n=84 fresh) |
| emptycart | 692 | 112 | 580 | 84 | 608 | 280 | 280 | 40.5% | 40.5% | no-cap (10000) ×84; empty read (0) ×28 | min 0 / median 5 / mean 3.8 / max 5 (n=84 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 31 live-cap changes (see fresh-threshold counts)
- postcheckout: 80 live-cap changes (see fresh-threshold counts)
- getcart: 30 live-cap changes (see fresh-threshold counts)
- postcart: no cap 12:01:40–12:13:10
- emptycart: no cap 12:01:40–12:13:10

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 692 | 1150 | 0.8 | 0.255 | 0.349 | 0 | 0.0% |
| checkoutservice | 692 | 800 | 0.8 | 0.719 | 1.038 | 406 | 58.7% |
| recommendationservice | 692 | 1150 | 0.8 | 0.613 | 0.91 | 101 | 14.6% |
| paymentservice | 692 | 155 | 0.8 | 0.235 | 0.581 | 0 | 0.0% |
| emailservice | 692 | 120 | 0.8 | 0.579 | 0.992 | 93 | 13.4% |
| productcatalogservice | 692 | 800 | 0.95 | 0.432 | 0.613 | 0 | 0.0% |
| cartservice | 692 | 800 | 0.95 | 0.386 | 0.551 | 0 | 0.0% |
| currencyservice | 692 | 770 | 0.8 | 0.407 | 0.596 | 0 | 0.0% |
| shippingservice | 692 | 770 | 0.8 | 0.106 | 0.17 | 0 | 0.0% |
| adservice | 692 | 1150 | 0.8 | 0.099 | 0.16 | 0 | 0.0% |
| redis-cart | 692 | 540 | 0.8 | 0.072 | 0.396 | 0 | 0.0% |

### `S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1`

`S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1` is FLAGGED with TopFull off. The collector log has no `fetch failed` warning. The flag is a no-fresh stretch longer than 30 s. The CSV covers 875 s (2026-10-12T23:58:15Z → 2026-10-13T00:12:50Z). Threshold reads went stale on all five APIs for 55 s (6.3% of the span). Admitted-rate reads went stale on all five APIs for 55 s (6.3% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 822 | 166 | 656 | 166 | 656 | 55 | 55 | 6.3% | 6.3% | no-cap (10000) ×166 | min 0 / median 175 / mean 167.2 / max 175 (n=166 fresh) |
| postcheckout | 822 | 166 | 656 | 166 | 656 | 55 | 55 | 6.3% | 6.3% | no-cap (10000) ×166 | min 0 / median 30 / mean 27.2 / max 30 (n=166 fresh) |
| getcart | 822 | 166 | 656 | 166 | 656 | 55 | 55 | 6.3% | 6.3% | no-cap (10000) ×166 | min 0 / median 70 / mean 67.0 / max 70 (n=166 fresh) |
| postcart | 822 | 166 | 656 | 166 | 656 | 55 | 55 | 6.3% | 6.3% | no-cap (10000) ×166 | min 0 / median 90 / mean 86.1 / max 90 (n=166 fresh) |
| emptycart | 822 | 166 | 656 | 166 | 656 | 55 | 55 | 6.3% | 6.3% | no-cap (10000) ×166 | min 0 / median 5 / mean 4.8 / max 5 (n=166 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 23:58:15–00:12:50
- postcheckout: no cap 23:58:15–00:12:50
- getcart: no cap 23:58:15–00:12:50
- postcart: no cap 23:58:15–00:12:50
- emptycart: no cap 23:58:15–00:12:50

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 822 | 1150 | 0.8 | 0.33 | 0.375 | 0 | 0.0% |
| checkoutservice | 822 | 200 | 0.8 | 1 | 3.23 | 796 | 96.8% |
| recommendationservice | 822 | 1150 | 0.8 | 0.47 | 0.576 | 0 | 0.0% |
| paymentservice | 822 | 155 | 0.8 | 0.09 | 0.548 | 0 | 0.0% |
| emailservice | 822 | 120 | 0.8 | 0.097 | 0.758 | 0 | 0.0% |
| productcatalogservice | 822 | 800 | 0.95 | 0.689 | 0.776 | 0 | 0.0% |
| cartservice | 822 | 800 | 0.95 | 0.576 | 0.725 | 0 | 0.0% |
| currencyservice | 822 | 770 | 0.8 | 0.415 | 0.534 | 0 | 0.0% |
| shippingservice | 822 | 770 | 0.8 | 0.095 | 0.155 | 0 | 0.0% |
| adservice | 822 | 1150 | 0.8 | 0.115 | 0.235 | 0 | 0.0% |
| redis-cart | 822 | 540 | 0.8 | 0.08 | 0.131 | 0 | 0.0% |

### `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run1_r2`

`S4A_topology_position_burst/both/final_4a_constrained_both_burst_run1_r2` is FLAGGED with TopFull on. The collector log has 226 `fetch failed` warnings (thresholds fetch failed ×113, stats fetch failed ×113), from 2026-10-13T09:12:40Z → 2026-10-13T09:22:00Z. Reason text: 224× timed out; 2× <urlopen error timed out>. The CSV covers 713 s (2026-10-13T09:10:13Z → 2026-10-13T09:22:06Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 570 s (79.9% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 714 | 602 | 112 | 30 | 684 | 5 | 570 | 0.0% | 79.9% | caps 10×6; no-cap (10000) ×25; empty read (0) ×571 | min 0 / median 0 / mean 1.4 / max 7 (n=30 fresh) |
| postcheckout | 714 | 602 | 112 | 30 | 684 | 5 | 570 | 0.0% | 79.9% | caps 10×574; no-cap (10000) ×25; empty read (0) ×3 | min 0 / median 0 / mean 1.4 / max 7 (n=30 fresh) |
| getcart | 714 | 602 | 112 | 30 | 684 | 5 | 570 | 0.0% | 79.9% | caps 10×5; no-cap (10000) ×26; empty read (0) ×571 | min 0 / median 0 / mean 1.5 / max 7 (n=30 fresh) |
| postcart | 714 | 602 | 112 | 30 | 684 | 5 | 570 | 0.0% | 79.9% | caps 190.8×1, 214.8×1, 264.2×2, 270.6×1, 284.063×1, 284.1×1, 296.3×1; no-cap (10000) ×23; empty read (0) ×571 | min 0 / median 0 / mean 90.2 / max 478 (n=30 fresh) |
| emptycart | 714 | 602 | 112 | 30 | 684 | 5 | 570 | 0.0% | 79.9% | no-cap (10000) ×30; empty read (0) ×572 | min 0 / median 0 / mean 1.0 / max 5 (n=30 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 09:10:15–09:12:05; 10 09:12:08–09:12:10; no cap at 09:12:15; 10 at 09:12:20; no cap at 09:12:25; 10 09:12:30–09:22:05
- postcheckout: no cap 09:10:15–09:12:05; 10 at 09:12:10; no cap at 09:12:15; 10 at 09:12:20; no cap at 09:12:25; 10 09:12:30–09:22:05
- getcart: no cap 09:10:15–09:12:05; 10 at 09:12:10; no cap 09:12:11–09:12:15; 10 at 09:12:20; no cap at 09:12:25; 10 09:12:30–09:22:05
- postcart: 8 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 09:10:15–09:22:05

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 714 | 1150 | 0.8 | 0.087 | 0.349 | 0 | 0.0% |
| checkoutservice | 714 | 800 | 0.8 | 0.049 | 0.32 | 0 | 0.0% |
| recommendationservice | 714 | 1150 | 0.8 | 0.042 | 0.087 | 0 | 0.0% |
| paymentservice | 714 | 155 | 0.8 | 0.039 | 0.31 | 0 | 0.0% |
| emailservice | 714 | 120 | 0.8 | 0.104 | 0.542 | 0 | 0.0% |
| productcatalogservice | 714 | 50 | 0.95 | 0.324 | 1.32 | 175 | 24.5% |
| cartservice | 714 | 800 | 0.95 | 0.087 | 0.367 | 0 | 0.0% |
| currencyservice | 714 | 770 | 0.8 | 0.023 | 0.121 | 0 | 0.0% |
| shippingservice | 714 | 770 | 0.8 | 0.013 | 0.081 | 0 | 0.0% |
| adservice | 714 | 1150 | 0.8 | 0.025 | 0.061 | 0 | 0.0% |
| redis-cart | 714 | 540 | 0.8 | 0.02 | 0.176 | 0 | 0.0% |

### `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2`

`S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2` is FLAGGED with TopFull on. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T09:30:45Z → 2026-10-13T09:40:10Z. Reason text: 227× timed out; 1× <urlopen error timed out>. The CSV covers 713 s (2026-10-13T09:28:22Z → 2026-10-13T09:40:15Z). Threshold reads went stale on all five APIs for 575 s (80.6% of the span). Admitted-rate reads went stale on all five APIs for 575 s (80.6% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 714 | 34 | 680 | 29 | 685 | 575 | 575 | 80.6% | 80.6% | caps 10×10; no-cap (10000) ×22; empty read (0) ×2 | min 0 / median 0 / mean 1.2 / max 6 (n=29 fresh) |
| postcheckout | 714 | 34 | 680 | 29 | 685 | 575 | 575 | 80.6% | 80.6% | caps 10×9; no-cap (10000) ×22; empty read (0) ×3 | min 0 / median 0 / mean 1.2 / max 6 (n=29 fresh) |
| getcart | 714 | 34 | 680 | 29 | 685 | 575 | 575 | 80.6% | 80.6% | caps 10×9; no-cap (10000) ×23; empty read (0) ×2 | min 0 / median 0 / mean 1.2 / max 6 (n=29 fresh) |
| postcart | 714 | 34 | 680 | 29 | 685 | 575 | 575 | 80.6% | 80.6% | caps min 137.4 / median 239.4 / max 329.7 / 9 distinct / 10 fresh reads; no-cap (10000) ×22; empty read (0) ×2 | min 0 / median 0 / mean 67.6 / max 381 (n=29 fresh) |
| emptycart | 714 | 34 | 680 | 29 | 685 | 575 | 575 | 80.6% | 80.6% | no-cap (10000) ×29; empty read (0) ×5 | min 0 / median 0 / mean 0.8 / max 4 (n=29 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 09:28:25–09:30:10; 10 09:30:15–09:40:15
- postcheckout: no cap 09:28:25–09:30:10; 10 09:30:15–09:40:15
- getcart: no cap 09:28:25–09:30:10; 10 09:30:15–09:30:20; no cap at 09:30:22; 10 09:30:25–09:40:15
- postcart: 10 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 09:28:25–09:40:15

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 714 | 1150 | 0.8 | 0.081 | 0.287 | 0 | 0.0% |
| checkoutservice | 714 | 800 | 0.8 | 0.054 | 0.321 | 0 | 0.0% |
| recommendationservice | 714 | 1150 | 0.8 | 0.042 | 0.09 | 0 | 0.0% |
| paymentservice | 714 | 155 | 0.8 | 0.037 | 0.355 | 0 | 0.0% |
| emailservice | 714 | 120 | 0.8 | 0.102 | 0.508 | 0 | 0.0% |
| productcatalogservice | 714 | 50 | 0.95 | 0.305 | 1.28 | 144 | 20.2% |
| cartservice | 714 | 800 | 0.95 | 0.085 | 0.339 | 0 | 0.0% |
| currencyservice | 714 | 770 | 0.8 | 0.022 | 0.164 | 0 | 0.0% |
| shippingservice | 714 | 770 | 0.8 | 0.014 | 0.07 | 0 | 0.0% |
| adservice | 714 | 1150 | 0.8 | 0.025 | 0.068 | 0 | 0.0% |
| redis-cart | 714 | 540 | 0.8 | 0.019 | 0.191 | 0 | 0.0% |

### `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2_r2`

`S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2_r2` is FLAGGED with TopFull on. The collector log has 224 `fetch failed` warnings (thresholds fetch failed ×112, stats fetch failed ×112), from 2026-10-13T09:49:00Z → 2026-10-13T09:58:15Z. Reason text: 223× timed out; 1× <urlopen error timed out>. The CSV covers 713 s (2026-10-13T09:46:30Z → 2026-10-13T09:58:23Z). Threshold reads went stale on all five APIs for 562 s (78.8% of the span). Admitted-rate reads went stale on all five APIs for 565 s (79.2% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 714 | 36 | 678 | 31 | 683 | 562 | 565 | 78.8% | 79.2% | caps 10×9; no-cap (10000) ×23; empty read (0) ×4 | min 0 / median 0 / mean 1.7 / max 10 (n=31 fresh) |
| postcheckout | 714 | 36 | 678 | 31 | 683 | 562 | 565 | 78.8% | 79.2% | caps 10×10; no-cap (10000) ×24; empty read (0) ×2 | min 0 / median 0 / mean 1.7 / max 10 (n=31 fresh) |
| getcart | 714 | 36 | 678 | 31 | 683 | 562 | 565 | 78.8% | 79.2% | caps 10×10; no-cap (10000) ×23; empty read (0) ×3 | min 0 / median 0 / mean 1.8 / max 10 (n=31 fresh) |
| postcart | 714 | 36 | 678 | 31 | 683 | 562 | 565 | 78.8% | 79.2% | caps min 66 / median 267.446 / max 560 / 10 distinct / 12 fresh reads; no-cap (10000) ×22; empty read (0) ×2 | min 0 / median 0 / mean 105.2 / max 599 (n=31 fresh) |
| emptycart | 714 | 36 | 678 | 31 | 683 | 562 | 565 | 78.8% | 79.2% | no-cap (10000) ×31; empty read (0) ×5 | min 0 / median 0 / mean 1.0 / max 5 (n=31 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 09:46:30–09:48:15; 10 at 09:48:20; no cap at 09:48:25; 10 09:48:30–09:58:20
- postcheckout: no cap 09:46:30–09:48:15; 10 at 09:48:20; no cap at 09:48:25; 10 09:48:30–09:48:52; no cap at 09:48:55; 10 09:48:58–09:58:20
- getcart: no cap 09:46:30–09:48:15; 10 at 09:48:20; no cap at 09:48:25; 10 09:48:30–09:58:20
- postcart: 11 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 09:46:30–09:58:20

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 714 | 1150 | 0.8 | 0.187 | 0.368 | 0 | 0.0% |
| checkoutservice | 714 | 800 | 0.8 | 0.015 | 0.224 | 0 | 0.0% |
| recommendationservice | 714 | 1150 | 0.8 | 0.045 | 0.087 | 0 | 0.0% |
| paymentservice | 714 | 155 | 0.8 | 0.028 | 0.284 | 0 | 0.0% |
| emailservice | 714 | 120 | 0.8 | 0.082 | 0.45 | 0 | 0.0% |
| productcatalogservice | 714 | 50 | 0.95 | 0.358 | 1.28 | 196 | 27.5% |
| cartservice | 714 | 800 | 0.95 | 0.057 | 0.427 | 0 | 0.0% |
| currencyservice | 714 | 770 | 0.8 | 0.016 | 0.084 | 0 | 0.0% |
| shippingservice | 714 | 770 | 0.8 | 0.009 | 0.057 | 0 | 0.0% |
| adservice | 714 | 1150 | 0.8 | 0.024 | 0.135 | 0 | 0.0% |
| redis-cart | 714 | 540 | 0.8 | 0.017 | 0.126 | 0 | 0.0% |

### `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3`

`S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3` is FLAGGED with TopFull on. The collector log has 226 `fetch failed` warnings (thresholds fetch failed ×113, stats fetch failed ×113), from 2026-10-13T20:26:25Z → 2026-10-13T20:35:45Z. Reason text: 223× timed out; 3× <urlopen error timed out>. The CSV covers 720 s (2026-10-13T20:23:48Z → 2026-10-13T20:35:48Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 568 s (78.9% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 721 | 700 | 21 | 31 | 690 | 5 | 568 | 0.0% | 78.9% | caps 10×103, 12.3×1, 14.6×1, 18.3×1, 18.5×1; no-cap (10000) ×26; empty read (0) ×567 | min 0 / median 0 / mean 6.8 / max 44 (n=31 fresh) |
| postcheckout | 721 | 700 | 21 | 31 | 690 | 5 | 568 | 0.0% | 78.9% | caps 10×107, 11.8×2; no-cap (10000) ×26; empty read (0) ×565 | min 0 / median 0 / mean 2.9 / max 18 (n=31 fresh) |
| getcart | 721 | 700 | 21 | 31 | 690 | 5 | 568 | 0.0% | 78.9% | caps 10×102, 19×1, 20.3×1, 20.5×2, 20.6×1, 21.0324×2; no-cap (10000) ×26; empty read (0) ×565 | min 0 / median 0 / mean 7.1 / max 44 (n=31 fresh) |
| postcart | 721 | 700 | 21 | 31 | 690 | 5 | 568 | 0.0% | 78.9% | caps 234.3×1, 234.5×1, 307.3×1, 307.356×1, 307.4×1, 401.4×1, 417.753×102, 422.821×563; no-cap (10000) ×26; empty read (0) ×3 | min 0 / median 0 / mean 85.5 / max 534 (n=31 fresh) |
| emptycart | 721 | 700 | 21 | 31 | 690 | 5 | 568 | 0.0% | 78.9% | no-cap (10000) ×31; empty read (0) ×669 | min 0 / median 0 / mean 0.8 / max 5 (n=31 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 57 live-cap changes (see fresh-threshold counts)
- postcheckout: 55 live-cap changes (see fresh-threshold counts)
- getcart: 58 live-cap changes (see fresh-threshold counts)
- postcart: 59 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 20:23:50–20:26:20

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 721 | 1150 | 0.8 | 0.094 | 0.198 | 0 | 0.0% |
| checkoutservice | 721 | 800 | 0.8 | 0.141 | 0.389 | 0 | 0.0% |
| recommendationservice | 721 | 1150 | 0.8 | 0.074 | 0.137 | 0 | 0.0% |
| paymentservice | 721 | 155 | 0.8 | 0.056 | 0.329 | 0 | 0.0% |
| emailservice | 721 | 120 | 0.8 | 0.157 | 0.533 | 0 | 0.0% |
| productcatalogservice | 721 | 100 | 0.95 | 0.55 | 1.1 | 283 | 39.3% |
| cartservice | 721 | 800 | 0.95 | 0.167 | 0.502 | 0 | 0.0% |
| currencyservice | 721 | 770 | 0.8 | 0.057 | 0.14 | 0 | 0.0% |
| shippingservice | 721 | 770 | 0.8 | 0.026 | 0.086 | 0 | 0.0% |
| adservice | 721 | 1150 | 0.8 | 0.03 | 0.071 | 0 | 0.0% |
| redis-cart | 721 | 540 | 0.8 | 0.033 | 0.252 | 0 | 0.0% |

### `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3_r2`

`S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3_r2` is FLAGGED with TopFull on. The collector log has 222 `fetch failed` warnings (thresholds fetch failed ×111, stats fetch failed ×111), from 2026-10-13T20:45:20Z → 2026-10-13T20:54:30Z. Reason text: 216× timed out; 6× <urlopen error timed out>. The CSV covers 724 s (2026-10-13T20:42:33Z → 2026-10-13T20:54:37Z). Threshold reads went stale on all five APIs for 558 s (77.1% of the span). Admitted-rate reads went stale on all five APIs for 560 s (77.3% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 725 | 38 | 687 | 34 | 691 | 558 | 560 | 77.1% | 77.3% | caps 10×4, 10.3×1, 10.5×1, 10.9×1, 11.7×1, 20×2; no-cap (10000) ×26; empty read (0) ×2 | min 0 / median 0 / mean 9.3 / max 50 (n=34 fresh) |
| postcheckout | 725 | 38 | 687 | 34 | 691 | 558 | 560 | 77.1% | 77.3% | caps 10×5, 10.3×1, 10.5×1, 13.5×1, 14.3×1; no-cap (10000) ×26; empty read (0) ×3 | min 0 / median 0 / mean 3.7 / max 20 (n=34 fresh) |
| getcart | 725 | 38 | 687 | 34 | 691 | 558 | 560 | 77.1% | 77.3% | caps 10×3, 10.3×1, 10.5×1, 11.6×1, 11.6454×1, 12.4×1, 20×2; no-cap (10000) ×26; empty read (0) ×2 | min 0 / median 0 / mean 9.6 / max 50 (n=34 fresh) |
| postcart | 725 | 38 | 687 | 34 | 691 | 558 | 560 | 77.1% | 77.3% | caps min 226.974 / median 302.5 / max 446.4 / 9 distinct / 11 fresh reads; no-cap (10000) ×26; empty read (0) ×1 | min 0 / median 0 / mean 115.9 / max 598 (n=34 fresh) |
| emptycart | 725 | 38 | 687 | 34 | 691 | 558 | 560 | 77.1% | 77.3% | no-cap (10000) ×34; empty read (0) ×4 | min 0 / median 0 / mean 1.1 / max 5 (n=34 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 8 live-cap changes (see fresh-threshold counts)
- postcheckout: 7 live-cap changes (see fresh-threshold counts)
- getcart: 9 live-cap changes (see fresh-threshold counts)
- postcart: 10 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 20:42:35–20:54:35

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 725 | 1150 | 0.8 | 0.13 | 0.331 | 0 | 0.0% |
| checkoutservice | 725 | 800 | 0.8 | 0.128 | 0.489 | 0 | 0.0% |
| recommendationservice | 725 | 1150 | 0.8 | 0.056 | 0.122 | 0 | 0.0% |
| paymentservice | 725 | 155 | 0.8 | 0.054 | 0.361 | 0 | 0.0% |
| emailservice | 725 | 120 | 0.8 | 0.158 | 0.542 | 0 | 0.0% |
| productcatalogservice | 725 | 100 | 0.95 | 0.489 | 1.1 | 263 | 36.3% |
| cartservice | 725 | 800 | 0.95 | 0.15 | 0.521 | 0 | 0.0% |
| currencyservice | 725 | 770 | 0.8 | 0.041 | 0.126 | 0 | 0.0% |
| shippingservice | 725 | 770 | 0.8 | 0.021 | 0.084 | 0 | 0.0% |
| adservice | 725 | 1150 | 0.8 | 0.029 | 0.071 | 0 | 0.0% |
| redis-cart | 725 | 540 | 0.8 | 0.034 | 0.302 | 0 | 0.0% |

### `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4`

`S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4` is FLAGGED with TopFull on. The collector log has 226 `fetch failed` warnings (thresholds fetch failed ×113, stats fetch failed ×113), from 2026-10-13T21:03:55Z → 2026-10-13T21:13:15Z. Reason text: 225× timed out; 1× <urlopen error timed out>. The CSV covers 723 s (2026-10-13T21:01:17Z → 2026-10-13T21:13:20Z). Threshold reads went stale on all five APIs for 570 s (78.8% of the span). Admitted-rate reads went stale on all five APIs for 570 s (78.8% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 724 | 36 | 688 | 32 | 692 | 570 | 570 | 78.8% | 78.8% | caps 10×2, 10.6×1, 11.2×1, 11.8×1, 11.8208×1, 12.8×1, 19.7×1, 20×1; no-cap (10000) ×26; empty read (0) ×1 | min 0 / median 0 / mean 6.8 / max 42 (n=32 fresh) |
| postcheckout | 724 | 36 | 688 | 32 | 692 | 570 | 570 | 78.8% | 78.8% | caps 10×4, 10.6×1, 12.1773×1, 12.2×1; no-cap (10000) ×26; empty read (0) ×3 | min 0 / median 0 / mean 3.0 / max 18 (n=32 fresh) |
| getcart | 724 | 36 | 688 | 32 | 692 | 570 | 570 | 78.8% | 78.8% | caps 10×2, 10.6×1, 12.8×1, 13.4×2, 19.7×1, 20×1; no-cap (10000) ×26; empty read (0) ×2 | min 0 / median 0 / mean 7.1 / max 44 (n=32 fresh) |
| postcart | 724 | 36 | 688 | 32 | 692 | 570 | 570 | 78.8% | 78.8% | caps 238.8×1, 245.7×1, 246×1, 290.576×1, 290.6×1, 291.1×1, 305.5×1, 353.3×1; no-cap (10000) ×26; empty read (0) ×2 | min 0 / median 0 / mean 84.4 / max 465 (n=32 fresh) |
| emptycart | 724 | 36 | 688 | 32 | 692 | 570 | 570 | 78.8% | 78.8% | no-cap (10000) ×32; empty read (0) ×4 | min 0 / median 0 / mean 0.8 / max 5 (n=32 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 9 live-cap changes (see fresh-threshold counts)
- postcheckout: no cap 21:01:20–21:03:25; 10 21:03:30–21:03:35; 12.1773 at 21:03:38; 12.2 at 21:03:40; 10 21:03:45–21:03:50; 10.6 at 21:13:20
- getcart: 7 live-cap changes (see fresh-threshold counts)
- postcart: 9 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 21:01:20–21:13:20

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 724 | 1150 | 0.8 | 0.084 | 0.143 | 0 | 0.0% |
| checkoutservice | 724 | 800 | 0.8 | 0.232 | 0.522 | 0 | 0.0% |
| recommendationservice | 724 | 1150 | 0.8 | 0.061 | 0.117 | 0 | 0.0% |
| paymentservice | 724 | 155 | 0.8 | 0.075 | 0.374 | 0 | 0.0% |
| emailservice | 724 | 120 | 0.8 | 0.209 | 0.55 | 0 | 0.0% |
| productcatalogservice | 724 | 100 | 0.95 | 0.819 | 1.15 | 475 | 65.6% |
| cartservice | 724 | 800 | 0.95 | 0.236 | 0.456 | 0 | 0.0% |
| currencyservice | 724 | 770 | 0.8 | 0.058 | 0.149 | 0 | 0.0% |
| shippingservice | 724 | 770 | 0.8 | 0.031 | 0.097 | 0 | 0.0% |
| adservice | 724 | 1150 | 0.8 | 0.032 | 0.072 | 0 | 0.0% |
| redis-cart | 724 | 540 | 0.8 | 0.04 | 0.237 | 0 | 0.0% |

### `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4_r2`

`S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4_r2` is FLAGGED with TopFull on. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T21:23:05Z → 2026-10-13T21:32:30Z. Reason text: 228× timed out. The CSV covers 726 s (2026-10-13T21:20:28Z → 2026-10-13T21:32:34Z). Threshold reads went stale on all five APIs for 572 s (78.8% of the span). Admitted-rate reads went stale on all five APIs for 574 s (79.1% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 727 | 37 | 690 | 31 | 696 | 572 | 574 | 78.8% | 79.1% | caps 11.3×1, 15.5×1, 16×1, 16.1929×2, 16.2×1, 16.2934×1, 16.3×1; no-cap (10000) ×26; empty read (0) ×3 | min 0 / median 0 / mean 5.3 / max 38 (n=31 fresh) |
| postcheckout | 727 | 37 | 690 | 31 | 696 | 572 | 574 | 78.8% | 79.1% | caps 10×2, 12.1×1, 12.1×1, 13×3; no-cap (10000) ×27; empty read (0) ×3 | min 0 / median 0 / mean 2.3 / max 16 (n=31 fresh) |
| getcart | 727 | 37 | 690 | 31 | 696 | 572 | 574 | 78.8% | 79.1% | caps 18×1, 18.2×1, 18.3×1, 20.3×1, 22.6×1, 22.6345×1; no-cap (10000) ×26; empty read (0) ×5 | min 0 / median 0 / mean 5.7 / max 40 (n=31 fresh) |
| postcart | 727 | 37 | 690 | 31 | 696 | 572 | 574 | 78.8% | 79.1% | caps 210×1, 210.2×1, 210.3×1, 291.792×1, 305.7×1, 396.9×1, 492.167×1; no-cap (10000) ×26; empty read (0) ×4 | min 0 / median 0 / mean 67.0 / max 452 (n=31 fresh) |
| emptycart | 727 | 37 | 690 | 31 | 696 | 572 | 574 | 78.8% | 79.1% | no-cap (10000) ×31; empty read (0) ×6 | min 0 / median 0 / mean 0.6 / max 4 (n=31 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 8 live-cap changes (see fresh-threshold counts)
- postcheckout: no cap 21:20:30–21:22:35; 10 21:22:40–21:22:45; 12.1 at 21:22:49; 12.1 at 21:22:50; no cap at 21:22:52; 13 21:22:55–21:23:00
- getcart: 7 live-cap changes (see fresh-threshold counts)
- postcart: 8 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 21:20:30–21:23:00

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 727 | 1150 | 0.8 | 0.121 | 0.304 | 0 | 0.0% |
| checkoutservice | 727 | 800 | 0.8 | 0.148 | 0.51 | 0 | 0.0% |
| recommendationservice | 727 | 1150 | 0.8 | 0.09 | 0.33 | 0 | 0.0% |
| paymentservice | 727 | 155 | 0.8 | 0.062 | 0.374 | 0 | 0.0% |
| emailservice | 727 | 120 | 0.8 | 0.162 | 0.633 | 0 | 0.0% |
| productcatalogservice | 727 | 100 | 0.95 | 0.497 | 1.18 | 262 | 36.0% |
| cartservice | 727 | 800 | 0.95 | 0.207 | 0.569 | 0 | 0.0% |
| currencyservice | 727 | 770 | 0.8 | 0.058 | 0.197 | 0 | 0.0% |
| shippingservice | 727 | 770 | 0.8 | 0.025 | 0.105 | 0 | 0.0% |
| adservice | 727 | 1150 | 0.8 | 0.03 | 0.064 | 0 | 0.0% |
| redis-cart | 727 | 540 | 0.8 | 0.034 | 0.331 | 0 | 0.0% |

### `S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run2_r2`

`S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run2_r2` is FLAGGED with TopFull on. The collector log has 216 `fetch failed` warnings (thresholds fetch failed ×108, stats fetch failed ×108), from 2026-10-14T04:38:50Z → 2026-10-14T04:47:45Z. Reason text: 216× timed out. The CSV covers 716 s (2026-10-14T04:35:55Z → 2026-10-14T04:47:51Z). Threshold reads went stale on all five APIs for 545 s (76.1% of the span). Admitted-rate reads went stale on all five APIs for 545 s (76.1% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 717 | 36 | 681 | 36 | 681 | 545 | 545 | 76.1% | 76.1% | no-cap (10000) ×36 | min 0 / median 0 / mean 13.0 / max 50 (n=36 fresh) |
| postcheckout | 717 | 36 | 681 | 36 | 681 | 545 | 545 | 76.1% | 76.1% | no-cap (10000) ×36 | min 0 / median 0 / mean 5.2 / max 20 (n=36 fresh) |
| getcart | 717 | 36 | 681 | 36 | 681 | 545 | 545 | 76.1% | 76.1% | no-cap (10000) ×36 | min 0 / median 0 / mean 13.3 / max 50 (n=36 fresh) |
| postcart | 717 | 36 | 681 | 36 | 681 | 545 | 545 | 76.1% | 76.1% | no-cap (10000) ×36 | min 0 / median 0 / mean 160.6 / max 612 (n=36 fresh) |
| emptycart | 717 | 36 | 681 | 36 | 681 | 545 | 545 | 76.1% | 76.1% | no-cap (10000) ×36 | min 0 / median 0 / mean 1.5 / max 5 (n=36 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 04:35:55–04:47:50
- postcheckout: no cap 04:35:55–04:47:50
- getcart: no cap 04:35:55–04:47:50
- postcart: no cap 04:35:55–04:47:50
- emptycart: no cap 04:35:55–04:47:50

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 717 | 1150 | 0.8 | 0.203 | 0.312 | 0 | 0.0% |
| checkoutservice | 717 | 800 | 0.8 | 0.342 | 0.55 | 0 | 0.0% |
| recommendationservice | 717 | 1150 | 0.8 | 0.18 | 0.349 | 0 | 0.0% |
| paymentservice | 717 | 155 | 0.8 | 0.133 | 0.406 | 0 | 0.0% |
| emailservice | 717 | 120 | 0.8 | 0.338 | 0.733 | 0 | 0.0% |
| productcatalogservice | 717 | 800 | 0.95 | 0.317 | 0.487 | 0 | 0.0% |
| cartservice | 717 | 800 | 0.95 | 0.434 | 0.838 | 0 | 0.0% |
| currencyservice | 717 | 770 | 0.8 | 0.158 | 0.321 | 0 | 0.0% |
| shippingservice | 717 | 770 | 0.8 | 0.06 | 0.123 | 0 | 0.0% |
| adservice | 717 | 1150 | 0.8 | 0.045 | 0.096 | 0 | 0.0% |
| redis-cart | 717 | 540 | 0.8 | 0.083 | 0.457 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1` is FLAGGED with TopFull off. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T07:41:55Z → 2026-10-13T07:51:20Z. Reason text: 228× timed out. The CSV covers 709 s (2026-10-13T07:39:35Z → 2026-10-13T07:51:24Z). Threshold reads went stale on all five APIs for 574 s (81.0% of the span). Admitted-rate reads went stale on all five APIs for 574 s (81.0% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 710 | 28 | 682 | 28 | 682 | 574 | 574 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 1.0 / max 5 (n=28 fresh) |
| postcheckout | 710 | 28 | 682 | 28 | 682 | 574 | 574 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 1.0 / max 6 (n=28 fresh) |
| getcart | 710 | 28 | 682 | 28 | 682 | 574 | 574 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 1.0 / max 6 (n=28 fresh) |
| postcart | 710 | 28 | 682 | 28 | 682 | 574 | 574 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 63.9 / max 352 (n=28 fresh) |
| emptycart | 710 | 28 | 682 | 28 | 682 | 574 | 574 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 0.7 / max 4 (n=28 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 07:39:35–07:41:50
- postcheckout: no cap 07:39:35–07:41:50
- getcart: no cap 07:39:35–07:41:50
- postcart: no cap 07:39:35–07:41:50
- emptycart: no cap 07:39:35–07:41:50

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 710 | 1150 | 0.8 | 0.183 | 0.556 | 0 | 0.0% |
| checkoutservice | 710 | 800 | 0.8 | 0.01 | 0.215 | 0 | 0.0% |
| recommendationservice | 710 | 1150 | 0.8 | 0.043 | 0.087 | 0 | 0.0% |
| paymentservice | 710 | 155 | 0.8 | 0.028 | 0.284 | 0 | 0.0% |
| emailservice | 710 | 120 | 0.8 | 0.079 | 0.392 | 0 | 0.0% |
| productcatalogservice | 710 | 50 | 0.95 | 0.317 | 1.24 | 162 | 22.8% |
| cartservice | 710 | 800 | 0.95 | 0.051 | 0.281 | 0 | 0.0% |
| currencyservice | 710 | 770 | 0.8 | 0.016 | 0.09 | 0 | 0.0% |
| shippingservice | 710 | 770 | 0.8 | 0.009 | 0.066 | 0 | 0.0% |
| adservice | 710 | 1150 | 0.8 | 0.024 | 0.075 | 0 | 0.0% |
| redis-cart | 710 | 540 | 0.8 | 0.017 | 0.144 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1_r2`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1_r2` is FLAGGED with TopFull off. The collector log has 226 `fetch failed` warnings (thresholds fetch failed ×113, stats fetch failed ×113), from 2026-10-13T08:00:05Z → 2026-10-13T08:09:25Z. Reason text: 225× timed out; 1× <urlopen error timed out>. The CSV covers 710 s (2026-10-13T07:57:39Z → 2026-10-13T08:09:29Z). Threshold reads went stale on all five APIs for 569 s (80.1% of the span). Admitted-rate reads went stale on all five APIs for 569 s (80.1% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 711 | 29 | 682 | 29 | 682 | 569 | 569 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 1.2 / max 8 (n=29 fresh) |
| postcheckout | 711 | 29 | 682 | 29 | 682 | 569 | 569 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 1.1 / max 6 (n=29 fresh) |
| getcart | 711 | 29 | 682 | 29 | 682 | 569 | 569 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 1.1 / max 6 (n=29 fresh) |
| postcart | 711 | 29 | 682 | 29 | 682 | 569 | 569 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 75.0 / max 510 (n=29 fresh) |
| emptycart | 711 | 29 | 682 | 29 | 682 | 569 | 569 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 0.9 / max 5 (n=29 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 07:57:40–08:00:00
- postcheckout: no cap 07:57:40–08:00:00
- getcart: no cap 07:57:40–08:00:00
- postcart: no cap 07:57:40–08:00:00
- emptycart: no cap 07:57:40–08:00:00

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 711 | 1150 | 0.8 | 0.15 | 0.337 | 0 | 0.0% |
| checkoutservice | 711 | 800 | 0.8 | 0.01 | 0.19 | 0 | 0.0% |
| recommendationservice | 711 | 1150 | 0.8 | 0.042 | 0.092 | 0 | 0.0% |
| paymentservice | 711 | 155 | 0.8 | 0.028 | 0.29 | 0 | 0.0% |
| emailservice | 711 | 120 | 0.8 | 0.081 | 0.4 | 0 | 0.0% |
| productcatalogservice | 711 | 50 | 0.95 | 0.334 | 1.38 | 164 | 23.1% |
| cartservice | 711 | 800 | 0.95 | 0.051 | 0.224 | 0 | 0.0% |
| currencyservice | 711 | 770 | 0.8 | 0.016 | 0.07 | 0 | 0.0% |
| shippingservice | 711 | 770 | 0.8 | 0.009 | 0.061 | 0 | 0.0% |
| adservice | 711 | 1150 | 0.8 | 0.024 | 0.056 | 0 | 0.0% |
| redis-cart | 711 | 540 | 0.8 | 0.017 | 0.131 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2` is FLAGGED with TopFull off. The collector log has 230 `fetch failed` warnings (thresholds fetch failed ×115, stats fetch failed ×115), from 2026-10-13T08:18:05Z → 2026-10-13T08:27:35Z. Reason text: 229× timed out; 1× <urlopen error timed out>. The CSV covers 714 s (2026-10-13T08:15:44Z → 2026-10-13T08:27:38Z). Threshold reads went stale on all five APIs for 578 s (81.0% of the span). Admitted-rate reads went stale on all five APIs for 578 s (81.0% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 715 | 28 | 687 | 28 | 687 | 578 | 578 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 0.7 / max 5 (n=28 fresh) |
| postcheckout | 715 | 28 | 687 | 28 | 687 | 578 | 578 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 0.8 / max 5 (n=28 fresh) |
| getcart | 715 | 28 | 687 | 28 | 687 | 578 | 578 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 0.8 / max 5 (n=28 fresh) |
| postcart | 715 | 28 | 687 | 28 | 687 | 578 | 578 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 55.2 / max 340 (n=28 fresh) |
| emptycart | 715 | 28 | 687 | 28 | 687 | 578 | 578 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 0.6 / max 4 (n=28 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 08:15:45–08:18:00
- postcheckout: no cap 08:15:45–08:18:00
- getcart: no cap 08:15:45–08:18:00
- postcart: no cap 08:15:45–08:18:00
- emptycart: no cap 08:15:45–08:18:00

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 715 | 1150 | 0.8 | 0.148 | 0.338 | 0 | 0.0% |
| checkoutservice | 715 | 800 | 0.8 | 0.014 | 0.196 | 0 | 0.0% |
| recommendationservice | 715 | 1150 | 0.8 | 0.041 | 0.098 | 0 | 0.0% |
| paymentservice | 715 | 155 | 0.8 | 0.028 | 0.284 | 0 | 0.0% |
| emailservice | 715 | 120 | 0.8 | 0.086 | 0.425 | 0 | 0.0% |
| productcatalogservice | 715 | 50 | 0.95 | 0.364 | 1.28 | 190 | 26.6% |
| cartservice | 715 | 800 | 0.95 | 0.052 | 0.384 | 0 | 0.0% |
| currencyservice | 715 | 770 | 0.8 | 0.016 | 0.073 | 0 | 0.0% |
| shippingservice | 715 | 770 | 0.8 | 0.009 | 0.052 | 0 | 0.0% |
| adservice | 715 | 1150 | 0.8 | 0.025 | 0.064 | 0 | 0.0% |
| redis-cart | 715 | 540 | 0.8 | 0.016 | 0.148 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2_r2`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2_r2` is FLAGGED with TopFull off. The collector log has 230 `fetch failed` warnings (thresholds fetch failed ×115, stats fetch failed ×115), from 2026-10-13T08:36:10Z → 2026-10-13T08:45:40Z. Reason text: 228× timed out; 2× <urlopen error timed out>. The CSV covers 710 s (2026-10-13T08:33:52Z → 2026-10-13T08:45:42Z). Threshold reads went stale on all five APIs for 577 s (81.3% of the span). Admitted-rate reads went stale on all five APIs for 577 s (81.3% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 711 | 27 | 684 | 27 | 684 | 577 | 577 | 81.3% | 81.3% | no-cap (10000) ×27 | min 0 / median 0 / mean 0.8 / max 6 (n=27 fresh) |
| postcheckout | 711 | 27 | 684 | 27 | 684 | 577 | 577 | 81.3% | 81.3% | no-cap (10000) ×27 | min 0 / median 0 / mean 0.9 / max 6 (n=27 fresh) |
| getcart | 711 | 27 | 684 | 27 | 684 | 577 | 577 | 81.3% | 81.3% | no-cap (10000) ×27 | min 0 / median 0 / mean 1.0 / max 6 (n=27 fresh) |
| postcart | 711 | 27 | 684 | 27 | 684 | 577 | 577 | 81.3% | 81.3% | no-cap (10000) ×27 | min 0 / median 0 / mean 60.3 / max 414 (n=27 fresh) |
| emptycart | 711 | 27 | 684 | 27 | 684 | 577 | 577 | 81.3% | 81.3% | no-cap (10000) ×27 | min 0 / median 0 / mean 0.7 / max 4 (n=27 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 08:33:55–08:36:05
- postcheckout: no cap 08:33:55–08:36:05
- getcart: no cap 08:33:55–08:36:05
- postcart: no cap 08:33:55–08:36:05
- emptycart: no cap 08:33:55–08:36:05

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 711 | 1150 | 0.8 | 0.145 | 0.314 | 0 | 0.0% |
| checkoutservice | 711 | 800 | 0.8 | 0.011 | 0.14 | 0 | 0.0% |
| recommendationservice | 711 | 1150 | 0.8 | 0.041 | 0.089 | 0 | 0.0% |
| paymentservice | 711 | 155 | 0.8 | 0.028 | 0.29 | 0 | 0.0% |
| emailservice | 711 | 120 | 0.8 | 0.085 | 0.417 | 0 | 0.0% |
| productcatalogservice | 711 | 50 | 0.95 | 0.325 | 1.48 | 167 | 23.5% |
| cartservice | 711 | 800 | 0.95 | 0.054 | 0.426 | 0 | 0.0% |
| currencyservice | 711 | 770 | 0.8 | 0.015 | 0.069 | 0 | 0.0% |
| shippingservice | 711 | 770 | 0.8 | 0.009 | 0.051 | 0 | 0.0% |
| adservice | 711 | 1150 | 0.8 | 0.024 | 0.057 | 0 | 0.0% |
| redis-cart | 711 | 540 | 0.8 | 0.016 | 0.178 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3` is FLAGGED with TopFull off. The collector log has 226 `fetch failed` warnings (thresholds fetch failed ×113, stats fetch failed ×113), from 2026-10-13T19:11:00Z → 2026-10-13T19:20:20Z. Reason text: 226× timed out. The CSV covers 722 s (2026-10-13T19:08:25Z → 2026-10-13T19:20:27Z). Threshold freshness stayed within 30 s on every API (longest 1 s). Admitted-rate reads went stale on all five APIs for 570 s (78.9% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 723 | 723 | 0 | 32 | 691 | 1 | 570 | 0.0% | 78.9% | caps 10×691; no-cap (10000) ×32 | min 0 / median 0 / mean 5.3 / max 34 (n=32 fresh) |
| postcheckout | 723 | 723 | 0 | 32 | 691 | 1 | 570 | 0.0% | 78.9% | caps 10×691; no-cap (10000) ×32 | min 0 / median 0 / mean 2.1 / max 15 (n=32 fresh) |
| getcart | 723 | 723 | 0 | 32 | 691 | 1 | 570 | 0.0% | 78.9% | caps 10×691; no-cap (10000) ×32 | min 0 / median 0 / mean 5.8 / max 36 (n=32 fresh) |
| postcart | 723 | 723 | 0 | 32 | 691 | 1 | 570 | 0.0% | 78.9% | caps 417.753×691; no-cap (10000) ×32 | min 0 / median 0 / mean 85.5 / max 498 (n=32 fresh) |
| emptycart | 723 | 723 | 0 | 32 | 691 | 1 | 570 | 0.0% | 78.9% | no-cap (10000) ×32; empty read (0) ×691 | min 0 / median 0 / mean 0.9 / max 5 (n=32 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 64 live-cap changes (see fresh-threshold counts)
- postcheckout: 64 live-cap changes (see fresh-threshold counts)
- getcart: 64 live-cap changes (see fresh-threshold counts)
- postcart: 64 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 19:08:25–19:20:25

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 723 | 1150 | 0.8 | 0.149 | 0.235 | 0 | 0.0% |
| checkoutservice | 723 | 800 | 0.8 | 0.04 | 0.3 | 0 | 0.0% |
| recommendationservice | 723 | 1150 | 0.8 | 0.126 | 0.263 | 0 | 0.0% |
| paymentservice | 723 | 155 | 0.8 | 0.034 | 0.329 | 0 | 0.0% |
| emailservice | 723 | 120 | 0.8 | 0.106 | 0.508 | 0 | 0.0% |
| productcatalogservice | 723 | 100 | 0.95 | 0.394 | 1.14 | 214 | 29.6% |
| cartservice | 723 | 800 | 0.95 | 0.143 | 0.509 | 0 | 0.0% |
| currencyservice | 723 | 770 | 0.8 | 0.062 | 0.173 | 0 | 0.0% |
| shippingservice | 723 | 770 | 0.8 | 0.014 | 0.075 | 0 | 0.0% |
| adservice | 723 | 1150 | 0.8 | 0.029 | 0.067 | 0 | 0.0% |
| redis-cart | 723 | 540 | 0.8 | 0.034 | 0.202 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3_r2`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3_r2` is FLAGGED with TopFull off. The collector log has 230 `fetch failed` warnings (thresholds fetch failed ×115, stats fetch failed ×115), from 2026-10-13T19:29:50Z → 2026-10-13T19:39:20Z. Reason text: 228× timed out; 2× <urlopen error timed out>. The CSV covers 722 s (2026-10-13T19:27:22Z → 2026-10-13T19:39:24Z). Threshold freshness stayed within 30 s on every API (longest 1 s). Admitted-rate reads went stale on all five APIs for 579 s (80.2% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 723 | 723 | 0 | 29 | 694 | 1 | 579 | 0.0% | 80.2% | caps 10×694; no-cap (10000) ×29 | min 0 / median 0 / mean 3.5 / max 23 (n=29 fresh) |
| postcheckout | 723 | 723 | 0 | 29 | 694 | 1 | 579 | 0.0% | 80.2% | caps 10×694; no-cap (10000) ×29 | min 0 / median 0 / mean 1.5 / max 10 (n=29 fresh) |
| getcart | 723 | 723 | 0 | 29 | 694 | 1 | 579 | 0.0% | 80.2% | caps 10×694; no-cap (10000) ×29 | min 0 / median 0 / mean 3.7 / max 24 (n=29 fresh) |
| postcart | 723 | 723 | 0 | 29 | 694 | 1 | 579 | 0.0% | 80.2% | caps 417.753×694; no-cap (10000) ×29 | min 0 / median 0 / mean 56.1 / max 425 (n=29 fresh) |
| emptycart | 723 | 723 | 0 | 29 | 694 | 1 | 579 | 0.0% | 80.2% | no-cap (10000) ×29; empty read (0) ×694 | min 0 / median 0 / mean 0.6 / max 4 (n=29 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 59 live-cap changes (see fresh-threshold counts)
- postcheckout: 59 live-cap changes (see fresh-threshold counts)
- getcart: 59 live-cap changes (see fresh-threshold counts)
- postcart: 59 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 19:27:25–19:29:45

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 723 | 1150 | 0.8 | 0.151 | 0.28 | 0 | 0.0% |
| checkoutservice | 723 | 800 | 0.8 | 0.042 | 0.295 | 0 | 0.0% |
| recommendationservice | 723 | 1150 | 0.8 | 0.118 | 0.239 | 0 | 0.0% |
| paymentservice | 723 | 155 | 0.8 | 0.033 | 0.323 | 0 | 0.0% |
| emailservice | 723 | 120 | 0.8 | 0.104 | 0.625 | 0 | 0.0% |
| productcatalogservice | 723 | 100 | 0.95 | 0.321 | 1.2 | 156 | 21.6% |
| cartservice | 723 | 800 | 0.95 | 0.178 | 0.568 | 0 | 0.0% |
| currencyservice | 723 | 770 | 0.8 | 0.054 | 0.186 | 0 | 0.0% |
| shippingservice | 723 | 770 | 0.8 | 0.014 | 0.073 | 0 | 0.0% |
| adservice | 723 | 1150 | 0.8 | 0.029 | 0.067 | 0 | 0.0% |
| redis-cart | 723 | 540 | 0.8 | 0.028 | 0.25 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4` is FLAGGED with TopFull off. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T19:48:30Z → 2026-10-13T19:58:00Z. Reason text: 223× timed out; 5× <urlopen error timed out>. The CSV covers 720 s (2026-10-13T19:46:06Z → 2026-10-13T19:58:06Z). Threshold freshness stayed within 30 s on every API (longest 2 s). Admitted-rate reads went stale on all five APIs for 580 s (80.6% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 720 | 720 | 0 | 29 | 691 | 2 | 580 | 0.0% | 80.6% | caps 10×691; no-cap (10000) ×29 | min 0 / median 0 / mean 4.3 / max 25 (n=29 fresh) |
| postcheckout | 720 | 720 | 0 | 29 | 691 | 2 | 580 | 0.0% | 80.6% | caps 10×691; no-cap (10000) ×29 | min 0 / median 0 / mean 1.9 / max 11 (n=29 fresh) |
| getcart | 720 | 720 | 0 | 29 | 691 | 2 | 580 | 0.0% | 80.6% | caps 10×691; no-cap (10000) ×29 | min 0 / median 0 / mean 4.6 / max 27 (n=29 fresh) |
| postcart | 720 | 720 | 0 | 29 | 691 | 2 | 580 | 0.0% | 80.6% | caps 417.753×691; no-cap (10000) ×29 | min 0 / median 0 / mean 60.8 / max 390 (n=29 fresh) |
| emptycart | 720 | 720 | 0 | 29 | 691 | 2 | 580 | 0.0% | 80.6% | no-cap (10000) ×29; empty read (0) ×691 | min 0 / median 0 / mean 0.6 / max 4 (n=29 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 59 live-cap changes (see fresh-threshold counts)
- postcheckout: 59 live-cap changes (see fresh-threshold counts)
- getcart: 59 live-cap changes (see fresh-threshold counts)
- postcart: 59 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 19:46:10–19:58:05

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 720 | 1150 | 0.8 | 0.141 | 0.348 | 0 | 0.0% |
| checkoutservice | 720 | 800 | 0.8 | 0.051 | 0.345 | 0 | 0.0% |
| recommendationservice | 720 | 1150 | 0.8 | 0.118 | 0.25 | 0 | 0.0% |
| paymentservice | 720 | 155 | 0.8 | 0.039 | 0.355 | 0 | 0.0% |
| emailservice | 720 | 120 | 0.8 | 0.11 | 0.475 | 0 | 0.0% |
| productcatalogservice | 720 | 100 | 0.95 | 0.395 | 1.13 | 203 | 28.2% |
| cartservice | 720 | 800 | 0.95 | 0.193 | 0.576 | 0 | 0.0% |
| currencyservice | 720 | 770 | 0.8 | 0.058 | 0.174 | 0 | 0.0% |
| shippingservice | 720 | 770 | 0.8 | 0.016 | 0.094 | 0 | 0.0% |
| adservice | 720 | 1150 | 0.8 | 0.029 | 0.071 | 0 | 0.0% |
| redis-cart | 720 | 540 | 0.8 | 0.032 | 0.272 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4_r2`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4_r2` is FLAGGED with TopFull off. The collector log has 230 `fetch failed` warnings (thresholds fetch failed ×115, stats fetch failed ×115), from 2026-10-13T20:07:35Z → 2026-10-13T20:17:05Z. Reason text: 229× timed out; 1× <urlopen error timed out>. The CSV covers 720 s (2026-10-13T20:05:07Z → 2026-10-13T20:17:07Z). Threshold freshness stayed within 30 s on every API (longest 1 s). Admitted-rate reads went stale on all five APIs for 577 s (80.1% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 721 | 721 | 0 | 29 | 692 | 1 | 577 | 0.0% | 80.1% | caps 10×692; no-cap (10000) ×29 | min 0 / median 0 / mean 3.7 / max 24 (n=29 fresh) |
| postcheckout | 721 | 721 | 0 | 29 | 692 | 1 | 577 | 0.0% | 80.1% | caps 10×692; no-cap (10000) ×29 | min 0 / median 0 / mean 1.6 / max 10 (n=29 fresh) |
| getcart | 721 | 721 | 0 | 29 | 692 | 1 | 577 | 0.0% | 80.1% | caps 10×692; no-cap (10000) ×29 | min 0 / median 0 / mean 4.0 / max 26 (n=29 fresh) |
| postcart | 721 | 721 | 0 | 29 | 692 | 1 | 577 | 0.0% | 80.1% | caps 417.753×692; no-cap (10000) ×29 | min 0 / median 0 / mean 59.7 / max 426 (n=29 fresh) |
| emptycart | 721 | 721 | 0 | 29 | 692 | 1 | 577 | 0.0% | 80.1% | no-cap (10000) ×29; empty read (0) ×692 | min 0 / median 0 / mean 0.6 / max 4 (n=29 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 59 live-cap changes (see fresh-threshold counts)
- postcheckout: 59 live-cap changes (see fresh-threshold counts)
- getcart: 59 live-cap changes (see fresh-threshold counts)
- postcart: 59 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 20:05:10–20:07:30

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 721 | 1150 | 0.8 | 0.16 | 0.4 | 0 | 0.0% |
| checkoutservice | 721 | 800 | 0.8 | 0.041 | 0.335 | 0 | 0.0% |
| recommendationservice | 721 | 1150 | 0.8 | 0.118 | 0.378 | 0 | 0.0% |
| paymentservice | 721 | 155 | 0.8 | 0.034 | 0.342 | 0 | 0.0% |
| emailservice | 721 | 120 | 0.8 | 0.1 | 0.483 | 0 | 0.0% |
| productcatalogservice | 721 | 100 | 0.95 | 0.377 | 1.14 | 186 | 25.8% |
| cartservice | 721 | 800 | 0.95 | 0.168 | 0.575 | 0 | 0.0% |
| currencyservice | 721 | 770 | 0.8 | 0.058 | 0.179 | 0 | 0.0% |
| shippingservice | 721 | 770 | 0.8 | 0.015 | 0.094 | 0 | 0.0% |
| adservice | 721 | 1150 | 0.8 | 0.029 | 0.073 | 0 | 0.0% |
| redis-cart | 721 | 540 | 0.8 | 0.032 | 0.252 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run5`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run5` is FLAGGED with TopFull off. The collector log has 226 `fetch failed` warnings (thresholds fetch failed ×113, stats fetch failed ×113), from 2026-10-14T16:28:00Z → 2026-10-14T16:37:20Z. Reason text: 226× timed out. The CSV covers 714 s (2026-10-14T16:25:31Z → 2026-10-14T16:37:25Z). Threshold reads went stale on all five APIs for 570 s (79.8% of the span). Admitted-rate reads went stale on all five APIs for 570 s (79.8% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 715 | 30 | 685 | 30 | 685 | 570 | 570 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 5.6 / max 25 (n=30 fresh) |
| postcheckout | 715 | 30 | 685 | 30 | 685 | 570 | 570 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 2.4 / max 12 (n=30 fresh) |
| getcart | 715 | 30 | 685 | 30 | 685 | 570 | 570 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 6.2 / max 28 (n=30 fresh) |
| postcart | 715 | 30 | 685 | 30 | 685 | 570 | 570 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 90.1 / max 510 (n=30 fresh) |
| emptycart | 715 | 30 | 685 | 30 | 685 | 570 | 570 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 0.9 / max 5 (n=30 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 16:25:35–16:37:25
- postcheckout: no cap 16:25:35–16:37:25
- getcart: no cap 16:25:35–16:37:25
- postcart: no cap 16:25:35–16:37:25
- emptycart: no cap 16:25:35–16:37:25

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 715 | 1150 | 0.8 | 0.12 | 0.173 | 0 | 0.0% |
| checkoutservice | 715 | 800 | 0.8 | 0.095 | 0.349 | 0 | 0.0% |
| recommendationservice | 715 | 1150 | 0.8 | 0.106 | 0.243 | 0 | 0.0% |
| paymentservice | 715 | 155 | 0.8 | 0.035 | 0.284 | 0 | 0.0% |
| emailservice | 715 | 120 | 0.8 | 0.115 | 0.325 | 0 | 0.0% |
| productcatalogservice | 715 | 100 | 0.95 | 0.831 | 1.12 | 424 | 59.3% |
| cartservice | 715 | 800 | 0.95 | 0.218 | 0.389 | 0 | 0.0% |
| currencyservice | 715 | 770 | 0.8 | 0.084 | 0.152 | 0 | 0.0% |
| shippingservice | 715 | 770 | 0.8 | 0.02 | 0.06 | 0 | 0.0% |
| adservice | 715 | 1150 | 0.8 | 0.029 | 0.057 | 0 | 0.0% |
| redis-cart | 715 | 540 | 0.8 | 0.043 | 0.289 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run5_r2`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run5_r2` is FLAGGED with TopFull off. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-14T18:09:30Z → 2026-10-14T18:18:55Z. Reason text: 226× timed out; 2× <urlopen error timed out>. The CSV covers 719 s (2026-10-14T18:07:01Z → 2026-10-14T18:19:00Z). Threshold reads went stale on all five APIs for 575 s (80.0% of the span). Admitted-rate reads went stale on all five APIs for 575 s (80.0% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 720 | 30 | 690 | 30 | 690 | 575 | 575 | 80.0% | 80.0% | no-cap (10000) ×30 | min 0 / median 0 / mean 4.6 / max 24 (n=30 fresh) |
| postcheckout | 720 | 30 | 690 | 30 | 690 | 575 | 575 | 80.0% | 80.0% | no-cap (10000) ×30 | min 0 / median 0 / mean 2.0 / max 11 (n=30 fresh) |
| getcart | 720 | 30 | 690 | 30 | 690 | 575 | 575 | 80.0% | 80.0% | no-cap (10000) ×30 | min 0 / median 0 / mean 4.9 / max 28 (n=30 fresh) |
| postcart | 720 | 30 | 690 | 30 | 690 | 575 | 575 | 80.0% | 80.0% | no-cap (10000) ×30 | min 0 / median 0 / mean 72.7 / max 444 (n=30 fresh) |
| emptycart | 720 | 30 | 690 | 30 | 690 | 575 | 575 | 80.0% | 80.0% | no-cap (10000) ×30 | min 0 / median 0 / mean 0.7 / max 4 (n=30 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 18:07:05–18:19:00
- postcheckout: no cap 18:07:05–18:19:00
- getcart: no cap 18:07:05–18:19:00
- postcart: no cap 18:07:05–18:19:00
- emptycart: no cap 18:07:05–18:19:00

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 720 | 1150 | 0.8 | 0.122 | 0.19 | 0 | 0.0% |
| checkoutservice | 720 | 800 | 0.8 | 0.124 | 0.407 | 0 | 0.0% |
| recommendationservice | 720 | 1150 | 0.8 | 0.123 | 0.269 | 0 | 0.0% |
| paymentservice | 720 | 155 | 0.8 | 0.043 | 0.252 | 0 | 0.0% |
| emailservice | 720 | 120 | 0.8 | 0.144 | 0.408 | 0 | 0.0% |
| productcatalogservice | 720 | 100 | 0.95 | 0.83 | 1.15 | 434 | 60.3% |
| cartservice | 720 | 800 | 0.95 | 0.195 | 0.356 | 0 | 0.0% |
| currencyservice | 720 | 770 | 0.8 | 0.09 | 0.168 | 0 | 0.0% |
| shippingservice | 720 | 770 | 0.8 | 0.024 | 0.075 | 0 | 0.0% |
| adservice | 720 | 1150 | 0.8 | 0.039 | 0.064 | 0 | 0.0% |
| redis-cart | 720 | 540 | 0.8 | 0.046 | 0.32 | 0 | 0.0% |

### `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run6`

`S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run6` is FLAGGED with TopFull off. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-14T18:29:00Z → 2026-10-14T18:38:25Z. Reason text: 227× timed out; 1× <urlopen error timed out>. The CSV covers 715 s (2026-10-14T18:26:35Z → 2026-10-14T18:38:30Z). Threshold reads went stale on all five APIs for 575 s (80.4% of the span). Admitted-rate reads went stale on all five APIs for 575 s (80.4% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 5.1 / max 26 (n=30 fresh) |
| postcheckout | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 2.2 / max 11 (n=30 fresh) |
| getcart | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 5.7 / max 32 (n=30 fresh) |
| postcart | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 72.4 / max 450 (n=30 fresh) |
| emptycart | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 0.7 / max 4 (n=30 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 18:26:35–18:38:30
- postcheckout: no cap 18:26:35–18:38:30
- getcart: no cap 18:26:35–18:38:30
- postcart: no cap 18:26:35–18:38:30
- emptycart: no cap 18:26:35–18:38:30

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 716 | 1150 | 0.8 | 0.115 | 0.19 | 0 | 0.0% |
| checkoutservice | 716 | 800 | 0.8 | 0.144 | 0.37 | 0 | 0.0% |
| recommendationservice | 716 | 1150 | 0.8 | 0.109 | 0.255 | 0 | 0.0% |
| paymentservice | 716 | 155 | 0.8 | 0.047 | 0.265 | 0 | 0.0% |
| emailservice | 716 | 120 | 0.8 | 0.151 | 0.358 | 0 | 0.0% |
| productcatalogservice | 716 | 100 | 0.95 | 0.835 | 1.14 | 414 | 57.8% |
| cartservice | 716 | 800 | 0.95 | 0.188 | 0.344 | 0 | 0.0% |
| currencyservice | 716 | 770 | 0.8 | 0.081 | 0.19 | 0 | 0.0% |
| shippingservice | 716 | 770 | 0.8 | 0.026 | 0.087 | 0 | 0.0% |
| adservice | 716 | 1150 | 0.8 | 0.034 | 0.062 | 0 | 0.0% |
| redis-cart | 716 | 540 | 0.8 | 0.042 | 0.285 | 0 | 0.0% |

### `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run2_r2`

`S4A_topology_position_normal/both/final_4a_constrained_both_normal_run2_r2` is FLAGGED with TopFull on. The collector log has 192 `fetch failed` warnings (thresholds fetch failed ×96, stats fetch failed ×96), from 2026-10-13T06:16:15Z → 2026-10-13T06:24:10Z. Reason text: 191× timed out; 1× <urlopen error timed out>. The CSV covers 713 s (2026-10-13T06:12:20Z → 2026-10-13T06:24:13Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 483 s (67.7% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 714 | 549 | 165 | 47 | 667 | 5 | 483 | 0.0% | 67.7% | caps min 10 / median 9677.4 / max 9928.7 / 20 distinct / 31 fresh reads; no-cap (10000) ×27; empty read (0) ×491 | min 0 / median 3 / mean 4.4 / max 10 (n=47 fresh) |
| postcheckout | 714 | 549 | 165 | 47 | 667 | 5 | 483 | 0.0% | 67.7% | caps 10×21, 9893.17×1, 9893.2×2, 9909.1×1, 9931×1, 9971.3×1; no-cap (10000) ×28; empty read (0) ×494 | min 0 / median 3 / mean 4.4 / max 10 (n=47 fresh) |
| getcart | 714 | 549 | 165 | 47 | 667 | 5 | 483 | 0.0% | 67.7% | caps 10×32, 10.4×1; no-cap (10000) ×507; empty read (0) ×9 | min 0 / median 3 / mean 4.5 / max 10 (n=47 fresh) |
| postcart | 714 | 549 | 165 | 47 | 667 | 5 | 483 | 0.0% | 67.7% | caps min 52.2 / median 133.2 / max 694.1 / 31 distinct / 33 fresh reads; no-cap (10000) ×23; empty read (0) ×493 | min 0 / median 174 / mean 271.7 / max 616 (n=47 fresh) |
| emptycart | 714 | 549 | 165 | 47 | 667 | 5 | 483 | 0.0% | 67.7% | no-cap (10000) ×47; empty read (0) ×502 | min 0 / median 2 / mean 2.3 / max 5 (n=47 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 27 live-cap changes (see fresh-threshold counts)
- postcheckout: 15 live-cap changes (see fresh-threshold counts)
- getcart: 7 live-cap changes (see fresh-threshold counts)
- postcart: 32 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 06:12:20–06:16:10

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 714 | 1150 | 0.8 | 0.16 | 0.407 | 0 | 0.0% |
| checkoutservice | 714 | 800 | 0.8 | 0.039 | 0.354 | 0 | 0.0% |
| recommendationservice | 714 | 1150 | 0.8 | 0.045 | 0.117 | 0 | 0.0% |
| paymentservice | 714 | 155 | 0.8 | 0.034 | 0.329 | 0 | 0.0% |
| emailservice | 714 | 120 | 0.8 | 0.096 | 0.567 | 0 | 0.0% |
| productcatalogservice | 714 | 50 | 0.95 | 0.33 | 1.38 | 173 | 24.2% |
| cartservice | 714 | 800 | 0.95 | 0.069 | 0.341 | 0 | 0.0% |
| currencyservice | 714 | 770 | 0.8 | 0.02 | 0.112 | 0 | 0.0% |
| shippingservice | 714 | 770 | 0.8 | 0.011 | 0.077 | 0 | 0.0% |
| adservice | 714 | 1150 | 0.8 | 0.024 | 0.057 | 0 | 0.0% |
| redis-cart | 714 | 540 | 0.8 | 0.016 | 0.119 | 0 | 0.0% |

### `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3`

`S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3` is FLAGGED with TopFull on. The collector log has 226 `fetch failed` warnings (thresholds fetch failed ×113, stats fetch failed ×113), from 2026-10-13T17:15:30Z → 2026-10-13T17:24:50Z. Reason text: 224× timed out; 2× <urlopen error timed out>. The CSV covers 726 s (2026-10-13T17:12:50Z → 2026-10-13T17:24:56Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 570 s (78.5% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 727 | 604 | 123 | 33 | 694 | 5 | 570 | 0.0% | 78.5% | caps min 21.4 / median 23.754 / max 25.8422 / 9 distinct / 9 fresh reads; no-cap (10000) ×28; empty read (0) ×567 | min 0 / median 0 / mean 6.3 / max 42 (n=33 fresh) |
| postcheckout | 727 | 604 | 123 | 33 | 694 | 5 | 570 | 0.0% | 78.5% | caps 10×5, 10.0988×1, 10.2×1; no-cap (10000) ×28; empty read (0) ×569 | min 0 / median 0 / mean 2.6 / max 17 (n=33 fresh) |
| getcart | 727 | 604 | 123 | 33 | 694 | 5 | 570 | 0.0% | 78.5% | caps 15.5×1, 15.5314×564, 19.8×1, 21.69×2, 21.7×1, 22.2×1, 23.598×1, 23.6×1; no-cap (10000) ×28; empty read (0) ×4 | min 0 / median 0 / mean 6.6 / max 42 (n=33 fresh) |
| postcart | 727 | 604 | 123 | 33 | 694 | 5 | 570 | 0.0% | 78.5% | caps min 269.69 / median 354.578 / max 356.666 / 9 distinct / 574 fresh reads; no-cap (10000) ×28; empty read (0) ×2 | min 0 / median 0 / mean 82.8 / max 510 (n=33 fresh) |
| emptycart | 727 | 604 | 123 | 33 | 694 | 5 | 570 | 0.0% | 78.5% | no-cap (10000) ×33; empty read (0) ×571 | min 0 / median 0 / mean 0.8 / max 5 (n=33 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 10 live-cap changes (see fresh-threshold counts)
- postcheckout: no cap 17:12:50–17:15:05; 10.0988 at 17:15:07; 10.2 at 17:15:10; 10 17:15:15–17:24:55
- getcart: 10 live-cap changes (see fresh-threshold counts)
- postcart: 10 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 17:12:50–17:24:55

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 727 | 1150 | 0.8 | 0.113 | 0.286 | 0 | 0.0% |
| checkoutservice | 727 | 800 | 0.8 | 0.087 | 0.389 | 0 | 0.0% |
| recommendationservice | 727 | 1150 | 0.8 | 0.106 | 0.297 | 0 | 0.0% |
| paymentservice | 727 | 155 | 0.8 | 0.045 | 0.329 | 0 | 0.0% |
| emailservice | 727 | 120 | 0.8 | 0.128 | 0.567 | 0 | 0.0% |
| productcatalogservice | 727 | 100 | 0.95 | 0.494 | 1.09 | 254 | 34.9% |
| cartservice | 727 | 800 | 0.95 | 0.155 | 0.472 | 0 | 0.0% |
| currencyservice | 727 | 770 | 0.8 | 0.06 | 0.205 | 0 | 0.0% |
| shippingservice | 727 | 770 | 0.8 | 0.02 | 0.094 | 0 | 0.0% |
| adservice | 727 | 1150 | 0.8 | 0.031 | 0.085 | 0 | 0.0% |
| redis-cart | 727 | 540 | 0.8 | 0.033 | 0.196 | 0 | 0.0% |

### `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3_r2`

`S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3_r2` is FLAGGED with TopFull on. The collector log has 224 `fetch failed` warnings (thresholds fetch failed ×112, stats fetch failed ×112), from 2026-10-13T17:37:45Z → 2026-10-13T17:47:00Z. Reason text: 223× timed out; 1× <urlopen error timed out>. The CSV covers 722 s (2026-10-13T17:35:02Z → 2026-10-13T17:47:04Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 564 s (78.1% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 723 | 597 | 126 | 32 | 691 | 5 | 564 | 0.0% | 78.1% | caps 10×1, 11.2×2, 11.8×1, 16×2, 18.2×1; no-cap (10000) ×25; empty read (0) ×565 | min 0 / median 0 / mean 7.8 / max 48 (n=32 fresh) |
| postcheckout | 723 | 597 | 126 | 32 | 691 | 5 | 564 | 0.0% | 78.1% | caps 10×3, 10.3206×1, 10.6846×1, 10.7×1, 11×1, 11.2×2; no-cap (10000) ×27; empty read (0) ×561 | min 0 / median 0 / mean 3.4 / max 20 (n=32 fresh) |
| getcart | 723 | 597 | 126 | 32 | 691 | 5 | 564 | 0.0% | 78.1% | caps 10×559, 11.2×2, 15.4×1, 15.9×1, 18×2; no-cap (10000) ×25; empty read (0) ×7 | min 0 / median 0 / mean 8.1 / max 48 (n=32 fresh) |
| postcart | 723 | 597 | 126 | 32 | 691 | 5 | 564 | 0.0% | 78.1% | caps min 210 / median 371.783 / max 471.051 / 9 distinct / 10 fresh reads; no-cap (10000) ×25; empty read (0) ×562 | min 0 / median 0 / mean 97.5 / max 582 (n=32 fresh) |
| emptycart | 723 | 597 | 126 | 32 | 691 | 5 | 564 | 0.0% | 78.1% | no-cap (10000) ×32; empty read (0) ×565 | min 0 / median 0 / mean 0.9 / max 5 (n=32 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 17:35:05–17:37:05; 16 17:37:10–17:37:15; 11.8 at 17:37:20; 18.2 at 17:37:25; 10 at 17:37:30; 11.2 17:37:35–17:37:40
- postcheckout: 9 live-cap changes (see fresh-threshold counts)
- getcart: 7 live-cap changes (see fresh-threshold counts)
- postcart: 11 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 17:35:05–17:37:40

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 723 | 1150 | 0.8 | 0.116 | 0.22 | 0 | 0.0% |
| checkoutservice | 723 | 800 | 0.8 | 0.086 | 0.451 | 0 | 0.0% |
| recommendationservice | 723 | 1150 | 0.8 | 0.054 | 0.189 | 0 | 0.0% |
| paymentservice | 723 | 155 | 0.8 | 0.048 | 0.323 | 0 | 0.0% |
| emailservice | 723 | 120 | 0.8 | 0.129 | 0.533 | 0 | 0.0% |
| productcatalogservice | 723 | 100 | 0.95 | 0.327 | 1.13 | 164 | 22.7% |
| cartservice | 723 | 800 | 0.95 | 0.112 | 0.472 | 0 | 0.0% |
| currencyservice | 723 | 770 | 0.8 | 0.035 | 0.134 | 0 | 0.0% |
| shippingservice | 723 | 770 | 0.8 | 0.017 | 0.09 | 0 | 0.0% |
| adservice | 723 | 1150 | 0.8 | 0.028 | 0.062 | 0 | 0.0% |
| redis-cart | 723 | 540 | 0.8 | 0.027 | 0.193 | 0 | 0.0% |

### `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run4`

`S4A_topology_position_normal/both/final_4a_constrained_both_normal_run4` is FLAGGED with TopFull on. The collector log has 226 `fetch failed` warnings (thresholds fetch failed ×113, stats fetch failed ×113), from 2026-10-13T17:58:00Z → 2026-10-13T18:07:20Z. Reason text: 224× timed out; 2× <urlopen error timed out>. The CSV covers 722 s (2026-10-13T17:55:21Z → 2026-10-13T18:07:23Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 568 s (78.7% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 723 | 601 | 122 | 31 | 692 | 5 | 568 | 0.0% | 78.7% | caps 11.9171×566, 12.3×2, 12.3412×1, 13.2×1, 16×1, 18.9×1, 19.2693×1, 19.3×1; no-cap (10000) ×25; empty read (0) ×2 | min 0 / median 0 / mean 6.8 / max 43 (n=31 fresh) |
| postcheckout | 723 | 601 | 122 | 31 | 692 | 5 | 568 | 0.0% | 78.7% | caps 10×573; no-cap (10000) ×25; empty read (0) ×3 | min 0 / median 0 / mean 2.8 / max 18 (n=31 fresh) |
| getcart | 723 | 601 | 122 | 31 | 692 | 5 | 568 | 0.0% | 78.7% | caps 12.4×2, 12.4279×1, 13.3×1, 17.5969×1, 17.6×1, 18×1, 18.989×1, 19×1; no-cap (10000) ×25; empty read (0) ×567 | min 0 / median 0 / mean 7.1 / max 44 (n=31 fresh) |
| postcart | 723 | 601 | 122 | 31 | 692 | 5 | 568 | 0.0% | 78.7% | caps 210×1, 268.488×1, 268.5×2, 362.363×1, 362.4×1, 363.2×1, 466.5×1, 466.507×566; no-cap (10000) ×25; empty read (0) ×2 | min 0 / median 0 / mean 85.5 / max 534 (n=31 fresh) |
| emptycart | 723 | 601 | 122 | 31 | 692 | 5 | 568 | 0.0% | 78.7% | no-cap (10000) ×31; empty read (0) ×570 | min 0 / median 0 / mean 0.8 / max 5 (n=31 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 9 live-cap changes (see fresh-threshold counts)
- postcheckout: no cap 17:55:25–17:57:25; 10 17:57:30–18:07:21
- getcart: 9 live-cap changes (see fresh-threshold counts)
- postcart: 10 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 17:55:25–17:57:55

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 723 | 1150 | 0.8 | 0.127 | 0.291 | 0 | 0.0% |
| checkoutservice | 723 | 800 | 0.8 | 0.099 | 0.444 | 0 | 0.0% |
| recommendationservice | 723 | 1150 | 0.8 | 0.059 | 0.144 | 0 | 0.0% |
| paymentservice | 723 | 155 | 0.8 | 0.052 | 0.323 | 0 | 0.0% |
| emailservice | 723 | 120 | 0.8 | 0.137 | 0.533 | 0 | 0.0% |
| productcatalogservice | 723 | 100 | 0.95 | 0.389 | 1.17 | 187 | 25.9% |
| cartservice | 723 | 800 | 0.95 | 0.119 | 0.45 | 0 | 0.0% |
| currencyservice | 723 | 770 | 0.8 | 0.04 | 0.126 | 0 | 0.0% |
| shippingservice | 723 | 770 | 0.8 | 0.019 | 0.087 | 0 | 0.0% |
| adservice | 723 | 1150 | 0.8 | 0.028 | 0.07 | 0 | 0.0% |
| redis-cart | 723 | 540 | 0.8 | 0.031 | 0.239 | 0 | 0.0% |

### `S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run1_r2`

`S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run1_r2` is FLAGGED with TopFull on. The collector log has 200 `fetch failed` warnings (thresholds fetch failed ×100, stats fetch failed ×100), from 2026-10-14T00:42:00Z → 2026-10-14T00:50:15Z. Reason text: 199× timed out; 1× <urlopen error timed out>. The CSV covers 718 s (2026-10-14T00:38:23Z → 2026-10-14T00:50:21Z). Threshold reads went stale on all five APIs for 505 s (70.3% of the span). Admitted-rate reads went stale on all five APIs for 505 s (70.3% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 719 | 44 | 675 | 44 | 675 | 505 | 505 | 70.3% | 70.3% | no-cap (10000) ×44 | min 0 / median 4 / mean 19.6 / max 50 (n=44 fresh) |
| postcheckout | 719 | 44 | 675 | 44 | 675 | 505 | 505 | 70.3% | 70.3% | no-cap (10000) ×44 | min 0 / median 2 / mean 8.0 / max 20 (n=44 fresh) |
| getcart | 719 | 44 | 675 | 44 | 675 | 505 | 505 | 70.3% | 70.3% | no-cap (10000) ×44 | min 0 / median 5 / mean 19.9 / max 52 (n=44 fresh) |
| postcart | 719 | 44 | 675 | 44 | 675 | 505 | 505 | 70.3% | 70.3% | no-cap (10000) ×44 | min 0 / median 56 / mean 236.2 / max 603 (n=44 fresh) |
| emptycart | 719 | 44 | 675 | 44 | 675 | 505 | 505 | 70.3% | 70.3% | no-cap (10000) ×44 | min 0 / median 1 / mean 2.1 / max 5 (n=44 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 00:38:25–00:50:20
- postcheckout: no cap 00:38:25–00:50:20
- getcart: no cap 00:38:25–00:50:20
- postcart: no cap 00:38:25–00:50:20
- emptycart: no cap 00:38:25–00:50:20

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 719 | 1150 | 0.8 | 0.197 | 0.318 | 0 | 0.0% |
| checkoutservice | 719 | 800 | 0.8 | 0.378 | 0.635 | 0 | 0.0% |
| recommendationservice | 719 | 1150 | 0.8 | 0.175 | 0.317 | 0 | 0.0% |
| paymentservice | 719 | 155 | 0.8 | 0.132 | 0.394 | 0 | 0.0% |
| emailservice | 719 | 120 | 0.8 | 0.34 | 0.767 | 0 | 0.0% |
| productcatalogservice | 719 | 800 | 0.95 | 0.303 | 0.463 | 0 | 0.0% |
| cartservice | 719 | 800 | 0.95 | 0.515 | 0.882 | 0 | 0.0% |
| currencyservice | 719 | 770 | 0.8 | 0.155 | 0.31 | 0 | 0.0% |
| shippingservice | 719 | 770 | 0.8 | 0.061 | 0.14 | 0 | 0.0% |
| adservice | 719 | 1150 | 0.8 | 0.047 | 0.094 | 0 | 0.0% |
| redis-cart | 719 | 540 | 0.8 | 0.078 | 0.431 | 0 | 0.0% |

### `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1`

`S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1` is FLAGGED with TopFull off. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T04:05:05Z → 2026-10-13T04:14:30Z. Reason text: 227× timed out; 1× <urlopen error timed out>. The CSV covers 711 s (2026-10-13T04:02:44Z → 2026-10-13T04:14:35Z). Threshold reads went stale on all five APIs for 575 s (80.9% of the span). Admitted-rate reads went stale on all five APIs for 575 s (80.9% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 712 | 29 | 683 | 29 | 683 | 575 | 575 | 80.9% | 80.9% | no-cap (10000) ×29 | min 0 / median 0 / mean 1.1 / max 5 (n=29 fresh) |
| postcheckout | 712 | 29 | 683 | 29 | 683 | 575 | 575 | 80.9% | 80.9% | no-cap (10000) ×29 | min 0 / median 0 / mean 1.1 / max 5 (n=29 fresh) |
| getcart | 712 | 29 | 683 | 29 | 683 | 575 | 575 | 80.9% | 80.9% | no-cap (10000) ×29 | min 0 / median 0 / mean 1.2 / max 6 (n=29 fresh) |
| postcart | 712 | 29 | 683 | 29 | 683 | 575 | 575 | 80.9% | 80.9% | no-cap (10000) ×29 | min 0 / median 0 / mean 64.2 / max 340 (n=29 fresh) |
| emptycart | 712 | 29 | 683 | 29 | 683 | 575 | 575 | 80.9% | 80.9% | no-cap (10000) ×29 | min 0 / median 0 / mean 0.8 / max 4 (n=29 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 04:02:45–04:14:35
- postcheckout: no cap 04:02:45–04:14:35
- getcart: no cap 04:02:45–04:14:35
- postcart: no cap 04:02:45–04:14:35
- emptycart: no cap 04:02:45–04:14:35

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 712 | 1150 | 0.8 | 0.136 | 0.319 | 0 | 0.0% |
| checkoutservice | 712 | 800 | 0.8 | 0.013 | 0.199 | 0 | 0.0% |
| recommendationservice | 712 | 1150 | 0.8 | 0.04 | 0.146 | 0 | 0.0% |
| paymentservice | 712 | 155 | 0.8 | 0.027 | 0.316 | 0 | 0.0% |
| emailservice | 712 | 120 | 0.8 | 0.082 | 0.375 | 0 | 0.0% |
| productcatalogservice | 712 | 50 | 0.95 | 0.323 | 1.32 | 166 | 23.3% |
| cartservice | 712 | 800 | 0.95 | 0.066 | 0.374 | 0 | 0.0% |
| currencyservice | 712 | 770 | 0.8 | 0.015 | 0.077 | 0 | 0.0% |
| shippingservice | 712 | 770 | 0.8 | 0.009 | 0.061 | 0 | 0.0% |
| adservice | 712 | 1150 | 0.8 | 0.024 | 0.057 | 0 | 0.0% |
| redis-cart | 712 | 540 | 0.8 | 0.016 | 0.07 | 0 | 0.0% |

### `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1_r2`

`S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1_r2` is FLAGGED with TopFull off. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T04:23:30Z → 2026-10-13T04:32:55Z. Reason text: 228× timed out. The CSV covers 715 s (2026-10-13T04:21:05Z → 2026-10-13T04:33:00Z). Threshold reads went stale on all five APIs for 575 s (80.4% of the span). Admitted-rate reads went stale on all five APIs for 575 s (80.4% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 1.1 / max 5 (n=30 fresh) |
| postcheckout | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 1.1 / max 5 (n=30 fresh) |
| getcart | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 1.3 / max 7 (n=30 fresh) |
| postcart | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 70.5 / max 430 (n=30 fresh) |
| emptycart | 716 | 30 | 686 | 30 | 686 | 575 | 575 | 80.4% | 80.4% | no-cap (10000) ×30 | min 0 / median 0 / mean 0.7 / max 4 (n=30 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 04:21:05–04:33:00
- postcheckout: no cap 04:21:05–04:33:00
- getcart: no cap 04:21:05–04:33:00
- postcart: no cap 04:21:05–04:33:00
- emptycart: no cap 04:21:05–04:33:00

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 716 | 1150 | 0.8 | 0.143 | 0.525 | 0 | 0.0% |
| checkoutservice | 716 | 800 | 0.8 | 0.012 | 0.189 | 0 | 0.0% |
| recommendationservice | 716 | 1150 | 0.8 | 0.041 | 0.083 | 0 | 0.0% |
| paymentservice | 716 | 155 | 0.8 | 0.031 | 0.303 | 0 | 0.0% |
| emailservice | 716 | 120 | 0.8 | 0.081 | 0.467 | 0 | 0.0% |
| productcatalogservice | 716 | 50 | 0.95 | 0.338 | 1.26 | 183 | 25.6% |
| cartservice | 716 | 800 | 0.95 | 0.049 | 0.333 | 0 | 0.0% |
| currencyservice | 716 | 770 | 0.8 | 0.016 | 0.075 | 0 | 0.0% |
| shippingservice | 716 | 770 | 0.8 | 0.01 | 0.056 | 0 | 0.0% |
| adservice | 716 | 1150 | 0.8 | 0.024 | 0.062 | 0 | 0.0% |
| redis-cart | 716 | 540 | 0.8 | 0.016 | 0.078 | 0 | 0.0% |

### `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2`

`S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2` is FLAGGED with TopFull off. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T04:44:20Z → 2026-10-13T04:53:45Z. Reason text: 228× timed out. The CSV covers 710 s (2026-10-13T04:42:01Z → 2026-10-13T04:53:51Z). Threshold reads went stale on all five APIs for 575 s (81.0% of the span). Admitted-rate reads went stale on all five APIs for 575 s (81.0% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 711 | 28 | 683 | 28 | 683 | 575 | 575 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 1.0 / max 5 (n=28 fresh) |
| postcheckout | 711 | 28 | 683 | 28 | 683 | 575 | 575 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 1.1 / max 6 (n=28 fresh) |
| getcart | 711 | 28 | 683 | 28 | 683 | 575 | 575 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 1.1 / max 6 (n=28 fresh) |
| postcart | 711 | 28 | 683 | 28 | 683 | 575 | 575 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 65.2 / max 357 (n=28 fresh) |
| emptycart | 711 | 28 | 683 | 28 | 683 | 575 | 575 | 81.0% | 81.0% | no-cap (10000) ×28 | min 0 / median 0 / mean 0.8 / max 4 (n=28 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 04:42:05–04:53:50
- postcheckout: no cap 04:42:05–04:53:50
- getcart: no cap 04:42:05–04:53:50
- postcart: no cap 04:42:05–04:53:50
- emptycart: no cap 04:42:05–04:53:50

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 711 | 1150 | 0.8 | 0.152 | 0.347 | 0 | 0.0% |
| checkoutservice | 711 | 800 | 0.8 | 0.012 | 0.147 | 0 | 0.0% |
| recommendationservice | 711 | 1150 | 0.8 | 0.04 | 0.09 | 0 | 0.0% |
| paymentservice | 711 | 155 | 0.8 | 0.028 | 0.29 | 0 | 0.0% |
| emailservice | 711 | 120 | 0.8 | 0.083 | 0.425 | 0 | 0.0% |
| productcatalogservice | 711 | 50 | 0.95 | 0.301 | 1.38 | 157 | 22.1% |
| cartservice | 711 | 800 | 0.95 | 0.053 | 0.266 | 0 | 0.0% |
| currencyservice | 711 | 770 | 0.8 | 0.016 | 0.071 | 0 | 0.0% |
| shippingservice | 711 | 770 | 0.8 | 0.009 | 0.064 | 0 | 0.0% |
| adservice | 711 | 1150 | 0.8 | 0.024 | 0.063 | 0 | 0.0% |
| redis-cart | 711 | 540 | 0.8 | 0.016 | 0.1 | 0 | 0.0% |

### `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2_r2`

`S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2_r2` is FLAGGED with TopFull off. The collector log has 230 `fetch failed` warnings (thresholds fetch failed ×115, stats fetch failed ×115), from 2026-10-13T05:02:20Z → 2026-10-13T05:11:50Z. Reason text: 230× timed out. The CSV covers 710 s (2026-10-13T05:00:03Z → 2026-10-13T05:11:53Z). Threshold reads went stale on all five APIs for 578 s (81.4% of the span). Admitted-rate reads went stale on all five APIs for 578 s (81.4% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 711 | 27 | 684 | 27 | 684 | 578 | 578 | 81.4% | 81.4% | no-cap (10000) ×27 | min 0 / median 0 / mean 0.8 / max 5 (n=27 fresh) |
| postcheckout | 711 | 27 | 684 | 27 | 684 | 578 | 578 | 81.4% | 81.4% | no-cap (10000) ×27 | min 0 / median 0 / mean 0.8 / max 5 (n=27 fresh) |
| getcart | 711 | 27 | 684 | 27 | 684 | 578 | 578 | 81.4% | 81.4% | no-cap (10000) ×27 | min 0 / median 0 / mean 0.8 / max 5 (n=27 fresh) |
| postcart | 711 | 27 | 684 | 27 | 684 | 578 | 578 | 81.4% | 81.4% | no-cap (10000) ×27 | min 0 / median 0 / mean 52.3 / max 339 (n=27 fresh) |
| emptycart | 711 | 27 | 684 | 27 | 684 | 578 | 578 | 81.4% | 81.4% | no-cap (10000) ×27 | min 0 / median 0 / mean 0.6 / max 4 (n=27 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 05:00:05–05:02:15
- postcheckout: no cap 05:00:05–05:02:15
- getcart: no cap 05:00:05–05:02:15
- postcart: no cap 05:00:05–05:02:15
- emptycart: no cap 05:00:05–05:02:15

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 711 | 1150 | 0.8 | 0.146 | 0.356 | 0 | 0.0% |
| checkoutservice | 711 | 800 | 0.8 | 0.009 | 0.174 | 0 | 0.0% |
| recommendationservice | 711 | 1150 | 0.8 | 0.044 | 0.49 | 0 | 0.0% |
| paymentservice | 711 | 155 | 0.8 | 0.028 | 0.323 | 0 | 0.0% |
| emailservice | 711 | 120 | 0.8 | 0.077 | 0.433 | 0 | 0.0% |
| productcatalogservice | 711 | 50 | 0.95 | 0.324 | 1.42 | 162 | 22.8% |
| cartservice | 711 | 800 | 0.95 | 0.046 | 0.263 | 0 | 0.0% |
| currencyservice | 711 | 770 | 0.8 | 0.016 | 0.084 | 0 | 0.0% |
| shippingservice | 711 | 770 | 0.8 | 0.008 | 0.06 | 0 | 0.0% |
| adservice | 711 | 1150 | 0.8 | 0.025 | 0.059 | 0 | 0.0% |
| redis-cart | 711 | 540 | 0.8 | 0.015 | 0.078 | 0 | 0.0% |

### `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3`

`S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3` is FLAGGED with TopFull off. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T15:19:25Z → 2026-10-13T15:28:50Z. Reason text: 226× timed out; 2× <urlopen error timed out>. The CSV covers 721 s (2026-10-13T15:16:57Z → 2026-10-13T15:28:58Z). Threshold reads went stale on all five APIs for 575 s (79.8% of the span). Admitted-rate reads went stale on all five APIs for 575 s (79.8% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 722 | 30 | 692 | 30 | 692 | 575 | 575 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 4.8 / max 38 (n=30 fresh) |
| postcheckout | 722 | 30 | 692 | 30 | 692 | 575 | 575 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 2.1 / max 15 (n=30 fresh) |
| getcart | 722 | 30 | 692 | 30 | 692 | 575 | 575 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 5.4 / max 39 (n=30 fresh) |
| postcart | 722 | 30 | 692 | 30 | 692 | 575 | 575 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 68.9 / max 456 (n=30 fresh) |
| emptycart | 722 | 30 | 692 | 30 | 692 | 575 | 575 | 79.8% | 79.8% | no-cap (10000) ×30 | min 0 / median 0 / mean 0.7 / max 4 (n=30 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 15:17:00–15:28:55
- postcheckout: no cap 15:17:00–15:28:55
- getcart: no cap 15:17:00–15:28:55
- postcart: no cap 15:17:00–15:28:55
- emptycart: no cap 15:17:00–15:28:55

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 722 | 1150 | 0.8 | 0.13 | 0.24 | 0 | 0.0% |
| checkoutservice | 722 | 800 | 0.8 | 0.042 | 0.369 | 0 | 0.0% |
| recommendationservice | 722 | 1150 | 0.8 | 0.116 | 0.271 | 0 | 0.0% |
| paymentservice | 722 | 155 | 0.8 | 0.036 | 0.361 | 0 | 0.0% |
| emailservice | 722 | 120 | 0.8 | 0.095 | 0.55 | 0 | 0.0% |
| productcatalogservice | 722 | 100 | 0.95 | 0.375 | 1.15 | 191 | 26.5% |
| cartservice | 722 | 800 | 0.95 | 0.152 | 0.474 | 0 | 0.0% |
| currencyservice | 722 | 770 | 0.8 | 0.054 | 0.169 | 0 | 0.0% |
| shippingservice | 722 | 770 | 0.8 | 0.014 | 0.081 | 0 | 0.0% |
| adservice | 722 | 1150 | 0.8 | 0.028 | 0.067 | 0 | 0.0% |
| redis-cart | 722 | 540 | 0.8 | 0.03 | 0.181 | 0 | 0.0% |

### `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3_r2`

`S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3_r2` is FLAGGED with TopFull off. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T15:39:30Z → 2026-10-13T15:48:55Z. Reason text: 226× timed out; 2× <urlopen error timed out>. The CSV covers 725 s (2026-10-13T15:36:55Z → 2026-10-13T15:49:00Z). Threshold reads went stale on all five APIs for 575 s (79.3% of the span). Admitted-rate reads went stale on all five APIs for 575 s (79.3% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 726 | 32 | 694 | 32 | 694 | 575 | 575 | 79.3% | 79.3% | no-cap (10000) ×32 | min 0 / median 0 / mean 4.1 / max 26 (n=32 fresh) |
| postcheckout | 726 | 32 | 694 | 32 | 694 | 575 | 575 | 79.3% | 79.3% | no-cap (10000) ×32 | min 0 / median 0 / mean 1.8 / max 11 (n=32 fresh) |
| getcart | 726 | 32 | 694 | 32 | 694 | 575 | 575 | 79.3% | 79.3% | no-cap (10000) ×32 | min 0 / median 0 / mean 4.7 / max 27 (n=32 fresh) |
| postcart | 726 | 32 | 694 | 32 | 694 | 575 | 575 | 79.3% | 79.3% | no-cap (10000) ×32 | min 0 / median 0 / mean 67.0 / max 455 (n=32 fresh) |
| emptycart | 726 | 32 | 694 | 32 | 694 | 575 | 575 | 79.3% | 79.3% | no-cap (10000) ×32 | min 0 / median 0 / mean 0.7 / max 4 (n=32 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 15:36:55–15:49:00
- postcheckout: no cap 15:36:55–15:49:00
- getcart: no cap 15:36:55–15:49:00
- postcart: no cap 15:36:55–15:49:00
- emptycart: no cap 15:36:55–15:49:00

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 726 | 1150 | 0.8 | 0.132 | 0.237 | 0 | 0.0% |
| checkoutservice | 726 | 800 | 0.8 | 0.046 | 0.305 | 0 | 0.0% |
| recommendationservice | 726 | 1150 | 0.8 | 0.12 | 0.346 | 0 | 0.0% |
| paymentservice | 726 | 155 | 0.8 | 0.035 | 0.303 | 0 | 0.0% |
| emailservice | 726 | 120 | 0.8 | 0.103 | 0.5 | 0 | 0.0% |
| productcatalogservice | 726 | 100 | 0.95 | 0.436 | 1.21 | 216 | 29.8% |
| cartservice | 726 | 800 | 0.95 | 0.201 | 0.595 | 0 | 0.0% |
| currencyservice | 726 | 770 | 0.8 | 0.06 | 0.178 | 0 | 0.0% |
| shippingservice | 726 | 770 | 0.8 | 0.014 | 0.075 | 0 | 0.0% |
| adservice | 726 | 1150 | 0.8 | 0.027 | 0.085 | 0 | 0.0% |
| redis-cart | 726 | 540 | 0.8 | 0.033 | 0.178 | 0 | 0.0% |

### `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4`

`S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4` is FLAGGED with TopFull off. The collector log has 230 `fetch failed` warnings (thresholds fetch failed ×115, stats fetch failed ×115), from 2026-10-13T15:59:00Z → 2026-10-13T16:08:30Z. Reason text: 227× timed out; 3× <urlopen error timed out>. The CSV covers 722 s (2026-10-13T15:56:31Z → 2026-10-13T16:08:33Z). Threshold reads went stale on all five APIs for 578 s (80.1% of the span). Admitted-rate reads went stale on all five APIs for 578 s (80.1% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 723 | 29 | 694 | 29 | 694 | 578 | 578 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 4.1 / max 28 (n=29 fresh) |
| postcheckout | 723 | 29 | 694 | 29 | 694 | 578 | 578 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 1.7 / max 12 (n=29 fresh) |
| getcart | 723 | 29 | 694 | 29 | 694 | 578 | 578 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 4.4 / max 29 (n=29 fresh) |
| postcart | 723 | 29 | 694 | 29 | 694 | 578 | 578 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 55.9 / max 395 (n=29 fresh) |
| emptycart | 723 | 29 | 694 | 29 | 694 | 578 | 578 | 80.1% | 80.1% | no-cap (10000) ×29 | min 0 / median 0 / mean 0.6 / max 4 (n=29 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 15:56:35–15:58:55
- postcheckout: no cap 15:56:35–15:58:55
- getcart: no cap 15:56:35–15:58:55
- postcart: no cap 15:56:35–15:58:55
- emptycart: no cap 15:56:35–15:58:55

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 723 | 1150 | 0.8 | 0.131 | 0.208 | 0 | 0.0% |
| checkoutservice | 723 | 800 | 0.8 | 0.043 | 0.324 | 0 | 0.0% |
| recommendationservice | 723 | 1150 | 0.8 | 0.116 | 0.296 | 0 | 0.0% |
| paymentservice | 723 | 155 | 0.8 | 0.033 | 0.303 | 0 | 0.0% |
| emailservice | 723 | 120 | 0.8 | 0.098 | 0.525 | 0 | 0.0% |
| productcatalogservice | 723 | 100 | 0.95 | 0.344 | 1.08 | 177 | 24.5% |
| cartservice | 723 | 800 | 0.95 | 0.15 | 0.464 | 0 | 0.0% |
| currencyservice | 723 | 770 | 0.8 | 0.058 | 0.195 | 0 | 0.0% |
| shippingservice | 723 | 770 | 0.8 | 0.014 | 0.092 | 0 | 0.0% |
| adservice | 723 | 1150 | 0.8 | 0.026 | 0.061 | 0 | 0.0% |
| redis-cart | 723 | 540 | 0.8 | 0.03 | 0.206 | 0 | 0.0% |

### `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4_r2`

`S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4_r2` is FLAGGED with TopFull off. The collector log has 230 `fetch failed` warnings (thresholds fetch failed ×115, stats fetch failed ×115), from 2026-10-13T16:40:40Z → 2026-10-13T16:50:10Z. Reason text: 229× timed out; 1× <urlopen error timed out>. The CSV covers 722 s (2026-10-13T16:38:14Z → 2026-10-13T16:50:16Z). Threshold reads went stale on all five APIs for 580 s (80.3% of the span). Admitted-rate reads went stale on all five APIs for 580 s (80.3% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 723 | 30 | 693 | 30 | 693 | 580 | 580 | 80.3% | 80.3% | no-cap (10000) ×30 | min 0 / median 0 / mean 4.1 / max 29 (n=30 fresh) |
| postcheckout | 723 | 30 | 693 | 30 | 693 | 580 | 580 | 80.3% | 80.3% | no-cap (10000) ×30 | min 0 / median 0 / mean 1.7 / max 12 (n=30 fresh) |
| getcart | 723 | 30 | 693 | 30 | 693 | 580 | 580 | 80.3% | 80.3% | no-cap (10000) ×30 | min 0 / median 0 / mean 4.6 / max 28 (n=30 fresh) |
| postcart | 723 | 30 | 693 | 30 | 693 | 580 | 580 | 80.3% | 80.3% | no-cap (10000) ×30 | min 0 / median 0 / mean 57.3 / max 378 (n=30 fresh) |
| emptycart | 723 | 30 | 693 | 30 | 693 | 580 | 580 | 80.3% | 80.3% | no-cap (10000) ×30 | min 0 / median 0 / mean 0.6 / max 4 (n=30 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 16:38:15–16:50:15
- postcheckout: no cap 16:38:15–16:50:15
- getcart: no cap 16:38:15–16:50:15
- postcart: no cap 16:38:15–16:50:15
- emptycart: no cap 16:38:15–16:50:15

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 723 | 1150 | 0.8 | 0.123 | 0.228 | 0 | 0.0% |
| checkoutservice | 723 | 800 | 0.8 | 0.052 | 0.383 | 0 | 0.0% |
| recommendationservice | 723 | 1150 | 0.8 | 0.108 | 0.344 | 0 | 0.0% |
| paymentservice | 723 | 155 | 0.8 | 0.037 | 0.303 | 0 | 0.0% |
| emailservice | 723 | 120 | 0.8 | 0.106 | 0.45 | 0 | 0.0% |
| productcatalogservice | 723 | 100 | 0.95 | 0.424 | 1.11 | 223 | 30.8% |
| cartservice | 723 | 800 | 0.95 | 0.149 | 0.479 | 0 | 0.0% |
| currencyservice | 723 | 770 | 0.8 | 0.057 | 0.177 | 0 | 0.0% |
| shippingservice | 723 | 770 | 0.8 | 0.015 | 0.086 | 0 | 0.0% |
| adservice | 723 | 1150 | 0.8 | 0.028 | 0.07 | 0 | 0.0% |
| redis-cart | 723 | 540 | 0.8 | 0.032 | 0.217 | 0 | 0.0% |

### `S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run2`

`S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run2` is FLAGGED with TopFull off. The collector log has 144 `fetch failed` warnings (thresholds fetch failed ×72, stats fetch failed ×72), from 2026-10-13T22:26:35Z → 2026-10-13T22:32:30Z. Reason text: 144× timed out. The CSV covers 742 s (2026-10-13T22:20:14Z → 2026-10-13T22:32:36Z). Threshold reads went stale on all five APIs for 365 s (49.2% of the span). Admitted-rate reads went stale on all five APIs for 365 s (49.2% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 743 | 77 | 666 | 77 | 666 | 365 | 365 | 49.2% | 49.2% | no-cap (10000) ×77 | min 0 / median 50 / mean 29.5 / max 50 (n=77 fresh) |
| postcheckout | 743 | 77 | 666 | 77 | 666 | 365 | 365 | 49.2% | 49.2% | no-cap (10000) ×77 | min 0 / median 20 / mean 11.8 / max 20 (n=77 fresh) |
| getcart | 743 | 77 | 666 | 77 | 666 | 365 | 365 | 49.2% | 49.2% | no-cap (10000) ×77 | min 0 / median 50 / mean 29.6 / max 50 (n=77 fresh) |
| postcart | 743 | 77 | 666 | 77 | 666 | 365 | 365 | 49.2% | 49.2% | no-cap (10000) ×77 | min 0 / median 588 / mean 354.2 / max 627 (n=77 fresh) |
| emptycart | 743 | 77 | 666 | 77 | 666 | 365 | 365 | 49.2% | 49.2% | no-cap (10000) ×77 | min 0 / median 5 / mean 3.0 / max 5 (n=77 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 22:20:15–22:32:35
- postcheckout: no cap 22:20:15–22:32:35
- getcart: no cap 22:20:15–22:32:35
- postcart: no cap 22:20:15–22:32:35
- emptycart: no cap 22:20:15–22:32:35

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 743 | 1150 | 0.8 | 0.203 | 0.297 | 0 | 0.0% |
| checkoutservice | 743 | 800 | 0.8 | 0.356 | 0.616 | 0 | 0.0% |
| recommendationservice | 743 | 1150 | 0.8 | 0.193 | 0.369 | 0 | 0.0% |
| paymentservice | 743 | 155 | 0.8 | 0.127 | 0.484 | 0 | 0.0% |
| emailservice | 743 | 120 | 0.8 | 0.332 | 0.775 | 0 | 0.0% |
| productcatalogservice | 743 | 800 | 0.95 | 0.308 | 0.516 | 0 | 0.0% |
| cartservice | 743 | 800 | 0.95 | 0.512 | 0.895 | 0 | 0.0% |
| currencyservice | 743 | 770 | 0.8 | 0.157 | 0.284 | 0 | 0.0% |
| shippingservice | 743 | 770 | 0.8 | 0.06 | 0.126 | 0 | 0.0% |
| adservice | 743 | 1150 | 0.8 | 0.045 | 0.092 | 0 | 0.0% |
| redis-cart | 743 | 540 | 0.8 | 0.088 | 0.448 | 0 | 0.0% |

### `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1`

`S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1` is FLAGGED with TopFull on. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T06:32:25Z → 2026-10-13T06:41:50Z. Reason text: 225× timed out; 3× <urlopen error timed out>. The CSV covers 688 s (2026-10-13T06:30:28Z → 2026-10-13T06:41:56Z). Threshold freshness stayed within 30 s on every API (longest 4 s). Admitted-rate reads went stale on all five APIs for 575 s (83.6% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 689 | 676 | 13 | 24 | 665 | 4 | 575 | 0.0% | 83.6% | caps 10×5; no-cap (10000) ×20; empty read (0) ×651 | min 0 / median 0 / mean 1.3 / max 6 (n=24 fresh) |
| postcheckout | 689 | 676 | 13 | 24 | 665 | 4 | 575 | 0.0% | 83.6% | caps 10×576; no-cap (10000) ×20; empty read (0) ×80 | min 0 / median 0 / mean 1.4 / max 6 (n=24 fresh) |
| getcart | 689 | 676 | 13 | 24 | 665 | 4 | 575 | 0.0% | 83.6% | caps 10×577; no-cap (10000) ×97; empty read (0) ×2 | min 0 / median 0 / mean 1.5 / max 7 (n=24 fresh) |
| postcart | 689 | 676 | 13 | 24 | 665 | 4 | 575 | 0.0% | 83.6% | caps 222×1, 276.5×1, 306.9×1, 330×1, 398.6×1, 445.5×1; no-cap (10000) ×19; empty read (0) ×651 | min 0 / median 0 / mean 88.5 / max 388 (n=24 fresh) |
| emptycart | 689 | 676 | 13 | 24 | 665 | 4 | 575 | 0.0% | 83.6% | no-cap (10000) ×24; empty read (0) ×652 | min 0 / median 0 / mean 1.0 / max 4 (n=24 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 06:30:30–06:32:00; 10 at 06:32:05; no cap at 06:32:10; 10 06:32:11–06:41:55
- postcheckout: no cap 06:30:30–06:32:00; 10 at 06:32:05; no cap at 06:32:10; 10 06:32:15–06:41:55
- getcart: no cap 06:30:28–06:32:02; 10 06:32:05–06:32:08; no cap at 06:32:10; 10 at 06:32:15; no cap at 06:32:20; 10 06:32:23–06:41:55
- postcart: 7 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 06:30:30–06:41:55

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 689 | 1150 | 0.8 | 0.112 | 0.258 | 0 | 0.0% |
| checkoutservice | 689 | 800 | 0.8 | 0.011 | 0.181 | 0 | 0.0% |
| recommendationservice | 689 | 1150 | 0.8 | 0.04 | 0.135 | 0 | 0.0% |
| paymentservice | 689 | 155 | 0.8 | 0.028 | 0.277 | 0 | 0.0% |
| emailservice | 689 | 120 | 0.8 | 0.079 | 0.408 | 0 | 0.0% |
| productcatalogservice | 689 | 50 | 0.95 | 0.342 | 1.3 | 173 | 25.1% |
| cartservice | 689 | 800 | 0.95 | 0.048 | 0.27 | 0 | 0.0% |
| currencyservice | 689 | 770 | 0.8 | 0.015 | 0.071 | 0 | 0.0% |
| shippingservice | 689 | 770 | 0.8 | 0.009 | 0.058 | 0 | 0.0% |
| adservice | 689 | 1150 | 0.8 | 0.024 | 0.063 | 0 | 0.0% |
| redis-cart | 689 | 540 | 0.8 | 0.016 | 0.104 | 0 | 0.0% |

### `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1_r2`

`S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1_r2` is FLAGGED with TopFull on. The collector log has 200 `fetch failed` warnings (thresholds fetch failed ×100, stats fetch failed ×100), from 2026-10-13T06:50:55Z → 2026-10-13T06:59:10Z. Reason text: 200× timed out. The CSV covers 688 s (2026-10-13T06:47:46Z → 2026-10-13T06:59:14Z). Threshold reads went stale on all five APIs for 504 s (73.3% of the span). Admitted-rate reads went stale on all five APIs for 504 s (73.3% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 689 | 55 | 634 | 37 | 652 | 504 | 504 | 73.3% | 73.3% | caps 10×24; no-cap (10000) ×19; empty read (0) ×12 | min 0 / median 3 / mean 4.0 / max 10 (n=37 fresh) |
| postcheckout | 689 | 55 | 634 | 37 | 652 | 504 | 504 | 73.3% | 73.3% | caps 10×23, 11×1; no-cap (10000) ×21; empty read (0) ×10 | min 0 / median 4 / mean 4.2 / max 10 (n=37 fresh) |
| getcart | 689 | 55 | 634 | 37 | 652 | 504 | 504 | 73.3% | 73.3% | caps 10×23; no-cap (10000) ×18; empty read (0) ×14 | min 0 / median 4 / mean 4.3 / max 10 (n=37 fresh) |
| postcart | 689 | 55 | 634 | 37 | 652 | 504 | 504 | 73.3% | 73.3% | caps min 118.76 / median 169.078 / max 242.6 / 29 distinct / 30 fresh reads; no-cap (10000) ×17; empty read (0) ×8 | min 0 / median 222 / mean 279.1 / max 627 (n=37 fresh) |
| emptycart | 689 | 55 | 634 | 37 | 652 | 504 | 504 | 73.3% | 73.3% | no-cap (10000) ×37; empty read (0) ×18 | min 0 / median 2 / mean 2.4 / max 5 (n=37 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 06:47:50–06:49:10; 10 at 06:49:15; no cap at 06:49:20; 10 06:49:25–06:50:15; no cap at 06:50:20; 10 06:50:25–06:50:50
- postcheckout: 10 live-cap changes (see fresh-threshold counts)
- getcart: no cap 06:47:50–06:49:10; 10 at 06:49:15; no cap at 06:49:20; 10 06:49:25–06:50:50
- postcart: 30 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 06:47:50–06:50:50

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 689 | 1150 | 0.8 | 0.083 | 0.283 | 0 | 0.0% |
| checkoutservice | 689 | 800 | 0.8 | 0.069 | 0.419 | 0 | 0.0% |
| recommendationservice | 689 | 1150 | 0.8 | 0.049 | 0.103 | 0 | 0.0% |
| paymentservice | 689 | 155 | 0.8 | 0.041 | 0.387 | 0 | 0.0% |
| emailservice | 689 | 120 | 0.8 | 0.114 | 0.483 | 0 | 0.0% |
| productcatalogservice | 689 | 50 | 0.95 | 0.319 | 1.3 | 163 | 23.7% |
| cartservice | 689 | 800 | 0.95 | 0.075 | 0.362 | 0 | 0.0% |
| currencyservice | 689 | 770 | 0.8 | 0.026 | 0.112 | 0 | 0.0% |
| shippingservice | 689 | 770 | 0.8 | 0.014 | 0.075 | 0 | 0.0% |
| adservice | 689 | 1150 | 0.8 | 0.026 | 0.071 | 0 | 0.0% |
| redis-cart | 689 | 540 | 0.8 | 0.02 | 0.122 | 0 | 0.0% |

### `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2`

`S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2` is FLAGGED with TopFull on. The collector log has 226 `fetch failed` warnings (thresholds fetch failed ×113, stats fetch failed ×113), from 2026-10-13T07:07:10Z → 2026-10-13T07:16:30Z. Reason text: 222× timed out; 4× <urlopen error timed out>. The CSV covers 687 s (2026-10-13T07:05:05Z → 2026-10-13T07:16:32Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 567 s (82.5% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 688 | 594 | 94 | 25 | 663 | 5 | 567 | 0.0% | 82.5% | caps 10×574; no-cap (10000) ×18; empty read (0) ×2 | min 0 / median 0 / mean 1.7 / max 8 (n=25 fresh) |
| postcheckout | 688 | 594 | 94 | 25 | 663 | 5 | 567 | 0.0% | 82.5% | caps 10×575; no-cap (10000) ×18; empty read (0) ×1 | min 0 / median 0 / mean 1.7 / max 8 (n=25 fresh) |
| getcart | 688 | 594 | 94 | 25 | 663 | 5 | 567 | 0.0% | 82.5% | caps 10×572; no-cap (10000) ×20; empty read (0) ×2 | min 0 / median 0 / mean 1.9 / max 9 (n=25 fresh) |
| postcart | 688 | 594 | 94 | 25 | 663 | 5 | 567 | 0.0% | 82.5% | caps min 162 / median 543.047 / max 543.047 / 9 distinct / 573 fresh reads; no-cap (10000) ×18; empty read (0) ×3 | min 0 / median 0 / mean 108.7 / max 544 (n=25 fresh) |
| emptycart | 688 | 594 | 94 | 25 | 663 | 5 | 567 | 0.0% | 82.5% | no-cap (10000) ×25; empty read (0) ×569 | min 0 / median 0 / mean 1.1 / max 5 (n=25 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 07:05:05–07:06:30; 10 07:06:35–07:16:32
- postcheckout: no cap 07:05:05–07:06:30; 10 07:06:35–07:16:32
- getcart: no cap 07:05:05–07:06:30; 10 at 07:06:35; no cap at 07:06:40; 10 07:06:45–07:07:00; no cap at 07:07:05; 10 07:07:08–07:16:32
- postcart: 10 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 07:05:05–07:07:05

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 688 | 1150 | 0.8 | 0.128 | 0.266 | 0 | 0.0% |
| checkoutservice | 688 | 800 | 0.8 | 0.013 | 0.244 | 0 | 0.0% |
| recommendationservice | 688 | 1150 | 0.8 | 0.046 | 0.096 | 0 | 0.0% |
| paymentservice | 688 | 155 | 0.8 | 0.03 | 0.316 | 0 | 0.0% |
| emailservice | 688 | 120 | 0.8 | 0.081 | 0.5 | 0 | 0.0% |
| productcatalogservice | 688 | 50 | 0.95 | 0.345 | 1.54 | 174 | 25.3% |
| cartservice | 688 | 800 | 0.95 | 0.052 | 0.374 | 0 | 0.0% |
| currencyservice | 688 | 770 | 0.8 | 0.016 | 0.081 | 0 | 0.0% |
| shippingservice | 688 | 770 | 0.8 | 0.009 | 0.058 | 0 | 0.0% |
| adservice | 688 | 1150 | 0.8 | 0.026 | 0.067 | 0 | 0.0% |
| redis-cart | 688 | 540 | 0.8 | 0.016 | 0.117 | 0 | 0.0% |

### `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3`

`S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3` is FLAGGED with TopFull on. The collector log has 228 `fetch failed` warnings (thresholds fetch failed ×114, stats fetch failed ×114), from 2026-10-13T18:16:20Z → 2026-10-13T18:25:45Z. Reason text: 224× timed out; 4× <urlopen error timed out>. The CSV covers 695 s (2026-10-13T18:14:15Z → 2026-10-13T18:25:50Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 575 s (82.7% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 696 | 604 | 92 | 26 | 670 | 5 | 575 | 0.0% | 82.7% | caps 10×4, 16×2, 16.8×1, 17.7×1; no-cap (10000) ×20; empty read (0) ×576 | min 0 / median 0 / mean 6.3 / max 32 (n=26 fresh) |
| postcheckout | 696 | 604 | 92 | 26 | 670 | 5 | 575 | 0.0% | 82.7% | caps 10×576, 11.5×1, 11.5336×1; no-cap (10000) ×20; empty read (0) ×6 | min 0 / median 0 / mean 2.6 / max 13 (n=26 fresh) |
| getcart | 696 | 604 | 92 | 26 | 670 | 5 | 575 | 0.0% | 82.7% | caps 10×573, 15.2×1, 16.6908×2, 17.2×1, 18×2; no-cap (10000) ×20; empty read (0) ×5 | min 0 / median 0 / mean 6.7 / max 32 (n=26 fresh) |
| postcart | 696 | 604 | 92 | 26 | 670 | 5 | 575 | 0.0% | 82.7% | caps 201×2, 239.8×1, 282.7×1, 364.1×1, 381.8×1, 469.7×1; no-cap (10000) ×20; empty read (0) ×577 | min 0 / median 0 / mean 85.8 / max 463 (n=26 fresh) |
| emptycart | 696 | 604 | 92 | 26 | 670 | 5 | 575 | 0.0% | 82.7% | no-cap (10000) ×26; empty read (0) ×578 | min 0 / median 0 / mean 0.8 / max 4 (n=26 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: no cap 18:14:15–18:15:50; 16 18:15:55–18:16:00; 17.7 at 18:16:05; 16.8 at 18:16:10; 10 18:16:13–18:25:50
- postcheckout: no cap 18:14:15–18:15:50; 10 18:15:55–18:16:06; 11.5336 at 18:16:09; 11.5 at 18:16:10; 10 18:16:15–18:25:50
- getcart: no cap 18:14:15–18:15:50; 18 18:15:55–18:16:00; 16.6908 18:16:01–18:16:02; 15.2 at 18:16:05; 17.2 at 18:16:10; 10 18:16:15–18:25:50
- postcart: 7 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 18:14:15–18:25:50

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 696 | 1150 | 0.8 | 0.127 | 0.325 | 0 | 0.0% |
| checkoutservice | 696 | 800 | 0.8 | 0.126 | 0.431 | 0 | 0.0% |
| recommendationservice | 696 | 1150 | 0.8 | 0.06 | 0.2 | 0 | 0.0% |
| paymentservice | 696 | 155 | 0.8 | 0.056 | 0.413 | 0 | 0.0% |
| emailservice | 696 | 120 | 0.8 | 0.158 | 0.633 | 0 | 0.0% |
| productcatalogservice | 696 | 100 | 0.95 | 0.482 | 1.14 | 247 | 35.5% |
| cartservice | 696 | 800 | 0.95 | 0.155 | 0.459 | 0 | 0.0% |
| currencyservice | 696 | 770 | 0.8 | 0.042 | 0.19 | 0 | 0.0% |
| shippingservice | 696 | 770 | 0.8 | 0.021 | 0.088 | 0 | 0.0% |
| adservice | 696 | 1150 | 0.8 | 0.03 | 0.069 | 0 | 0.0% |
| redis-cart | 696 | 540 | 0.8 | 0.037 | 0.261 | 0 | 0.0% |

### `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3_r2`

`S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3_r2` is FLAGGED with TopFull on. The collector log has 224 `fetch failed` warnings (thresholds fetch failed ×112, stats fetch failed ×112), from 2026-10-13T18:34:35Z → 2026-10-13T18:43:50Z. Reason text: 222× timed out; 2× <urlopen error timed out>. The CSV covers 705 s (2026-10-13T18:32:12Z → 2026-10-13T18:43:57Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 565 s (80.1% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 706 | 685 | 21 | 29 | 677 | 5 | 565 | 0.0% | 80.1% | caps 12.6×1, 12.9×1, 12.9022×1, 13.4×2, 14.2×2, 14.2415×564, 14.3×2; no-cap (10000) ×21; empty read (0) ×91 | min 0 / median 0 / mean 9.3 / max 46 (n=29 fresh) |
| postcheckout | 706 | 685 | 21 | 29 | 677 | 5 | 565 | 0.0% | 80.1% | caps 10×88, 11×1, 12.5×2, 12.5173×1, 13.7×1; no-cap (10000) ×22; empty read (0) ×570 | min 0 / median 0 / mean 3.7 / max 18 (n=29 fresh) |
| getcart | 706 | 685 | 21 | 29 | 677 | 5 | 565 | 0.0% | 80.1% | caps 10×85, 12.2858×1, 12.3×2, 14.1×2, 14.2569×1, 14.3×2, 15.4×2; no-cap (10000) ×21; empty read (0) ×569 | min 0 / median 0 / mean 9.7 / max 46 (n=29 fresh) |
| postcart | 706 | 685 | 21 | 29 | 677 | 5 | 565 | 0.0% | 80.1% | caps 163.393×1, 163.4×2, 246.67×1, 246.7×2, 324.662×1, 324.7×2, 420.1×1, 430.6×1; no-cap (10000) ×21; empty read (0) ×653 | min 0 / median 0 / mean 116.0 / max 552 (n=29 fresh) |
| emptycart | 706 | 685 | 21 | 29 | 677 | 5 | 565 | 0.0% | 80.1% | no-cap (10000) ×29; empty read (0) ×656 | min 0 / median 0 / mean 1.2 / max 5 (n=29 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 9 live-cap changes (see fresh-threshold counts)
- postcheckout: 49 live-cap changes (see fresh-threshold counts)
- getcart: 49 live-cap changes (see fresh-threshold counts)
- postcart: 11 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 18:32:15–18:43:55

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 706 | 1150 | 0.8 | 0.126 | 0.302 | 0 | 0.0% |
| checkoutservice | 706 | 800 | 0.8 | 0.134 | 0.515 | 0 | 0.0% |
| recommendationservice | 706 | 1150 | 0.8 | 0.071 | 0.261 | 0 | 0.0% |
| paymentservice | 706 | 155 | 0.8 | 0.058 | 0.381 | 0 | 0.0% |
| emailservice | 706 | 120 | 0.8 | 0.157 | 0.633 | 0 | 0.0% |
| productcatalogservice | 706 | 100 | 0.95 | 0.452 | 1.11 | 223 | 31.6% |
| cartservice | 706 | 800 | 0.95 | 0.175 | 0.549 | 0 | 0.0% |
| currencyservice | 706 | 770 | 0.8 | 0.048 | 0.134 | 0 | 0.0% |
| shippingservice | 706 | 770 | 0.8 | 0.022 | 0.087 | 0 | 0.0% |
| adservice | 706 | 1150 | 0.8 | 0.03 | 0.073 | 0 | 0.0% |
| redis-cart | 706 | 540 | 0.8 | 0.032 | 0.191 | 0 | 0.0% |

### `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run4`

`S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run4` is FLAGGED with TopFull on. The collector log has 224 `fetch failed` warnings (thresholds fetch failed ×112, stats fetch failed ×112), from 2026-10-13T18:52:40Z → 2026-10-13T19:01:55Z. Reason text: 222× timed out; 2× <urlopen error timed out>. The CSV covers 696 s (2026-10-13T18:50:25Z → 2026-10-13T19:02:01Z). Threshold freshness stayed within 30 s on every API (longest 5 s). Admitted-rate reads went stale on all five APIs for 565 s (81.2% of the span).

Numbers below are from `topfull_throttle.csv` only. Caps and admitted rates on a fresh row are measured. Carried rows (`*_fresh=0`) repeat the last successful read and are counted, not used as measured rates.

| API | Rows | Threshold fresh | Threshold carried | Admitted fresh | Admitted carried | Threshold gap s | Admitted gap s | Threshold % stale | Admitted % stale | Fresh thresholds | Fresh admitted rps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| getproduct | 697 | 598 | 99 | 28 | 669 | 5 | 565 | 0.0% | 81.2% | caps 10×568, 10.2×2, 11.2×1, 18×1; no-cap (10000) ×21; empty read (0) ×5 | min 0 / median 0 / mean 9.3 / max 46 (n=28 fresh) |
| postcheckout | 697 | 598 | 99 | 28 | 669 | 5 | 565 | 0.0% | 81.2% | caps 10×569, 10.1945×1, 10.2×2, 13.4×1; no-cap (10000) ×21; empty read (0) ×4 | min 0 / median 0 / mean 3.9 / max 19 (n=28 fresh) |
| getcart | 697 | 598 | 99 | 28 | 669 | 5 | 565 | 0.0% | 81.2% | caps 10×569, 10.2×2, 13.3873×1, 13.4×1, 13.5×1, 20×1; no-cap (10000) ×21; empty read (0) ×2 | min 0 / median 0 / mean 9.9 / max 48 (n=28 fresh) |
| postcart | 697 | 598 | 99 | 28 | 669 | 5 | 565 | 0.0% | 81.2% | caps min 216.9 / median 417.753 / max 489.9 / 9 distinct / 573 fresh reads; no-cap (10000) ×21; empty read (0) ×4 | min 0 / median 0 / mean 117.5 / max 564 (n=28 fresh) |
| emptycart | 697 | 598 | 99 | 28 | 669 | 5 | 565 | 0.0% | 81.2% | no-cap (10000) ×28; empty read (0) ×570 | min 0 / median 0 / mean 1.1 / max 5 (n=28 fresh) |

Live cap spans (`threshold_fresh=1`, threshold above 0; 10000 omitted as no cap):

- getproduct: 7 live-cap changes (see fresh-threshold counts)
- postcheckout: 7 live-cap changes (see fresh-threshold counts)
- getcart: 9 live-cap changes (see fresh-threshold counts)
- postcart: 12 live-cap changes (see fresh-threshold counts)
- emptycart: no cap 18:50:25–19:02:00

Detector fields from `topfull_detect.csv` (TopFull overload detector: quota, alpha, utilization, overloaded):

| Service | Rows | Quota mode | Alpha mode | Utilization mean | Utilization max | Overloaded rows | Overloaded share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 697 | 1150 | 0.8 | 0.124 | 0.234 | 0 | 0.0% |
| checkoutservice | 697 | 800 | 0.8 | 0.126 | 0.446 | 0 | 0.0% |
| recommendationservice | 697 | 1150 | 0.8 | 0.059 | 0.158 | 0 | 0.0% |
| paymentservice | 697 | 155 | 0.8 | 0.054 | 0.381 | 0 | 0.0% |
| emailservice | 697 | 120 | 0.8 | 0.153 | 0.55 | 0 | 0.0% |
| productcatalogservice | 697 | 100 | 0.95 | 0.488 | 1.11 | 244 | 35.0% |
| cartservice | 697 | 800 | 0.95 | 0.226 | 0.566 | 0 | 0.0% |
| currencyservice | 697 | 770 | 0.8 | 0.041 | 0.121 | 0 | 0.0% |
| shippingservice | 697 | 770 | 0.8 | 0.021 | 0.086 | 0 | 0.0% |
| adservice | 697 | 1150 | 0.8 | 0.029 | 0.093 | 0 | 0.0% |
| redis-cart | 697 | 540 | 0.8 | 0.033 | 0.27 | 0 | 0.0% |

## 4. TopFull-on flags and re-run decision

A flagged hold with TopFull on has cap and admitted-rate numbers that are carried across failed or missing proxy reads. Those series need a re-run decision before they are used as measured TopFull behavior. Goodput, latency, and RetryGuard figures are outside this audit.

**TopFull on, FLAGGED (25).** These are the re-run decisions:

- `S2_sustained_overload_burst/both/final_s2_both_burst_run1` — 196 fetch-failed warnings; threshold stale on all five APIs for 494 s; admitted stale on all five APIs for 494 s
- `S2_sustained_overload_burst/both/final_s2_both_burst_run2` — 224 fetch-failed warnings; threshold stale on all five APIs for 565 s; admitted stale on all five APIs for 565 s
- `S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep1` — 204 fetch-failed warnings; threshold stale on all five APIs for 513 s; admitted stale on all five APIs for 513 s
- `S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep2` — 218 fetch-failed warnings; admitted stale on all five APIs for 550 s
- `S2_sustained_overload_normal/both/study7_s2_normal_rgtf1_rep1` — 40 fetch-failed warnings; admitted stale on all five APIs for 105 s
- `S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2` — 110 fetch-failed warnings; threshold stale on all five APIs for 280 s; admitted stale on all five APIs for 280 s
- `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run1_r2` — 226 fetch-failed warnings; admitted stale on all five APIs for 570 s
- `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2` — 228 fetch-failed warnings; threshold stale on all five APIs for 575 s; admitted stale on all five APIs for 575 s
- `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2_r2` — 224 fetch-failed warnings; threshold stale on all five APIs for 562 s; admitted stale on all five APIs for 565 s
- `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3` — 226 fetch-failed warnings; admitted stale on all five APIs for 568 s
- `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3_r2` — 222 fetch-failed warnings; threshold stale on all five APIs for 558 s; admitted stale on all five APIs for 560 s
- `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4` — 226 fetch-failed warnings; threshold stale on all five APIs for 570 s; admitted stale on all five APIs for 570 s
- `S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4_r2` — 228 fetch-failed warnings; threshold stale on all five APIs for 572 s; admitted stale on all five APIs for 574 s
- `S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run2_r2` — 216 fetch-failed warnings; threshold stale on all five APIs for 545 s; admitted stale on all five APIs for 545 s
- `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run2_r2` — 192 fetch-failed warnings; admitted stale on all five APIs for 483 s
- `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3` — 226 fetch-failed warnings; admitted stale on all five APIs for 570 s
- `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3_r2` — 224 fetch-failed warnings; admitted stale on all five APIs for 564 s
- `S4A_topology_position_normal/both/final_4a_constrained_both_normal_run4` — 226 fetch-failed warnings; admitted stale on all five APIs for 568 s
- `S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run1_r2` — 200 fetch-failed warnings; threshold stale on all five APIs for 505 s; admitted stale on all five APIs for 505 s
- `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1` — 228 fetch-failed warnings; admitted stale on all five APIs for 575 s
- `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1_r2` — 200 fetch-failed warnings; threshold stale on all five APIs for 504 s; admitted stale on all five APIs for 504 s
- `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2` — 226 fetch-failed warnings; admitted stale on all five APIs for 567 s
- `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3` — 228 fetch-failed warnings; admitted stale on all five APIs for 575 s
- `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3_r2` — 224 fetch-failed warnings; admitted stale on all five APIs for 565 s
- `S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run4` — 224 fetch-failed warnings; admitted stale on all five APIs for 565 s

**TopFull off, FLAGGED (25).** The collector still scraped the proxy, and those scrapes failed the same rule. TopFull was off, so the re-run list above does not include them:

- `S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run2` — 16 fetch-failed warnings; longest threshold gap 45 s; longest admitted gap 45 s
- `S2_sustained_overload_burst/rg_only/s2_burst20_rgtf0` — 220 fetch-failed warnings; longest threshold gap 555 s; longest admitted gap 555 s
- `S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep1` — 224 fetch-failed warnings; longest threshold gap 565 s; longest admitted gap 565 s
- `S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep2` — 216 fetch-failed warnings; longest threshold gap 545 s; longest admitted gap 545 s
- `S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1` — 0 fetch-failed warnings; longest threshold gap 55 s; longest admitted gap 55 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1` — 228 fetch-failed warnings; longest threshold gap 574 s; longest admitted gap 574 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1_r2` — 226 fetch-failed warnings; longest threshold gap 569 s; longest admitted gap 569 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2` — 230 fetch-failed warnings; longest threshold gap 578 s; longest admitted gap 578 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2_r2` — 230 fetch-failed warnings; longest threshold gap 577 s; longest admitted gap 577 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3` — 226 fetch-failed warnings; longest threshold gap 1 s; longest admitted gap 570 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3_r2` — 230 fetch-failed warnings; longest threshold gap 1 s; longest admitted gap 579 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4` — 228 fetch-failed warnings; longest threshold gap 2 s; longest admitted gap 580 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4_r2` — 230 fetch-failed warnings; longest threshold gap 1 s; longest admitted gap 577 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run5` — 226 fetch-failed warnings; longest threshold gap 570 s; longest admitted gap 570 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run5_r2` — 228 fetch-failed warnings; longest threshold gap 575 s; longest admitted gap 575 s
- `S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run6` — 228 fetch-failed warnings; longest threshold gap 575 s; longest admitted gap 575 s
- `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1` — 228 fetch-failed warnings; longest threshold gap 575 s; longest admitted gap 575 s
- `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1_r2` — 228 fetch-failed warnings; longest threshold gap 575 s; longest admitted gap 575 s
- `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2` — 228 fetch-failed warnings; longest threshold gap 575 s; longest admitted gap 575 s
- `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2_r2` — 230 fetch-failed warnings; longest threshold gap 578 s; longest admitted gap 578 s
- `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3` — 228 fetch-failed warnings; longest threshold gap 575 s; longest admitted gap 575 s
- `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3_r2` — 228 fetch-failed warnings; longest threshold gap 575 s; longest admitted gap 575 s
- `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4` — 230 fetch-failed warnings; longest threshold gap 578 s; longest admitted gap 578 s
- `S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4_r2` — 230 fetch-failed warnings; longest threshold gap 580 s; longest admitted gap 580 s
- `S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run2` — 144 fetch-failed warnings; longest threshold gap 365 s; longest admitted gap 365 s
