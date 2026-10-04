# S2 latch-probe results

Results of runs 108–127; this section is the retro-scoring of runs 86–107. Scores are from `experiments/s2_latch_probe.py`. Runs 86–93 are the original cluster (`campaign_48/S2_sustained_overload/`, `--root campaign`). Runs 94–107 are the disk copy (`new vms/`). Run 85 is left out because its sampling gate failed. Mixes are getproduct / postcheckout / getcart / postcart / emptycart, from the runs 80–93 and 94–107 ranking tables. The run 108–127 section follows the retro-score.

| Run | Cluster | Mix | Class | Blend | Checkout streak/ov | Recs streak/ov | Retries f>recs | Retries f>ck | Checkout sojourn 90–150 s | Over-500 share |
|---:|---|---|---|---|---|---|---:|---:|---:|---:|
| 86 | original | 275/80/100/90/5 | released | yes | 108/163 | 226/456 | 217256 | 10434 | 306.6 ms | 0.00 |
| 87 | original | 275/70/100/90/5 | released | yes | 19/86 | 118/449 | 219175 | 2829 | 204.8 ms | 0.00 |
| 88 | original | 275/80/100/90/5 | released | yes | 15/58 | 175/446 | 235731 | 2181 | 216.4 ms | 0.00 |
| 89 | original | 275/90/100/90/5 | released | yes | 58/164 | 238/485 | 224314 | 9302 | 234.5 ms | 0.00 |
| 90 | original | 265/90/100/90/5 | released | no | 228/303 | 281/305 | 143521 | 30005 | 276.8 ms | 0.08 |
| 91 | original | 275/80/100/50/50 | sticky | no | 564/591 | 0/29 | 0 | 55805 | 250.2 ms | 0.00 |
| 92 | original | 275/90/100/90/5 | released | no | 59/128 | 454/480 | 235145 | 10323 | 332.3 ms | 0.00 |
| 93 | original | 265/90/100/90/5 | released | yes | 18/50 | 359/544 | 258910 | 2142 | 223.2 ms | 0.00 |
| 94 | disk copy | 275/90/100/90/5 | sticky | no | 561/590 | 0/0 | 0 | 61002 | 307.2 ms | 0.42 |
| 95 | disk copy | 275/90/100/90/5 | sticky | no | 564/591 | 0/0 | 0 | 61643 | 302.9 ms | 0.42 |
| 96 | disk copy | 275/90/100/90/5 | sticky | no | 566/592 | 0/0 | 0 | 61775 | 308.0 ms | 0.42 |
| 97 | disk copy | 275/90/100/90/5 | released | yes | 23/123 | 64/545 | 215908 | 2191 | 263.5 ms | 0.25 |
| 98 | disk copy | 275/80/100/90/5 | released | no | 0/24 | 250/567 | 310947 | 28 | 133.0 ms | 0.00 |
| 99 | disk copy | 275/90/100/90/5 | released | yes | 290/318 | 97/274 | 119696 | 32151 | 255.3 ms | 0.33 |
| 100 | disk copy | 275/90/100/90/5 | sticky | no | 548/590 | 0/0 | 0 | 62775 | 259.2 ms | 0.31 |
| 101 | disk copy | 275/90/100/90/5 | released | yes | 375/412 | 77/192 | 76303 | 41421 | 249.4 ms | 0.23 |
| 102 | disk copy | 275/80/100/90/5 | sticky | no | 537/586 | 0/0 | 0 | 52950 | 158.9 ms | 0.00 |
| 103 | disk copy | 275/80/100/90/5 | sticky | no | 546/585 | 0/0 | 0 | 54266 | 178.5 ms | 0.08 |
| 104 | disk copy | 275/80/100/90/5 | sticky | no | 546/584 | 0/0 | 0 | 54465 | 172.7 ms | 0.08 |
| 105 | disk copy | 275/85/100/90/5 | released | yes | 42/74 | 207/522 | 237503 | 4190 | 236.6 ms | 0.25 |
| 106 | disk copy | 275/85/100/90/5 | sticky | no | 559/593 | 0/0 | 0 | 58302 | 257.3 ms | 0.25 |
| 107 | disk copy | 275/85/100/90/5 | sticky | no | 561/594 | 0/0 | 0 | 58758 | 253.7 ms | 0.25 |

