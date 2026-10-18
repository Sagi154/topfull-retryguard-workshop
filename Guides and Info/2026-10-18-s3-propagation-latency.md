# S3 propagation latency, both-burst and TopFull-only (2026-10-18)

Question: how long after RetryGuard sheds retries toward `checkoutservice` does the upstream caller's latency recover? The caller is `frontend`, and only `postcheckout` walks `frontend -> checkoutservice`, so the caller-side latency is the `postcheckout` Locust `Latency95` (ms). Holds are the same clean S3 holds as [2026-10-18-s3-goodput-fail-rate.md](2026-10-18-s3-goodput-fail-rate.md), under `experiments/results/final_runs_results/S3_targeted_bottleneck_burst` and `S3_targeted_bottleneck_normal`.

Counting rule, same as the other S3 files: a both-controllers hold with no `frontend->checkoutservice ON→OFF` in `retryguard.log` is a TopFull-only hold. That is `analysis_s3_both_normal_run1`–`run3`. They are pooled with `tf_only run1`–`run3` below.

## Definitions

- **Activation, t0:** the first `frontend->checkoutservice ON→OFF` line in `retryguard.log`. Timestamps are master UTC. Locust rows are about 1.07 s apart and carry a UTC `timestamp`, so no clock fit is needed.
- **High:** `postcheckout` `Latency95` at or above 2000 ms (the 2200 ms timeout plateau).
- **Relief:** the first Locust row at or after t0 from which `Latency95` stays under 1000 ms for 10 consecutive rows.
- **Last high:** the last row at or above 2000 ms before relief.
- Locust P95 is a rolling value, so edges are smeared by a second or two.

## Both burst (RetryGuard and TopFull on, RetryGuard sheds)

| Run | t0 (shed) | TopFull first `postcheckout` cap | First high row | Last high row | Last high − t0 (s) | Relief − t0 (s) | Sheds in hold |
|---|---|---|---|---|---:|---:|---:|
| `analysis_s3_both_burst_run1` | 15:27:33 | 15:27:30 | 15:27:30 | 15:27:35 | 2.4 | 3.5 | 3 |
| `analysis_s3_both_burst_run2` | 15:46:24 | 15:46:15 | 15:46:21 | 15:46:26 | 2.7 | 3.7 | 4 |
| `analysis_s3_both_burst_run3` | 22:23:06 | 22:22:55 | 22:23:01 | 22:23:07 | 1.3 | 2.4 | 1 |
| Mean of three | | | | | 2.1 | **3.2** | |

Each shed fired `metric=rpr_burst`, `from_attempts=3`. After relief the median `postcheckout` P95 over the next 30 s is 415, 525, and 510 ms. Only the first shed is timed. Runs 1 and 2 shed again after an `OFF→ON`, and those later sheds are not scored.

## TopFull only (no RetryGuard shed)

There is no RetryGuard activation here, so there is no t0 and no delta. What the same signal does without a shed:

| Run | Source | First high row (s after first TopFull cap) | First high stretch (rows) | High stretches in hold | Mean stretch (rows) | Seconds at or above 2000 ms | Seconds at or above 1000 ms |
|---|---|---:|---:|---:|---:|---:|---:|
| `analysis_s3_tf_only_run1` | `tf_only` | −0.5 | 6 | 33 | 5.2 | 30.4% | 36.8% |
| `analysis_s3_tf_only_run2` | `tf_only` | 5.3 | 6 | 33 | 5.1 | 30.0% | 36.1% |
| `analysis_s3_tf_only_run3` | `tf_only` | 7.7 | 5 | 34 | 5.1 | 30.4% | 37.7% |
| `analysis_s3_both_normal_run1` | `both`, no shed | 10.6 | 6 | 33 | 5.0 | 29.2% | 35.9% |
| `analysis_s3_both_normal_run2` | `both`, no shed | 10.2 | 5 | 32 | 5.1 | 28.8% | 35.9% |
| `analysis_s3_both_normal_run3` | `both`, no shed | −1.2 | 5 | 34 | 5.1 | 30.3% | 37.0% |

The six TopFull-only holds agree: the first high stretch is 5–6 rows (about 5.5 s) and clears on its own. After that the stretches recur 32–34 times per hold, each about 5 rows (about 5.5 s), so `postcheckout` spends about 30% of its seconds at the timeout plateau. Median `postcheckout` P95 is 310–400 ms per hold.

## Reading

- **Delta after a shed:** 2.4, 3.5, and 3.7 s from the shed to relief on `both_burst`, about 3 s on average, all under one 5 s polling slot.
- **That delta is not clearly caused by the shed.** The first high stretch on a hold with no shed lasts 5–6 rows. The `both_burst` first stretches last about 6 s (run1 15:27:30–35, run2 15:46:21–26, run3 22:23:01–07), and the shed lands in the middle of them. So a stretch ending 1–4 s after the shed is what TopFull-only holds do with no shed at all. These three holds cannot separate "RetryGuard relieved it" from "the stretch ended".
- **After the first stretch, `both_burst` looks different from TopFull only.** Run 1 P95 sits near 550 ms with brief 1100 ms ticks, and there is no recurring 2200 ms sawtooth in the first 415 s of any of the three holds (the window I checked). TopFull-only holds keep the sawtooth. That is a difference in steady state, not a propagation delay, and it is not a 3 s effect. It is the same effect as the goodput and P95 tables in [2026-10-18-s3-variant-p95.md](2026-10-18-s3-variant-p95.md); this file does not size it.
- **CPU relief is not resolved.** `resource_usage.csv` polls every 5 s and the kubelet value often repeats for two polls, so a delta of about 3 s sits inside one sample. The first shed on `both_burst` also lands within 10 s of the first CPU rows, so there is no steady "before". No CPU delta is reported.
- **Per-hop latency is not available.** Outbound `upstream_rq_time` on `service_edges.csv` is structurally zero on this cluster ([METRICS-GATHERED.md](METRICS-GATHERED.md)). The frontend inbound sojourn mixes all five APIs.
- **RetryGuard-only holds** are the cleaner timing source (a shed with no TopFull cap running). They are not in this file's scope. Sample: `analysis_s3_rg_only_normal_run1` shed at 13:45:52 with P95 recovered at 13:45:57, about 5 s.
