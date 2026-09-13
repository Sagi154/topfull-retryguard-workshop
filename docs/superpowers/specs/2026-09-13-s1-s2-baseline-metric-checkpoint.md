# S1/S2 Baseline Metric Checkpoint

**Date:** 2026-09-13
**Plan:** [2026-09-13-s1-s2-baseline-metric-checkpoint.md](../plans/2026-09-13-s1-s2-baseline-metric-checkpoint.md)
**These are post-campaign checkpoint holds**, stored under the `campaign_48/` tree. They are **not** new 48-run matrix rows. The original campaign folders are unchanged.

| | S1 (normal op) | S2 (sustained overload) |
|---|---|---|
| Verdict | **PASS** | **FAIL on retry gates only** |
| Slot | `baseline_topfull_no_retryguard_normal_op_run20` | `baseline_topfull_no_retryguard_sustained_overload_run17` |
| Local path | `experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run20/` | `experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run17/` |
| Duration | 300 s | 600 s |
| RetryGuard | off | off |
| Mesh transport | `network_prometheus` on `topfull-master` | `network_prometheus` on `topfull-master` |
| Collected at | 2026-09-13T13:39:18.659169Z | 2026-09-13T14:03:41.021675Z |

Controller adjudication of Task 9 is written here as specified. Do not re-litigate.

---

## 1. Slots

Locked by Task 1; launched as-is (YAMLs were not bumped before launch).

| Key | Value |
|---|---|
| S1 `run_number` | 20 |
| S1 `log_folder` | `baseline_topfull_no_retryguard_normal_op_run20` |
| S2 `run_number` | 17 |
| S2 `log_folder` | `baseline_topfull_no_retryguard_sustained_overload_run17` |

Both folders now exist locally and on master. After this checkpoint, YAMLs were bumped so the next launch cannot overwrite them (S1 → **run21**, S2 → **run18**). run21 / run18 were confirmed absent locally and on master before the bump.

Collectors stayed on (`envoy_retry_collector`, `resource_usage_collector`, `topfull_throttle_collector`). Locust `user_counts` / `spawn_rate` / durations were not changed.

---

## 2. Dirty / clean notifies

Task 2 (before S1) and Task 6 (before S2) both printed:

`NOTIFY: environment is dirty`

Leftovers were **stale master `/tmp` scripts only**. No live experiment processes, no tmux, no Locust on either inspect.

| Task | When | Leftovers (master `/tmp` only) | After clean |
|---|---|---|---|
| Task 2 | before S1 | `envoy_retry_params.json`, `rg_envoy_retry.sh`, `rg_mc.sh`, `rg_proxy.sh`, `rg_resource_usage.sh`, `rg_rl.sh` | clean |
| Task 6 | after 180 s cool-off, before S2 | same as Task 2 plus `rg_topfull_throttle.sh` (S1 leftovers) | clean |

Task 6 skipped extra sleep: Task 3 runner ended 16:39:07 local; inspect clock 16:46:00 (**413 s** already elapsed vs 180 s required).

Paper CPU table held both times (checkout **1000m**, not a leftover S3 100m). All 10 VirtualServices had `retries.attempts: 3`.

---

## 3. Per-file inventory

Both folders: `missing []`, `unexpected []`. All 16 required files present and non-empty. Forbidden baseline/legacy files absent (`retryguard.log`, `envoy_retries_frontend.csv`, `envoy_retries_checkoutservice.csv`). `num_agent.csv` is present and allowed (not a required metric).

### S1 run20

| File | Bytes | Notes |
|---|---:|---|
| emptycart.csv | 6150 | 267 lines / 266 data rows |
| envoy_retry_collector.log | 170 | |
| getcart.csv | 6706 | 267 / 266 |
| getproduct.csv | 6376 | 267 / 266 |
| num_agent.csv | 765 | allowed |
| postcart.csv | 6152 | 267 / 266 |
| postcheckout.csv | 6144 | 267 / 266 |
| resource_usage.csv | 40453 | |
| resource_usage_collector.log | 127 | |
| run_manifest.json | 1344 | `duration_seconds: 300` |
| service_capacity.json | 1306 | |
| service_edges.csv | 3163715 | mesh outbound |
| service_inbound.csv | 223080 | mesh inbound |
| topfull_detect.csv | 214295 | Layer B |
| topfull_throttle.csv | 81694 | Layer A |
| topfull_throttle_collector.log | 140 | |
| total.csv | 7213 | 267 / 266 |