Of these 22 holds, 10 are sticky (91, 94, 95, 96, 100, 102, 103, 104, 106, 107) and 12 are released (86, 87, 88, 89, 90, 92, 93, 97, 98, 99, 101, 105); none are other, and no folder was missing. The nine disk-copy latches named in the handoff and the 99–107 guide are sticky. Run 91 is also sticky on the original cluster (checkout streak 564, recommendations streak 0, recommendations overloaded ticks 29). Released uses a frontend→recommendations retry bar of 70,000, so run 101 (76,303) is released and a count of 50,000 stays other. Checkout sojourn in the 90–150 s window does not separate the modes. Sticky means run from 158.9 ms (run 102) to 308.0 ms (run 96), with an over-500 share from 0.00 to 0.42. Released means run from 133.0 ms (run 98) to 332.3 ms (run 92), with an over-500 share from 0.00 to 0.33. No sticky hold is near 480 ms, and none has most ticks over 500 ms; released run 92 (332.3 ms) sits above every sticky hold. That overlap refutes the threshold story in the replays-differ guide for this window.

## Runs 108–127

The base is the run 89 mix (275/90/100/90/5) on Paper-C1: frontend 1150 m × 4, checkout 800 m × 1, recommendations 1150 m × 1, sidecar request 100 m, both controllers off, `spawn_rate` 50 unless the lever changes it. The plan was twenty holds in two shuffled blocks (seed 20261003), one change from that base per hold. Prep sets checkout and recommendations CPU and the checkout replica count before the 360 s cool-off, so the runner's CPU patch is `already at …; skipping patch`. Eighteen holds passed the sampling gate: 108–115 and 117–126. Run116 failed that gate (`total.csv` has 4 rows, mesh span 906 s). Run127 was not run. On the night of 2026-10-03, prep for run123 scaled checkout to 2 while the deployment was still at 1000 m, and `checkoutservice-85fb96fbf-9m4m4` stayed Pending (`FailedScheduling`, Insufficient cpu), so slots 124–127 were not started. On 2026-10-04 the VMs were started again (worker boot `2026-10-04 06:49:12`) and those four levers were run from checkout at 800 m × 1. A first launch of run123 that morning had its collectors stopped with SIGTERM about two minutes after Locust started (`total.csv` has 236 rows). That copy is `experiments/results/new vms/_discarded/run123-sigterm-20261004` and is not a score. The relaunch passed. Block A ended at run117, about 01:50 +03 on 2026-10-04. The VMs stayed up across that night's block boundary. Recommendations pod `recommendationservice-566f644686-jwsxh` is 3h15m old at run117's t=0, 3h42m old at run118's t=0, and 12h old at run123's t=0.

Every quoted runner log line is `already at …; skipping patch` (runs 110, 111, 113, 114, 116, 121, and 122). No kept runner log records an applied CPU patch. A checkout or recommendations pod about 6–7 minutes old at t=0 is the prep rollout during the cool-off. Run108's `t0.txt` is the snapshot before the in-runner restart.

Scores are `python experiments/s2_latch_probe.py score N`. Getproduct goodput is the canon mean (drop the first 30 rows and the last 5). Frontend sojourn is the hold-mean inbound Δ`rq_time_sum_ms` / Δ`rq_time_count`, last 5 polls dropped. Checkout sojourn and the over-500 share are the 90–150 s window. Pod age is the `AGE` column in `state/t0.txt`.

