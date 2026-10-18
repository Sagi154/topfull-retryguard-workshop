# S2 latch-probe v2, runs 132–153

## Setup

600 s holds, both controllers off, `spawn_rate` 50 except the `spawn10` and `*_spawn10` holds. Paper-C1, frontend pinned at 4, sidecar request 100 m with no CPU limit. The base mix is the run 89 mix, 275 / 90 / 100 / 90 / 5. Arms whose name contains `pc120` use postcheckout 120 (275 / 120 / 100 / 90 / 5). Seed 20261004, same shuffle as a series that would have started at run128. Runs 128–131 were already the `ck_rep2_pc120` replays, so this series starts at run132. Checkout and recommendations were rolled before every hold. `service_capacity.json` on each folder matches that hold's checkout and recommendations limit and replica count.

Twenty planned holds are run132–run151. Run136 (`recs_cpu1000_spawn10`) and run138 (`recs_cpu1000`) failed the sampling gate and are not modes. The two replacement holds are run152 (`recs_cpu1000_spawn10`) and run153 (`recs_cpu1000`). Both passed. Twenty holds are scored.

Sticky means checkout streak ≥ 400 and recommendations streak 0. Released means frontend → recommendations retries ≥ 70000 and the hold is not sticky. Anything else is other. A blend is recommendations and checkout both at streak ≥ 10 and overloaded ticks ≥ 10, plus email or payment overloaded ticks ≥ 10. A near-miss is two of those three bars, with the missing bar at a streak or overloaded-tick count of at least 5. Streaks and overloaded ticks in this guide drop the last 5 inbound polls (`experiments/s2_latch_probe.py score`). The ABC guide's (a) table keeps that tail, so a streak there can be a few samples longer.

Run136 failed with `total.csv` 152 rows, mesh span 269 s, and 54 steal samples per node. Run138 failed with 169 rows, mesh span 301 s, and about 60 steal samples per node. Their short windows are not in the verdicts.

Collected at: run132 2026-10-04T12:40:28.291155Z, end of block A run141 2026-10-04T18:01:24.601328Z, start of block B run142 2026-10-04T18:30:04.845953Z, last planned hold run151 2026-10-04T23:03:32.891359Z, last replacement run153 2026-10-05T00:02:39.866911Z.

## Per hold

