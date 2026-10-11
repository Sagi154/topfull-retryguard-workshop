# S2 tuning holds (2026-10-11): reenable 0.25, interval 20 s, climb 10 s

**Holds:** `study4_s2_tune_rgtf0_rep1`, `study4_s2_tune_rgtf1_rep1`, `study4_s2_tune_rgtf0_rep2`, `study4_s2_tune_rgtf1_rep2`, plus hold-1 replay `study4_s2_tune_rgtf0_rep1_r2` (replay of rep1, not scored in the table below). Folders under `experiments/results/campaign_48/S2_sustained_overload/`.
**Run log:** [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md)

## Setup

- Locked S2 mix 275 / 90 / 100 / 90 / 5, `spawn_rate` 50, 600 s, Paper-C1, frontend pinned at 4.
- Tuned RetryGuard: `retries_threshold` 0.4 (shed bar rpr > 0.40), `reenable_rejection` 0.25, `interval_samples` 20, `climb_rpr_1_to_2` 0.16, `climb_rpr_2_to_3` 0.32, `climb_interval_seconds` 10.
- TopFull off on rgtf0, on on rgtf1.

## Gate

Locust `total.csv` 566–571 rows (inside 540–580). `retryguard.log` START on all four carries the tuned set. No `PATCH_FAIL`, no traceback. Mesh inbound gaps ≥ 1.5 s: 0 of about 7300 samples on each hold.

## (a) Edge rpr, shed streak on frontend → checkoutservice

| Hold | streak s / ticks above 0.40 | mean rpr | max rpr |
| --- | --- | --- | --- |
| rgtf0 rep1 | 22 / 249 | 0.405 | 2.79 |
| rgtf1 rep1 | 8 / 207 | 0.826 | 6.64 |
| rgtf0 rep2 | 22 / 69 | 0.153 | 3.00 |
| rgtf1 rep2 | 8 / 199 | 0.811 | 6.00 |

Climb streaks on the one edge that climbed: rgtf0 rep1 5 (1-attempt), rgtf0 rep2 2 (1-attempt). No 2-attempt climb on any hold.

## (b) Rejection context (not the shed signal)

Checkoutservice rejection above 0.20: 26 / 280 (rgtf0 rep1), 9 / 204 (rgtf1 rep1), 25 / 180 (rgtf0 rep2), 8 / 189 (rgtf1 rep2). Recommendationservice and productcatalogservice never exceeded 0.20.

## (c) Toggles

Counted from `retryguard.log` transitions (`from_attempts` → `attempts`): rgtf0 rep1 11 disable / 10 re-enable (replay `_r2`: 9 / 9); rgtf0 rep2 3 disable / 3 re-enable; rgtf1 rep1 and rgtf1 rep2 0 / 0. No climb transitions on any hold.

## Reading

- TopFull on (rgtf1) holds gave higher checkout rpr and no toggles at all, while TopFull off toggled 3 to 11 times. With TopFull on, the checkout edge stays above the shed bar longer and RetryGuard never disables retries, so the retry relief that TopFull off gets is absent.
- The climb bars were never exercised beyond one 1-attempt climb on rgtf0 rep1 and one on rgtf0 rep2, so the 10 s climb has little evidence yet.
- The hold-1 replay was started before the 5 s live scrape was separated from the 1 s `rate_config` rows. Both folders pass the live-cap gate. The table uses rep1.