| Slot | Block | Treatment | Class | Blend | Ck streak/ov | Recs streak/ov | Email ov | Pay ov | Retries f>recs | Retries f>ck | Ck sojourn 90–150 s | Over-500 | Getproduct goodput | Frontend sojourn | Ck age t=0 | Recs age t=0 |
|---:|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 108 | A | restart | released | yes | 12/36 | 555/558 | 11 | 4 | 292131 | 1094 | 204.6 ms | 0.00 | 9.5 | 1041.6 ms | 34h | 4d1h |
| 109 | A | spawn10 | released | yes | 283/379 | 11/321 | 24 | 1 | 105651 | 27798 | 500.5 ms | 0.92 | 173.1 | 654.3 ms | 28m | 28m |
| 110 | A | recs_cpu1000 | other | yes | 496/548 | 42/506 | 13 | 1 | 22814 | 56837 | 238.7 ms | 0.25 | 254.9 | 364.5 ms | 56m | 6m28s |
| 111 | A | control | released | yes | 181/252 | 69/387 | 21 | 0 | 141345 | 19091 | 264.8 ms | 0.33 | 134.8 | 656.2 ms | 83m | 6m22s |
| 112 | A | ck_rep2 | released | no | 0/0 | 145/558 | 34 | 0 | 224832 | 7 | 73.9 ms | 0.00 | 57.9 | 858.5 ms | 111m, 6m20s | 34m |
| 113 | A | ck_cpu1000 | released | no | 0/25 | 143/557 | 28 | 0 | 239467 | 21 | 110.8 ms | 0.00 | 44.5 | 893.3 ms | 6m29s | 61m |
| 114 | A | recs_users310 | released | no | 9/40 | 185/561 | 12 | 0 | 226938 | 830 | 175.1 ms | 0.08 | 77.7 | 872.2 ms | 6m59s | 92m |
| 115 | A | ck_rep2_pc120 | released | yes | 11/12 | 116/547 | 142 | 4 | 217861 | 1194 | 175.3 ms | 0.04 | 73.9 | 839.6 ms | 38m, 6m27s | 124m |
| 116 | A | control | Failed the sampling gate: total.csv has 4 rows and the mesh span is 906 s. | | | | | | | | | | | | | |
| 117 | A | pc120 | released | yes | 19/92 | 136/561 | 36 | 0 | 230747 | 2213 | 272.7 ms | 0.25 | 64.8 | 886.2 ms | 110m | 3h15m |
| 118 | B | recs_users310 | released | no | 0/31 | 124/564 | 16 | 0 | 241497 | 13 | 121.0 ms | 0.00 | 56.9 | 893.2 ms | 137m | 3h42m |
| 119 | B | ck_rep2 | released | no | 0/0 | 21/449 | 125 | 0 | 170432 | 2 | 71.4 ms | 0.00 | 103.1 | 736.8 ms | 165m, 6m29s | 4h11m |
| 120 | B | spawn10 | released | yes | 14/69 | 45/593 | 15 | 0 | 213137 | 1303 | 193.1 ms | 0.17 | 63.9 | 839.1 ms | 3h12m | 4h38m |
| 121 | B | control | released | yes | 11/48 | 156/560 | 12 | 0 | 226799 | 1039 | 177.9 ms | 0.08 | 55.4 | 866.3 ms | 3h43m | 5h8m |
| 122 | B | ck_cpu1000 | released | no | 0/23 | 560/563 | 21 | 0 | 279481 | 39 | 103.2 ms | 0.00 | 14.4 | 995.0 ms | 6m24s | 5h35m |
| 123 | B | ck_rep2_pc120 | released | yes | 20/19 | 20/530 | 204 | 12 | 194503 | 2335 | 235.1 ms | 0.08 | 94.6 | 777.5 ms | 6h15m, 40m | 12h |
| 124 | B | restart | sticky | no | 567/590 | 0/0 | 10 | 2 | 0 | 64036 | 283.2 ms | 0.42 | 273.2 | 297.6 ms | 6h38m | 12h |
| 125 | B | pc120 | sticky | no | 549/589 | 0/0 | 13 | 0 | 0 | 87211 | 328.5 ms | 0.33 | 273.1 | 332.5 ms | 22m | 21m |
| 126 | B | recs_cpu1000 | sticky | no | 564/591 | 0/98 | 14 | 4 | 0 | 64124 | 256.6 ms | 0.31 | 273.4 | 279.0 ms | 44m | 6m15s |
| 127 | B | control | Did not run. The 2026-10-04 re-run covered slots 123–126 only. | | | | | | | | | | | | | |

Run108's checkout age 34h and recommendations age 4d1h are the pre-restart pods (restart counts 8 and 53). From run109 through run122, those two services show restart count 0 in `t0.txt`. Run112, run115, run119, and run123 list two checkout ages because prep had scaled checkout to 2. Run124's t=0 snapshot is before the in-runner restart, same as run108: checkout `76zdj` is 6h38m and recommendations `jwsxh` is 12h. Run125's t=0 pods are the ones that restart created (22m and 21m, restart count 0). Run125's gate passed with one note: checkout `replica_count` was 0 on one resource sample. Run126's recommendations age 6m15s is the 1000 m prep roll.

### Verdict per lever

`moved` / `no effect seen` / `mixed` are used only when both holds of that lever exist. A lever with one hold, or whose second hold did not run, is incomplete.

