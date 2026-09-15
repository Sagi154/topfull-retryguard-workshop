# S1/S2 Baseline Metric Readout (post-perTryTimeout, e2-standard-8)

**Date:** 2026-09-15 (UTC evening 2026-09-14)
**These are post-campaign checkpoint holds**, stored under the `campaign_48/` tree. They are **not** new 48-run matrix rows. The original campaign folders are unchanged.

| | S1 (normal op) | S2 (sustained overload) |
|---|---|---|
| Verdict | **DEGRADED vs run20** (load stressed on 8-vCPU worker) | **PARTIAL / truncated collectors** |
| Slot | `baseline_topfull_no_retryguard_normal_op_run21` | `baseline_topfull_no_retryguard_sustained_overload_run20` |
| Local path | `experiments/results/campaign_48/S1_normal_op/…_run21/` | `experiments/results/campaign_48/S2_sustained_overload/…_run20/` |
| Duration (YAML) | 300 s | 600 s |
| Locust rows | 266 (full S1 shape) | **282** (truncated vs ~525 campaign shape) |
| RetryGuard | off | off |
| Mesh transport | `network_prometheus` | `network_prometheus` |
| Collected at | 2026-09-14T21:48:20Z | 2026-09-14T22:18:06Z |

---

## 0. Infra note (quota resize)

Before launch, all three VMs were `TERMINATED` but sized at `e2-standard-32` / `e2-standard-32` / `e2-standard-16` (80 vCPU). Project `CPUS_ALL_REGIONS` quota is **32**, so they could not start together. Per [infra/vm-ips.env](../../../infra/vm-ips.env) and SETUP-GUIDE (`e2-standard-8`), all three were resized to **`e2-standard-8`** (24 vCPU total) and started. Cool-off between runs: **300 s**. VMs stopped after pull.

This is the first S1/S2 baseline pair after `perTryTimeout: 500ms`, but also the first on the restored 8-vCPU footprint. Numbers are **not** directly comparable to the 2026-09-13 checkpoint (S1 run20 / S2 run17), which ran on the larger machines.

---

## 1. Slots

| Key | Value |
|---|---|
| S1 `run_number` | 21 |
| S1 `log_folder` | `baseline_topfull_no_retryguard_normal_op_run21` |
| S2 `run_number` | 20 |
| S2 `log_folder` | `baseline_topfull_no_retryguard_sustained_overload_run20` |

YAMLs after close-out: S1 → **run22**, S2 → **run21**.

---

## 2. File inventory

Both folders: required 17-file baseline set present; `retryguard.log` and legacy `envoy_retries_*.csv` absent. `num_agent.csv` present (allowed).

| File | S1 bytes | S2 bytes |
|---|---:|---:|
| emptycart.csv | 6140 | 6500 |
| getcart.csv | 6961 | 7332 |
| getproduct.csv | 6580 | 6831 |
| postcart.csv | 6145 | 6525 |
| postcheckout.csv | 6022 | 6658 |
| total.csv | 7620 | 8453 |
| num_agent.csv | 756 | 243 |
| resource_usage.csv | 41158 | 32807 |
| service_edges.csv | 3184943 | 2561989 |
| service_inbound.csv | 225426 | 192436 |
| topfull_detect.csv | 215498 | 163055 |
| topfull_throttle.csv | 81603 | 62077 |
| service_capacity.json | 1306 | 1306 |
| run_manifest.json | 1287 | 1298 |
| collector logs | present | present (throttle log has many timeouts) |

S2 Locust / mesh / throttle series are **shorter than a full 600 s hold** (see §7).

---

## 3. Locust means (skip first 30 rows)

| Endpoint | S1 Fail | S2 Fail | S1 P95 | S2 P95 | S1 RPS | S2 RPS | S1 Goodput | S2 Goodput | S1 rej | S2 rej |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| getcart | **69.83** | **131.68** | **1696.2** | **2741.3** | 138.82 | 135.56 | 68.98 | 3.88 | 0.503 | 0.971 |
| getproduct | 41.65 | 59.09 | 1321.4 | 2842.1 | 89.97 | 60.95 | 48.32 | 1.86 | 0.463 | 0.969 |
| postcheckout | 2.00 | 11.61 | 1088.0 | 2213.3 | 9.46 | 12.35 | 7.46 | 0.74 | 0.211 | 0.940 |
| postcart | 0.00 | 1.21 | 278.4 | 485.8 | 69.28 | 66.65 | 69.28 | 65.44 | 0.000 | 0.018 |
| emptycart | 0.00 | 1.09 | 165.2 | 430.9 | 69.96 | 68.09 | 69.96 | 67.01 | 0.000 | 0.016 |
| total | 113.48 | 204.67 | 909.8 | 1742.7 | 377.49 | 343.60 | 264.01 | 138.92 | 0.301 | 0.596 |

Compare S1 run21 vs prior S1 run20 (32-vCPU worker era): getcart Fail **69.83 vs 0.79**, P95 **1696 vs 907**. S1 “normal op” is no longer cool on `e2-standard-8` at these user counts.

---

## 4. Mesh retries / 5xx / resets

### Outbound (`service_edges.csv`) — edges with `retry > 0`