Locust row count is the same full-hold shape as campaign S1 run4–6 (265–269 data rows), not a truncated scrape. Brief ~300 is not matched because the metric collector does not emit a row for every wall-clock second.

### S2 run17

| File | Bytes | Notes |
|---|---:|---|
| emptycart.csv | 12111 | 526 lines / 525 data rows |
| envoy_retry_collector.log | 170 | |
| getcart.csv | 13704 | 526 / 525 |
| getproduct.csv | 13360 | 526 / 525 |
| num_agent.csv | 1215 | allowed |
| postcart.csv | 12123 | 526 / 525 |
| postcheckout.csv | 12599 | 526 / 525 |
| resource_usage.csv | 74891 | |
| resource_usage_collector.log | 100 | |
| run_manifest.json | 1355 | `duration_seconds: 600` |
| service_capacity.json | 1306 | |
| service_edges.csv | 5633159 | mesh outbound |
| service_inbound.csv | 402279 | mesh inbound |
| topfull_detect.csv | 410491 | Layer B |
| topfull_throttle.csv | 156112 | Layer A |
| topfull_throttle_collector.log | 14761 | larger than S1 (live scrape log) |
| total.csv | 15742 | 526 / 525 |

525 data rows matches campaign S2 baseline run4–6 (523–526). Same collector shape as a full 600 s hold.

---

## 4. S1 / S2 Locust means

Means skip the first 30 Locust rows (S1: 266 → 236 used; S2: 525 → 495 used).

| Endpoint | S1 Fail | S2 Fail | S1 P95 | S2 P95 | S1 RPS | S2 RPS | S1 Goodput | S2 Goodput |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| getcart | **0.79** | **161.17** | **906.8** | **2197.8** | 149.97 | 163.4 | 149.18 | 2.24 |
| getproduct | 0.0 | 103.06 | 845.3 | 1490.5 | 99.37 | 104.52 | 99.37 | 1.46 |
| postcheckout | 0.0 | 13.56 | 477.1 | 1247.5 | 10.0 | 18.07 | 10.0 | 4.51 |
| postcart | 0.0 | 0.01 | 311.9 | 440.7 | 74.11 | 81.45 | 74.11 | 81.44 |
| emptycart | 0.0 | 0.01 | 229.5 | 308.2 | 74.53 | 80.68 | 74.53 | 80.67 |
| total | 0.79 | 277.81 | 554.1 | 1136.9 | 407.98 | 448.12 | 407.18 | 170.32 |

S1 getcart vs references (skip first 30):

| Run | Role | Fail | P95 |
|---|---|---:|---:|
| run20 | this checkpoint | **0.79** | **906.8** |
| run10 | both-off credit | 1.54 | 900.4 |
| run7 | old both-on docker-local | 29.16 | 1374.1 |

S1 is run10-like, not docker-local tax. Leftover collector tax vs run10 is **~+6 ms** getcart P95 (+6.4 ms; well inside the +37 ms HTTP-transport credit / `< 1200` bound).

S2 Fail/P95 is campaign-overload shaped (run4 getcart Fail 153.96 / P95 1563.4), not an S1-like cool hold. Load engaged.

---

## 5. Mesh 2xx / retry

`transport: network_prometheus`, `exec_host: topfull-master`, `max_workers: 4` on both manifests. Inbound unique services = all 11 Boutique names on both runs.

### S1 run20 — edges live, retry 0

- Edges `2xx` max **1044136**; `retry` max **0**.
- Frontend hot-edge `2xx`: `productcatalogservice` 1044136, `cartservice` 259961. 13 pairs with `2xx > 0`.

### S2 run17 — edges live and increasing, retry 0

- Edges `2xx` max **2120831**; `retry` max **0** (global unique `{0}`, sum 0).
- Frontend hot-edge `2xx` / `retry`:

| target | 2xx min / max | 5xx min / max | retry min / max |
|---|---|---|---|
| cartservice | 259961 / 523656 | 0 / 0 | **0 / 0** |
| checkoutservice | 6842 / 17898 | 0 / 0 | **0 / 0** |
| productcatalogservice | 1044136 / 2120831 | 0 / 0 | **0 / 0** |

Inbound `5xx` max is **0** on all 11 services. S2 `2xx` counters advance (productcatalog +1.08M over the scrape); `retry` does not.

**Interpretation (do not soften the FAIL label):** Locust Fail is SLO-miss (`>1s`) with inbound/outbound **5xx = 0**, so Istio retries never fire and Envoy `retry` stays 0. That is a **measurement finding**, not a missing CSV / dead collector.

---

## 6. Layer A freshness / Layer B overloaded

| | S1 run20 | S2 run17 |
|---|---|---|
| Layer A `threshold_fresh==1` | **20%** (330/1650) | **1%** (55/3150) |
| Admitted mean on `admitted_fresh==1` | **73.34** | **55.67** (max 169.0; not all-zero) |
| Layer A all-zero numeric cols? | no | no |
| Layer B `cadvisor_cpu>0` | True (3486/3630, max 727.0) | True (6786/6930, max 737.0) |
| Layer B `overloaded` | **0** | **0** (frontend max util **0.727**; S2 **0.737**) |
| Resource services | 11; frontend mem>0 (max 48410624) | 11; frontend mem>0 (max 63119360) |

S2 fresh=1% under saturation is allowed. Detector did not flag overload while Locust Fail was ~98% on getcart — recorded, not a listed FAIL trigger.

### Layer B per-service utilization

`topfull_detect.csv` columns: `cadvisor_cpu`, `quota`, `alpha`, `utilization` (`cadvisor_cpu / quota`), `overloaded` (`utilization > alpha`). α is constant per service on both holds: **0.95** for `productcatalogservice` / `cartservice`, **0.8** for the other nine. Quota is the paper table (catalog **500**, recommendation **2000**, everyone else **1000**). `overloaded` sum is **0** on both runs (330 rows/service on S1, 630 on S2). Hottest service both times: **frontend** (S1 peak 727/1000 at `2026-09-13T13:39:03Z`; S2 peak 737/1000 at `2026-09-13T13:55:25Z`). Neither frontend (needs >0.8) nor catalog (needs >0.95) crossed α.

| Service | Quota | α | S1 max util | S2 max util | S1 / S2 overloaded |
|---|---:|---:|---:|---:|---|
| frontend | 1000 | 0.80 | **0.727** | **0.737** | 0 / 0 |
| productcatalogservice | 500 | 0.95 | 0.576 | 0.528 | 0 / 0 |
| recommendationservice | 2000 | 0.80 | 0.2975 | 0.308 | 0 / 0 |
| currencyservice | 1000 | 0.80 | 0.272 | 0.328 | 0 / 0 |
| checkoutservice | 1000 | 0.80 | 0.212 | 0.317 | 0 / 0 |
| cartservice | 1000 | 0.95 | 0.197 | 0.170 | 0 / 0 |
| adservice | 1000 | 0.80 | 0.129 | 0.169 | 0 / 0 |
| shippingservice | 1000 | 0.80 | 0.086 | 0.085 | 0 / 0 |
| emailservice | 1000 | 0.80 | 0.044 | 0.067 | 0 / 0 |
| paymentservice | 1000 | 0.80 | 0.037 | 0.041 | 0 / 0 |
| redis-cart | 1000 | 0.80 | 0.022 | 0.022 | 0 / 0 |

Layer A context (not a detector threshold): every `threshold_fresh==1` row had `threshold = 10000` (uncapped sentinel). S2 `threshold = 0` rows are stale (`threshold_fresh=0`).

---

## 7. Pass / fail

### S1 run20 — **PASS**

All 8 Task 5 gates hold. getcart Fail 0.79 / P95 906.8 vs run10 1.54 / 900.4. Mesh 2xx live. Layer A 20% fresh.

### S2 run17 — **FAIL on retry gates only**

Plan required frontend hot-edge retry `max > min` and S2 retries > S1. Those two failed. All other S2 gates **PASS**:

