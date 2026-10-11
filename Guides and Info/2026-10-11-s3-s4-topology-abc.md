# S3 / S4A / S4B topology holds (2026-10-11)

**Holds:** 10, one TopFull-off and one TopFull-on per variant. Folders under `experiments/results/campaign_48/`:
- S3 checkoutservice 300m: `S3_targeted_bottleneck/study4_s3_ck300_rgtf{0,1}`
- S4A productcatalogservice 400m, postcart 140 / 190: `S4A_topology_position_A/study4_s4a_pc400_u{140,190}_rgtf{0,1}`
- S4B emailservice 50m / 60m: `S4B_topology_position_B/study4_s4b_em{50,60}_rgtf{0,1}`

**Run log:** [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md)

## Setup

- Locked S1 mix 175 / 30 / 70 / 90 / 5 (S4A varies postcart), `spawn_rate` 50, 600 s, Paper-C1, frontend pinned at 4.
- Same tuned RetryGuard set as the S2 tuning holds.

## Gate

Locust `total.csv` 567–574 rows on all ten. `retryguard.log` START carries the tuned set on all ten, no `PATCH_FAIL` or traceback. Mesh inbound gaps ≥ 1.5 s: 0 on nine holds; **77 of 7238 on S4A u140 rgtf1 and 297 of 7018 on S4A u190 rgtf1**. Those two holds have mesh sample gaps and should be read with that caveat. S4B emailservice dropped to 0–1 replicas on 77–149 samples across all four S4B holds, so the email CPU limit was not the only thing that changed. The runner was not designed to check replicas for these services.

## (a) Shed streak on frontend → checkoutservice (edge rpr, seconds above 0.40)

| Variant | TF off | TF on |
| --- | --- | --- |
| S3 checkout 300m | 22 / 23 ticks | 10 / 297 ticks |
| S4A productcatalog 400m, postcart 140 | 0 / 0 | 0 / 0 |
| S4A productcatalog 400m, postcart 190 | 0 / 0 | 0 / 0 |
| S4B email 50m | 10 / 58 | 7 / 181 |
| S4B email 60m | 6 / 33 | 5 / 46 |

checkoutservice → emailservice never crossed the shed bar on any hold (0 streak). Climb streaks were not reached on any hold.

## (c) Toggles

Counted from `retryguard.log` transitions: S3 TF off logged 1 disable and 0 re-enable; the other nine holds logged 0 transitions.

## Reading

- S3 is the only variant where the edge rpr crossed the shed bar for a meaningful stretch on both arms. TopFull on sustained it far longer (297 ticks) than off (23).
- S4A never crossed the shed bar on either arm at either postcart count. Productcatalog at 400m did not produce an rpr signal at the frontend → checkout edge.
- S4B crossed the shed bar at a modest level on both arms, a bit more with TopFull on. The email replica dips make S4B less clean than the CPU change alone would suggest.
- RetryGuard toggled once, in S3 TF off. Most holds did not exercise the disable path, so the topology comparison is weak on controller behavior. The rpr differences are the stronger signal here.
- Controller-side gap: the S3 TF on hold had a 297-tick shed streak with zero RetryGuard transitions, so RetryGuard did not act on sustained high rpr there. That needs a look before this is cited as evidence.
