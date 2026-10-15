# S2 TopFull proxy logs — run log

One line per launch, including a failed launch and its single replay. Order: tf_only, both_burst, tf_only, both_burst.

Master `current_rps` call (Task 3 Step 5): `overload_detection.py:512:        response = requests.get(url, proxies=proxies)` (no `timeout=`). Master `deploy_rl.py` calls `self.detector.current_rps()` at lines 115 and 177.

Proxy open-file limit on master (read during hold 2): `Max open files 1024 1048576` (soft, hard) on the `proxy_online_boutique` process.

`hold N | log_folder | PASS or INVALID | locust rows | note`

hold 1 | final_s2_tf_only_run3 | PASS | 554 | Paper-C1; users 275/90/100/90/5; tf; TopFull on; toggles n/a; frontend 4 on 145/145; catalog_1=145/145; TF live5s_caps=126; throttle FLAG (168 fetch warnings, first 13:23:35); proxy ticks=727 tick_gap_over_5s=no last_apply=13:30:35Z (last apply while the hold ran: 13:23:31Z; the two at 13:30:35Z came after shutdown unblocked the RL loop); rl longest_silence_s=422 from 13:23:32Z; proxy log first `http: Accept error: accept tcp [::]:8090: accept4: too many open files` at 13:23:32Z, 429 such lines; the RL main loop's last line before the silence is `['recommendationservice']`, so it blocked in `clustering()` → `current_rps()`; VS attempts 3; START ok
hold 2 | final_s2_both_burst_run3 | PASS | 557 | Paper-C1; users 275/90/100/90/5; burst_rpr 2.0; TopFull on; toggles 2 (off 1, up 1, burst 0); frontend 4 on 150/150; catalog_1=150/150; TF live5s_caps=7; throttle FLAG (224 fetch warnings, first 13:39:00); proxy ticks=757 tick_gap_over_5s=no last_apply=13:38:55Z; rl longest_silence_s=559 from 13:38:57Z; first `too many open files` 13:38:55Z, 568 such lines; proxy fd count sampled every ~14 s: 5 until Locust, 151 at 13:38:15, 609 at 13:38:44, 1024 from 13:38:58 to 13:48:03, 4 after shutdown; VS attempts 3; START ok