| Slot | Block | Treatment | Class | Blend | Ck streak/ov | Recs streak/ov | Email ov | Pay ov | Retries f>recs | Retries f>ck | Ck sojourn 90–150 | Over-500 | Steal master/worker/load |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| run132 | A | control | released | yes | 10 / 329 | 50 / 508 | 109 | 0 | 168467 | 923 | 198.7 | 0.08 | 0.08 / 0.13 / 0.27 |
| run133 | A | spawn10 | released | no | 8 / 164 | 38 / 584 | 37 | 0 | 202058 | 727 | 165.2 | 0.0 | 0.10 / 0.18 / 0.62 |
| run134 | A | control | released | yes | 158 / 271 | 23 / 379 | 51 | 0 | 146773 | 16945 | 236.2 | 0.25 | 0.16 / 0.11 / 0.27 |
| run135 | A | ck_cpu1000_pc120 | released | no | 116 / 262 | 6 / 388 | 156 | 0 | 144697 | 23255 | 281.4 | 0.42 | 0.13 / 0.09 / 0.43 |
| run136 | A | recs_cpu1000_spawn10 | failed | | | | | | | | | | |
| run137 | A | ck_rep2_pc120 | released | yes | 14 / 19 | 15 / 541 | 350 | 9 | 188153 | 1758 | 192.0 | 0.08 | 0.15 / 0.08 / 1.95 |
| run138 | A | recs_cpu1000 | failed | | | | | | | | | | |
| run139 | A | control | sticky | no | 562 / 589 | 0 / 0 | 12 | 1 | 2 | 61199 | 251.4 | 0.33 | 0.24 / 0.07 / 0.21 |
| run140 | A | ck_rep2_pc120_spawn10 | released | no | 16 / 24 | 3 / 301 | 411 | 2 | 139838 | 1997 | 227.9 | 0.08 | 0.13 / 0.06 / 0.89 |
| run141 | A | ck_cpu1000_pc120_spawn10 | other | no | 303 / 599 | 0 / 0 | 4 | 0 | 2920 | 76718 | 485.0 | 0.83 | 0.09 / 0.07 / 0.56 |
| run142 | B | spawn10 | sticky | no | 599 / 606 | 0 / 0 | 1 | 1 | 1082 | 61448 | 492.8 | 0.92 | 0.09 / 0.08 / 0.90 |
| run143 | B | control | other | no | 368 / 410 | 0 / 0 | 11 | 0 | 0 | 56683 |  |  | 0.09 / 0.05 / 0.90 |
| run144 | B | recs_cpu1000_spawn10 | sticky | no | 600 / 606 | 0 / 19 | 1 | 0 | 6 | 61071 | 481.8 | 0.83 | 0.12 / 0.06 / 0.50 |
| run145 | B | ck_rep2_pc120_spawn10 | released | no | 9 / 10 | 9 / 398 | 345 | 1 | 215043 | 1122 | 182.5 | 0.0 | 0.17 / 0.07 / 1.45 |
| run146 | B | ck_cpu1000_pc120 | released | yes | 113 / 254 | 19 / 364 | 142 | 0 | 132183 | 26227 | 289.2 | 0.42 | 0.12 / 0.07 / 0.01 |
| run147 | B | control | sticky | no | 558 / 591 | 0 / 0 | 19 | 0 | 0 | 61690 | 230.3 | 0.25 | 0.11 / 0.05 / 0.02 |
| run148 | B | recs_cpu1000 | sticky | no | 561 / 590 | 0 / 156 | 16 | 0 | 0 | 62515 | 252.1 | 0.33 | 0.11 / 0.06 / 0.01 |
| run149 | B | ck_cpu1000_pc120_spawn10 | sticky | no | 601 / 604 | 0 / 2 | 4 | 0 | 188 | 76898 | 496.1 | 0.92 | 0.16 / 0.10 / 0.02 |
| run150 | B | ck_rep2_pc120 | released | yes | 15 / 17 | 24 / 551 | 223 | 13 | 213469 | 1962 | 209.1 | 0.12 | 0.19 / 0.12 / 0.02 |
| run151 | B | control | released | no | 53 / 154 | 4 / 515 | 34 | 0 | 190893 | 5285 | 255.8 | 0.33 | 0.28 / 0.12 / 0.02 |
| run152 | R | recs_cpu1000_spawn10 | other | no | 302 / 600 | 0 / 266 | 0 | 0 | 1353 | 56426 | 498.3 | 0.83 | 0.30 / 0.11 / 0.01 |
| run153 | R | recs_cpu1000 | released | yes | 121 / 148 | 17 / 449 | 15 | 0 | 200126 | 12373 | 264.2 | 0.33 | 1.03 / 0.11 / 0.01 |

Run143's 90–150 s checkout sojourn is blank: that window sits in an inbound hole, so the scorer has no samples there. Its class is other because the trimmed checkout streak is 368, under 400.

## Verdict per arm

`moved` / `no effect seen` / `mixed` need two scored holds. A hold that failed the gate is not one of them. A replacement that passed is.