| Edge | S1 retry min..max (Δ) | S2 retry min..max (Δ) |
|---|---|---|
| frontend → recommendationservice | 0..3338 (**+3338**) | 34262..201169 (**+166907**) |
| frontend → cartservice | 0..150 (+150) | 150..150 (**0**, leftover) |
| frontend → checkoutservice | 0..9 (+9) | 9..9 (**0**, leftover) |
| frontend → productcatalogservice | 0 | 0 |

Hot cart/checkout/productcatalog edges: S2 **did not** grow retries during the hold (flat at S1 leftovers). The storm that did fire is **frontend → recommendationservice**.

Outbound `5xx` on hot edges stayed **0** both runs. `2xx`/`total` advanced on both.

### Inbound (`service_inbound.csv`)

| Service | S1 5xx max | S2 5xx max | S1 resets max | S2 resets max |
|---|---:|---:|---:|---:|
| frontend | **1151** | **98593** | 259 | **1575** |
| recommendationservice | 0 | 0 | **2281** | **142163** |
| cartservice | 0 | 0 | 150 | 189 |
| checkoutservice | 0 | 0 | 5 | 5 |
| productcatalogservice | 0 | 0 | 34 | 74 |
| others | 0 | 0 | small | small |

`perTryTimeout` is producing **resets** and **retries** (unlike 2026-09-13 run20/run17 where both were 0). Signal is concentrated on frontend / recommendationservice, not the cart/checkout hot path that prior §7b S2 run19 highlighted for checkout.

---

## 5. Layer A / Layer B / Layer 2

### Layer A (`topfull_throttle.csv`)

| | S1 | S2 |
|---|---|---|
| rows | 1655 | 1260 |
| `threshold_fresh==1` | 19.9% (330) | **4.0%** (50) |
| fresh threshold values | **only 10000** | **only 10000** |
| admitted mean (fresh) | 69.15 | 45.54 |
| all-zero? | no | no |

TopFull never left the uncapped sentinel (`threshold=10000`). S2 throttle log is full of `thresholds/stats fetch failed: timed out` after ~22:08Z.

### Layer B (`topfull_detect.csv`) — max utilization

| Service | Quota | α | S1 max util | S2 max util | S1 / S2 overloaded |
|---|---:|---:|---:|---:|---|
| adservice | 1000 | 0.80 | **0.803** | 0.178 | **1** / 0 |
| frontend | 1000 | 0.80 | 0.772 | **0.688** | 0 / 0 |
| productcatalogservice | 500 | 0.95 | 0.588 | 0.572 | 0 / 0 |
| cartservice | 1000 | 0.95 | 0.546 | 0.454 | 0 / 0 |
| recommendationservice | 2000 | 0.80 | 0.511 | 0.581 | 0 / 0 |
| currencyservice | 1000 | 0.80 | 0.469 | 0.478 | 0 / 0 |
| checkoutservice | 1000 | 0.80 | 0.278 | 0.275 | 0 / 0 |
| others | — | — | <0.10 | <0.09 | 0 / 0 |

S1 had **one** overloaded sample (adservice once above α). S2 overloaded sum = 0.

### Layer 2 (`resource_usage.csv`)

11 services both runs. S1 frontend max CPU **695** m / mem **64.6 MB**; S2 frontend **616** m / **78.8 MB**. Hottest S2 CPU: recommendationservice **1059** m.

---

## 6. Collector time spans

| Series | S1 span | S2 span |
|---|---|---|
| Locust rows | 266 (~full 300 s) | **282** (not ~525) |
| mesh edges/inbound | 390 s, 391 polls | 489 s, **313 polls** (gaps) |
| throttle / detect | 330 s | 489 s wall, but SHUTDOWN at 22:10:17Z |
| resource | 360 s | 485 s |

S2 runner held Locust for the full 600 s wall clock (01:07:54 → 01:17:54 local). Mesh/throttle CSVs stop at **22:10:17Z** (~2.5 min after Locust start) with `SHUTDOWN signal=15`. Metric collector only wrote ~282 Locust rows. Most likely cause: **master OOM / process kill under S2 load on e2-standard-8**, not a runner early-exit.

---

## 7. Ready / not ready

**Usable for:** confirming collectors still write the full METRICS-GATHERED file set; confirming `perTryTimeout` produces non-zero `retry`/`resets` (recommendationservice / frontend); S1-vs-S2 Locust Fail/P95 direction on the truncated S2 window.

**Not ready for:** paper-grade S1 “cool baseline” claims on this hardware (S1 is stressed); full 600 s S2 analysis; claiming a cart/checkout retry storm (those edges flat on S2); claiming TopFull throttled (threshold stayed 10000).

**Do not** treat these folders as replacements for `campaign_48/` matrix rows or the 2026-09-13 run20/run17 checkpoint. Do not overwrite `august_38/`.

---

## 8. YAML slots after this readout

| File | Next `run_number` | Next `log_folder` |
|---|---|---|
| `experiments/configs/scenario_1_baseline.yaml` | 22 | `baseline_topfull_no_retryguard_normal_op_run22` |
| `experiments/configs/scenario_2_baseline.yaml` | 21 | `baseline_topfull_no_retryguard_sustained_overload_run21` |

**Follow-up:** restore a worker large enough for S1 to stay cool (or lower S1 `user_counts`), then re-run a full-duration S2 before using these slots for analysis. Keep `perTryTimeout: 500ms`.