| Gate | Result |
|---|---|
| File set complete; `transport: network_prometheus` | PASS |
| Locust rows are a full 600 s series (525 = campaign shape) | PASS |
| getcart / getproduct / postcheckout Fail elevated vs S1 | PASS (161.17 / 103.06 / 13.56) |
| Frontend hot-edge `2xx` max `> 0` | PASS |
| Frontend hot-edge `retry` increases (`max > min`) | **FAIL** (0 / 0) |
| Resource + detect CSVs have real CPU/memory | PASS |
| Layer A not all-zero on fresh rows (fresh=1%, admitted mean 55.67) | PASS |
| Cross: S1 Fail << S2 Fail on getcart | PASS (0.79 << 161.17) |
| Cross: S1 P95 << S2 P95 on getcart | PASS (906.8 << 2197.8) |
| Cross: S2 retries > S1 retries | **FAIL** (both retry max 0) |

FAIL triggers that did **not** fire: missing mesh/throttle files; edges `2xx` all zero; Layer A all zeros; S2 Fail/P95 indistinguishable from S1 (load never engaged).

---

## 8. Ready / not ready for scenario analysis

**Collector stack is usable.** Ready for scenario analysis of goodput / P95 / rejection / CPU / mesh 2xx-5xx / Layer A-B.

**Not** ready to claim a retries-per-request storm from these two folders. Envoy `retry` stayed 0 on both; Locust Fail is an SLO-miss with mesh 5xx = 0.

Do not treat these folders as replacements for `campaign_48/` matrix rows run4–6. Do not overwrite `august_38/`.

---

## 9. YAML slots after this checkpoint

| File | Next `run_number` | Next `log_folder` |
|---|---|---|
| `experiments/configs/scenario_1_baseline.yaml` | 21 | `baseline_topfull_no_retryguard_normal_op_run21` |
| `experiments/configs/scenario_2_baseline.yaml` | 18 | `baseline_topfull_no_retryguard_sustained_overload_run18` |

Keep 300 s / 600 s, collectors on, `transport: network_prometheus`. S6 YAMLs still point at completed `run3` (unrelated overwrite trap).

---

## 10. Standing reminder (where we are)

Facts from S1 run20 / S2 run17. Use this as the current picture; what to address next is still open.

**1. Both runs had no retries.**
Envoy `retry` stayed **0** on every edge. RetryGuard was off. VirtualServices still had `attempts: 3`, but Istio retries never fired because they need **5xx**, and no new 5xx appeared during these holds.

**2. TopFull did not throttle.**
Every *fresh* Layer A scrape had `threshold = 10000` (uncapped sentinel). It never dropped. S2 `threshold = 0` rows are stale (`threshold_fresh=0`), not a real cap. Layer B `overloaded` was **0** on both (frontend CPU util peaked at 0.74). The proxy stayed in the path; the RL admission cap never engaged.

**3. Locust `Fail` here is “took longer than 1 s.”**
Locust marks `Fail` if `elapsed > 1s` **or** HTTP is not OK. The §4 table is **mean Fail RPS** (skip first 30 rows), not a raw count. On S2, getcart Fail 161 vs RPS 163 means ~98% of completed getcart calls missed the 1 s SLO.

**4. HTTP status was effectively all 2xx — not a literal “every request.”**
During these holds: inbound `4xx = 0`, inbound `5xx = 0` on all 11 services; outbound `4xx = 0`. The only outbound `5xx` is a leftover **22** on `frontend → adservice` that was already 22 at the start of S1 and **did not increase** through S2. A slow getcart that Locust calls Fail is typically still **HTTP 200**. Caveats: redis-cart is not HTTP (inbound 2xx stays 0); a small `total − 2xx − 4xx − 5xx` leftover exists (in-flight / non-HTTP codes).

**So:** S2 can look broken at Locust (high Fail, getcart P95 ~2.2 s) while the mesh looks healthy (2xx climbing, 5xx/retry 0) and TopFull never caps. Collector stack is usable for goodput / P95 / rejection / CPU / mesh 2xx-5xx / Layer A-B. **Not** ready to claim a retries-per-request storm from these two folders.