- `spawn10`: **mixed**. Scored holds: run133 (released, blend no), run142 (sticky, blend no). Checkout sojourn in the 90–150 s window: run133 165.2 ms (over-500 0.0, streak 8), run142 492.8 ms (over-500 0.92, streak 599). run133 data row 10 is 224.5 RPS and the series max is 273.0; run142 data row 10 is 211.5 RPS and the series max is 301.0; control run132 (`spawn_rate` 50) is 47.5 RPS on data row 10 (series max 280.0).
- `ck_cpu1000_pc120`: **moved**. Scored holds: run135 (released, blend no), run146 (released, blend yes). Checkout sojourn in the 90–150 s window: run135 281.4 ms (over-500 0.42, streak 116), run146 289.2 ms (over-500 0.42, streak 113). postcheckout mean goodput 25.47 req/s on run135 and 22.23 req/s on run146.
- `ck_rep2_pc120`: **moved, latch avoided**. Scored holds: run137 (released, blend yes), run150 (released, blend yes). Checkout sojourn in the 90–150 s window: run137 192.0 ms (over-500 0.08, streak 14), run150 209.1 ms (over-500 0.12, streak 15). Per-pod checkout CPU is 405.06 m on run137 (mean total 810.12 m, replica mode 2, 135 samples, replica count never 0) and 371.91 m on run150 (mean total 743.83 m, replica mode 2, 134 samples, replica count never 0). Postcheckout mean goodput is 40.45 req/s on run137 and 33.54 req/s on run150.
- `recs_cpu1000`: **mixed**. Scored holds: run148 (sticky, blend no), run153 (released, blend yes). Checkout sojourn in the 90–150 s window: run148 252.1 ms (over-500 0.33, streak 561), run153 264.2 ms (over-500 0.33, streak 121).
- `recs_cpu1000_spawn10`: **mixed**. Scored holds: run144 (sticky, blend no), run152 (other, blend no). Checkout sojourn in the 90–150 s window: run144 481.8 ms (over-500 0.83, streak 600), run152 498.3 ms (over-500 0.83, streak 302). run144 data row 10 is 200.5 RPS and the series max is 312.5; run152 data row 10 is 249.5 RPS and the series max is 310.5; control run132 (`spawn_rate` 50) is 47.5 RPS on data row 10 (series max 280.0).
- `ck_rep2_pc120_spawn10`: **moved, latch avoided**. Scored holds: run140 (released, blend no), run145 (released, blend no). Checkout sojourn in the 90–150 s window: run140 227.9 ms (over-500 0.08, streak 16), run145 182.5 ms (over-500 0.0, streak 9). Per-pod checkout CPU is 440.11 m on run140 (mean total 880.22 m, replica mode 2, 134 samples, replica count never 0) and 403.82 m on run145 (mean total 807.64 m, replica mode 2, 134 samples, replica count never 0). Postcheckout mean goodput is 46.63 req/s on run140 and 40.43 req/s on run145. Getproduct data row 10 is 207.0 RPS on run140 (series max 264.5) and 215.5 RPS on run145 (series max 277.0). Control run132 (`spawn_rate` 50) is 47.5 RPS on data row 10 (series max 280.0).
- `ck_cpu1000_pc120_spawn10`: **mixed**. Scored holds: run141 (other, blend no), run149 (sticky, blend no). Checkout sojourn in the 90–150 s window: run141 485.0 ms (over-500 0.83, streak 303), run149 496.1 ms (over-500 0.92, streak 601). Postcheckout mean goodput is 0.22 req/s on run141 and 0.06 req/s on run149. Getproduct data row 10 is 194.0 RPS on run141 (series max 307.5) and 204.0 RPS on run149 (series max 291.0). Control run132 (`spawn_rate` 50) is 47.5 RPS on data row 10 (series max 280.0).

Checkout sojourn stayed under 500 ms on both holds of `ck_rep2_pc120` (192.0 ms and 209.1 ms) and both holds of `ck_rep2_pc120_spawn10` (227.9 ms and 182.5 ms). It also stayed under 500 ms on both holds of `ck_cpu1000_pc120` (281.4 ms and 289.2 ms), and the over-500 share there is 0.42 on both, with streaks 116 and 113, so that arm is not latch-avoided.

## Controls

The six controls are run132 (released, blend yes), run134 (released, blend yes), run139 (sticky, blend no), run143 (other, blend no), run147 (sticky, blend no), and run151 (released, blend no, near-miss). The first and the last are both released. Two of six are sticky. The untouched mix changed mode inside the series and the last control released again. That is not a one-way late-day drift, and a single arm is still readable against that.