- `pc120`: **mixed**. Run117 is released and a blend (sojourn 272.7 ms). Run125 is sticky (checkout streak 549, recommendations streak 0, sojourn 328.5 ms, over-500 share 0.33). Postcheckout mean RPS is 84.08 on run117 and 64.2 on run125.
- `recs_users310`: **moved**. Run114 and run118 are both released, and neither is a blend.
- `ck_rep2`: **moved**, and **latch avoided**. Run112 and run119 are both released and not blends. Checkout sojourn is 73.9 ms and 71.4 ms, over-500 share 0.00 on both, so the sojourn stayed under 500 ms. Per-pod checkout CPU (mean of summed `cpu_millicores` / 2) is 249.9 m on run112 and 341.9 m on run119. Replica mode is 2 on every checkout resource sample (134 and 134).
- `ck_cpu1000`: **moved**, and **latch avoided**. Run113 and run122 are both released and not blends. Checkout sojourn is 110.8 ms and 103.2 ms, over-500 share 0.00 on both, so the sojourn stayed under 500 ms.
- `recs_cpu1000`: **mixed**. Run110 is other and a blend (checkout streak 496, frontend→recommendations retries 22814). Run126 is sticky (checkout streak 564, recommendations overloaded 98 ticks with streak 0, frontend→recommendations retries 0).
- `ck_rep2_pc120`: **moved**, and **latch avoided**. Run115 and run123 are both released blends. Checkout sojourn is 175.3 ms and 235.1 ms, over-500 share 0.04 and 0.08, so the sojourn stayed under 500 ms. Per-pod checkout CPU (mean of summed `cpu_millicores` / replica count) is 353.2 m on run115 and 369.6 m on run123. Replica mode is 2 on the checkout resource samples (135 and 133). Postcheckout mean RPS is 89.21 on run115 and 94.53 on run123.
- `spawn10`: **moved**. Run109 and run120 are both released blends. In `getproduct.csv` the arrival ramp is about 10 s: RPS is 271.0 at row 10 on run109 and 266.5 at row 10 on run120. Control run111 (`spawn_rate` 50) is at 52.5 RPS on row 10, and its 5 s mean first reaches 80% of the later plateau at row 36.
- `restart`: **mixed**. Run108 is released and a blend. Run124 is sticky (checkout streak 567, recommendations streak 0, frontend→recommendations retries 0, frontend→checkout retries 64036).

### Controls

The planned controls are runs 111, 116, 121, and 127. The two that scored are run111 (released, blend yes) and run121 (released, blend yes). Run116 failed the sampling gate. Run127 did not run. The two scored controls agree: both are released blends. The 7 earlier holds of this mix on the disk copy (runs 94–97 and 99–101) are 3 blends and 4 sticky.

### Replays-differ checks

(a) Runs 124, 125, and 126 are sticky, and they do not share a placement, restart count, or age that the released holds lack. Every snapshot from run108 through run126, including the failed run116, has checkout and recommendations on `topfull-worker1` and kernel `5.4.0-216-generic`. Runs 108–122 share worker boot `2026-10-03 17:45:52`. Runs 123–126 share worker boot `2026-10-04 06:49:12`. Run123 on that new boot is released, so the boot change does not by itself separate the modes. Run123 (released) and run124's pre-restart t=0 (sticky after the roll) share checkout pod `76zdj` and recommendations pod `jwsxh`. Run125 is sticky on the post-restart pods (restart count 0). Run126 is sticky with a recommendations pod 6m15s old.

(b) Checkout sojourn in the 90–150 s window does not separate sticky from released across the scored holds 86–126. In the retro-score, sticky sojourn runs from 158.9 ms (run 102) to 308.0 ms (run 96), over-500 share 0.00–0.42, and released sojourn runs from 133.0 ms (run 98) to 332.3 ms (run 92), over-500 share 0.00–0.33. The probe's released holds run from 71.4 ms (run119, share 0.00) to 500.5 ms (run109, share 0.92). The probe's sticky holds are 256.6 ms (run126, share 0.31), 283.2 ms (run124, share 0.42), and 328.5 ms (run125, share 0.33). Those three sit inside the released band. The ranges overlap. The one other hold, run110, sits at 238.7 ms, inside both bands.

(c) Scored block A is 8 released and 1 other (run110), with no sticky hold. Scored block B is 6 released (runs 118–123) and then 3 sticky (runs 124–126). The sticky holds are the last three of the day, and they are also the second holds of `restart`, `pc120`, and `recs_cpu1000`, whose first holds were not sticky. The two scored controls agree. Blend is yes on 6 of 9 scored block-A holds and on 3 of 9 scored block-B holds; the treatments differ, so that share is not an order effect. Pod ages do not reset between run117 and run118. They do reset for checkout and recommendations at run124's in-runner restart.

### Follow-up

Two holds are a screen. About eight holds of one configuration separate a 1-in-5 latch rate from a 3-in-5 latch rate. The mixed levers (`pc120`, `recs_cpu1000`, `restart`) are dropped here.

- `recs_users310` moved: three interleaved replays with controls, Paper-C1, getproduct 310.
- `ck_rep2` moved, latch avoided: three interleaved replays, checkout 2 × 800 m.
- `ck_cpu1000` moved, latch avoided: three interleaved replays, checkout 1000 m × 1.
- `ck_rep2_pc120` moved, latch avoided: three interleaved replays, checkout 2 × 800 m and postcheckout 120.
- `spawn10` moved: three interleaved replays at `spawn_rate` 10.

Service-by-service (a)/(b)/(c) tables for these holds: [2026-10-04-s2-latch-probe-abc.md](2026-10-04-s2-latch-probe-abc.md).
