# RetryGuard parameters are locked on every run with RetryGuard on

Every run with RetryGuard on uses one parameter set. The nine shared keys are `retry_metric` `edge_rpr`, `sample_interval_seconds` 1, `interval_samples` 20, `rejection_threshold` 0.2, `retries_threshold` 0.4, `climb_rpr_1_to_2` 0.16, `climb_rpr_2_to_3` 0.32, `climb_interval_seconds` 10, and `reenable_rejection` 0.25. Burst mode adds `burst_rpr` 2.0, `burst_window_seconds` 5, and `burst_min_first_attempts` 20. Normal mode uses those nine keys and leaves the three burst keys unset. Scenario 5 is the exception: it sweeps `interval_samples` and keeps the other locked keys.

The twelve S2 holds in [2026-10-12-s2-burst-matrix-abc.md](../../Guides%20and%20Info/history/2026-10-12-s2-burst-matrix-abc.md) (`experiments/configs/study_2026_10_12/03`–`14`) ran bars 1.5 and 2.0, two replicates each, TopFull off and TopFull on. That guide records both bars and stops there. The team chose `burst_rpr` 2.0 as the single bar and dropped 1.5. The burst handler those keys turn on is [ADR 0007](0007-burst-mode-sliding-aggregate.md).

**Status:** accepted.

**Considered options:** keep 1.5 and 2.0 both live, as the matrix guide does; lock 1.5; leave each scenario YAML free to set its own knobs.

**Consequences:** `campaign_48/`, `august_38/`, and other holds from before 2026-10-12 used different RetryGuard values and are not comparable to locked runs. The canonical table lives in [RETRYGUARD-IMPLEMENTATION.md](../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md).