Block A's first three scored holds (run132, run133, run134) are all released. Block A's last three slots (run139, run140, run141) are sticky, released, and other. Block B's first three (run142, run143, run144) are sticky, other, and sticky. Block B's last three (run149, run150, run151) are sticky, released, and released. The end of block B is not stickier than its start.

## Steal and mode

Sticky (6 holds): master 0.09–0.24 (mean 0.14, n=6); worker 0.05–0.10 (mean 0.07, n=6); load 0.01–0.90 (mean 0.28, n=6).
Not sticky (14 holds): master 0.08–1.03 (mean 0.22, n=14); worker 0.05–0.18 (mean 0.10, n=14); load 0.01–1.95 (mean 0.53, n=14).

The ranges overlap on master, worker, and load. Steal does not separate sticky from the other classes. No scored hold has a node hold-mean above 2%, so none is a steal warning. The highest load hold-mean is run137 at 1.95%. The highest master hold-mean is run153 at 1.03%.

## Blends

6 of 20 scored holds are blends (run132, run134, run137, run146, run150, run153). Block A 3/8, block B 2/10, replacements 1/2. Near-misses among scored holds: run133, run135, run140, run148, run151.

Two holds are a screen. About eight holds of one configuration separate a 1-in-5 latch rate from a 3-in-5 latch rate.

## What to replay

Only a moved arm is a candidate for another hold, and a control stays in the interleave because the six controls are not one class.

- `ck_rep2_pc120` moved and the latch was avoided. Both holds are released blends, checkout streak 14 and 15, per-pod CPU about 405 m and 372 m against an 800 m limit.
- `ck_rep2_pc120_spawn10` moved and the latch was avoided. Both holds are released and neither is a blend. Run140 is a near-miss (recommendations streak 3, overloaded 301). Checkout streak 16 and 9.
- `ck_cpu1000_pc120` moved and the latch was not avoided. Both holds are released, and checkout streak stays above 30 (116 and 113).

`spawn10`, `recs_cpu1000`, `recs_cpu1000_spawn10`, and `ck_cpu1000_pc120_spawn10` are mixed.

## Comparison with the first probe

`ck_rep2_pc120` in the first probe (run115 and run123) was moved and latch-avoided: both released blends, sojourn 175.3 ms and 235.1 ms, per-pod checkout CPU 353.2 m and 369.6 m. Runs 137 and 150 land the same way.

The first probe's `ck_cpu1000` (run113 and run122, checkout 1000 m and postcheckout still 90) was latch-avoided, sojourn 110.8 ms and 103.2 ms. This series did not repeat that arm. `ck_cpu1000_pc120` adds postcheckout 120 and is not latch-avoided.

The first probe's `spawn10` (run109 and run120) was moved: both released blends, with getproduct already near its plateau about 10 s in. Here run133 is released and run142 is sticky.

## Handoff

Folders are under `experiments/results/new vms/`. Do not overwrite runs 128–153 or `new vms/_discarded/`. The next both-off slot is run154 (`experiments/configs/scenario_2_baseline_no_topfull.yaml`). The Paper-C1 restore gate passed before this close-out: checkout 800 m × 1, recommendations 1150 m × 1, frontend HPA min=max=4, catalog HPA min=max=1, sidecar request 100 m, `proxyCPULimit` unset. Stopping the three copy-project VMs is the last step of the close-out, after the push.

## Read next

- Service tables: [2026-10-04-s2-latch-probe-v2-abc.md](2026-10-04-s2-latch-probe-v2-abc.md).
- First probe: [2026-10-03-s2-latch-probe-results.md](2026-10-03-s2-latch-probe-results.md) and [2026-10-04-s2-latch-probe-abc.md](2026-10-04-s2-latch-probe-abc.md).
- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Why the two modes exclude each other: [2026-10-04-s2-checkout-latch.md](2026-10-04-s2-checkout-latch.md).
- Same mix, different landing: [2026-10-03-s2-same-mix-replays-differ.md](2026-10-03-s2-same-mix-replays-differ.md).
