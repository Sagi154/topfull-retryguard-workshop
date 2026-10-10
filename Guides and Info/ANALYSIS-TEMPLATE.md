# Analysis template

Use this when writing up one hold or a group of holds. The numbers come from `experiments/analysis_score.py`. The meanings of (a), (b), and (c) are in [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). The worked example of the table layout is [2026-10-08-s2-run24-both-on-replay-abc.md](2026-10-08-s2-run24-both-on-replay-abc.md).

`experiments/rho_estimate_report.py` is retired. Arrival rate, sojourn, and toggles come from `analysis_score.py`. Leave `rho_estimate_report.md` files that are already in run folders as they are.

`experiments/s2_both_off_abc.py` still scores the retired inbound-rejection reading. New guides use `analysis_score.py`.

## Score the folders

```powershell
python experiments/analysis_score.py <run_dir> [<run_dir> ...]
python experiments/analysis_score.py --sep 2 <run_a> <run_b> <run_c> <run_d>
```

`--sep N` inserts a bold bar (`**┃**`) after every N columns. One folder is a single-run guide: same sections, one column, no bar. Labels are the `run<N>` suffix of the folder name.

The scorer uses every inbound row and every Locust row with `RPS > 0`. It does not drop the first 30 Locust rows or the last 5 polls. Those trims belong to `s2_probe_tables.py` and the canon scorer.

The file streak is in seconds. A guide that counted consecutive rows (the four-arms file for runs 24 and 25) is a row count. Say which unit a comparison column uses. The parenthetical on a RetryGuard hold is the controller's max `high` from `retryguard.log`, which is a sample count.

## Write the guide

Put the guide in `Guides and Info/` with a date and the mix or the arm in the name. Sections, in this order. A section that does not apply (no `retryguard.log`, one hold with no replay) gets one sentence saying so.

1. **Setup.** Duration, mix as getproduct / postcheckout / getcart / postcart / emptycart, `spawn_rate`, CPU table and replica pin, which controllers are on, cool-off, folder paths.
2. **Index.** One row per arm or per generation of the same setup, with the slot numbers. Column order follows this index. A bold bar separates groups.
3. **Gate.** Passed or failed, then the scorer's gate numbers: Locust `total.csv` rows, frontend replicas on every `resource_usage.csv` sample, any service whose replica count hit 0, `service_capacity.json` against the pin, mesh span, inbound gaps of 1.5 s or longer. A failed gate stays in the guide with the reason, and its columns stay blank only when the files are unusable.
4. **Edge-mode bars.** Copy the scorer's first line (shed bar, climb bars, rejection bar, re-enable bar). Add the interval the hold actually used: shed and 0→1 take `interval_samples` seconds of row timestamps; 1→2 and 2→3 take 15 s on the current controller (`CLIMB_INTERVAL_SECONDS`). Holds before 2026-10-08 used 30 s for every step. `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.
5. **(a) Edge rpr.** Three tables from the scorer, only for edges with a tick above the shed bar or a retry delta. The other controlled edges are one sentence. Cell shapes:
   - File streak seconds / ticks above the shed bar, and the controller `high` in parentheses when a log exists. **Bold** is a file streak of at least 30 seconds.
   - Mean rpr / max rpr / volume rpr. Volume is the hold's `Δretry / first attempts`.
   - Climb streaks while that attempt cap is in force: samples at 1 attempt with rpr at or under the 1→2 bar, then samples at 2 attempts with rpr at or under the 2→3 bar. An em dash means that cap never applied.
6. **Rejection, beside (a).** Not the shed signal. Longest streak / count above 0.20, then longest streak / count strictly under the re-enable bar (0.10 unless the START line says otherwise). **Bold** in the 0.20 table is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain. Then `grpc_4 / grpc_14` for recommendationservice, productcatalogservice, currencyservice, and adservice.
7. **(b) Detector overloaded fraction.** `overloaded=1` ticks over `topfull_detect.csv` rows, as `ticks/rows (share%)`. **Bold** is a share of at least 0.5.
8. **(c) Retry volume.** Outbound retry delta by target. Inbound resets for all 11 services. The same `grpc_4 / grpc_14` pair is what the retry policy counts on the four read callees.
9. **RetryGuard toggles.** One table per callee whose attempt count changes. Columns follow the index, with the same bold bars. Rows, in this order. An em dash means that edge never went to 0, so the re-enable bar was not in force. When an edge sheds more than once, list each cycle in the cell in time order.
   - `ON→OFF / OFF→ON` counts.
   - Shed rpr, from the `ON→OFF` line.
   - Attempts after re-enable: the attempt count once the climb that follows `0→1` stops. The cell is 3 when it climbs back to the full policy. An em dash when the edge stays at 0.
   - Time OFF, in seconds, from the shed timestamp to the re-enable timestamp, or to the controller exit when the edge stays at 0.
   - OFF rejection min / median. The samples are the `state=OFF` `OBSERVE` lines for that callee (`rejection=`).
   - Streak under the bar: the longest run of those OFF-window samples with rejection strictly below that hold's `reenable_rejection`. A streak that reaches the interval is the `0→1` step.

   One sentence under the table names which holds re-enabled and which stayed at 0. The timestamp log (time, name, step, attempts before the step, rpr or rejection) follows when a cell holds more than one cycle. When RetryGuard is off, say there is no `retryguard.log` and skip the tables. The scorer's toggle list is the transition lines; the OFF-window min, median, streak, and time OFF are read from `retryguard.log` as above.
10. **Locust goodput.** Mean `Goodput` while `RPS > 0`, per API.
11. **Locust fail rate.** Mean `Fail / RPS` while `RPS > 0`, per API.
12. **Locust P95.** Mean `Latency95` (ms) while `RPS > 0`, per API.
13. **Inbound arrival rate.** Positive `Δtotal` over the elapsed time of `service_inbound.csv`, per service, req/s.
14. **Inbound sojourn.** `Δrq_time_sum_ms / Δrq_time_count`, milliseconds.
15. **Share of inbound requests above 500 ms.** From the `rq_time_buckets` `le=500` cumulative count.
16. **CPU.** Per-pod quota, replica mode, mean millicores, max millicores. Mean and max are `cpu_millicores` summed across replicas, so frontend can sit above its per-pod quota.
17. **CPU as a fraction of per-pod quota × replicas.** Mean / max of `cpu_millicores / (quota × replica_count)`. Quota is the per-pod `quota` in `topfull_detect.csv`. A sample with replica count 0 is left out of the fraction.
18. **Detector max utilization.** Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).
19. **TopFull live caps.** The scorer lists live reads (`threshold_fresh=1`, threshold above 0). 10000 is no cap. A live 0 is an empty read and is left out. Write the arrow trace from that list when the series is short enough to read; otherwise keep the scorer's collapsed spans. `postcart` and `emptycart` are called out when every live read is no cap.
20. **Per arm, or per hold.** One paragraph: what shed, what climbed, retry volume, `grpc_4`, and which services were detector-hot.
21. **Related links.** This template, the (a)/(b)/(c) reading, the edge-mode section of [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md), and the previous guide for the same mix when one exists.

## Done when

Every section above is present or has its one-sentence omission. Bold marks match the rules in (a), the 0.20 rejection table, and (b). Group bars match the index. Each callee that changed attempt count has the six-row toggle table, and an edge that never went to 0 is an em dash on the OFF rows. The file streak unit is seconds, and any column taken from an older row-count guide says so. No number in the prose disagrees with the scorer output or with `retryguard.log`.
