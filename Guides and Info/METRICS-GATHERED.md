# Metrics we gather

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Comprehensive inventory of every metric collected during experiment runs: sources, columns, derived values, clocks, and what is empty or unused. **For the "why do we collect this" narrative (rationale per metric, mapped to the eval deck's open questions), see [METRICS-CATALOG.md](METRICS-CATALOG.md) instead — that doc is the companion "how + why" read; this one stays the columns/files inventory.** How a hold is scored from these files: [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md) and `python experiments/analysis_score.py <run_dir>`. Operational details (how to pull, verify, load) live in [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md). Gaps and what is answerable: [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md). RetryGuard’s use of these CSVs: [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md) (canonical parameter table; do not copy the values from this file). Locust is **per entry API**, not per Kubernetes service — why, and how to get true per-service RPS/errors/latency/retries: [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md). Concrete collector design for per-service outgoing/incoming retries, goodput, offered load, and capacity: [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md). TopFull admission caps (also per Locust API): [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md).

We gather **three layers of measurement**, plus a run manifest. On the 48-run campaign (`campaign_48/`) every layer is present. The older August 38-run set only has Layer 1 Locust CSVs and RetryGuard logs.

The eval deck’s Layer 1 “retries per request” and Layer 2 CPU/memory do **not** come from TopFull’s original collectors. We added two scrapers for those.

---

## The three layers (what we actually collect)

| Layer | Deck said | What we actually write | Cadence |
|---|---|---|---|
| **1. API / system performance** | goodput, latency, rejection, retries/request | Locust CSVs from TopFull `metric_collector.py` + Envoy retry CSVs | 1 s (Locust), 1 s (Envoy mesh) |
| **2. Infrastructure** | CPU, memory, pod counts | `resource_usage.csv` via kubelet `stats/summary` (not TopFull’s in-memory `resource_collector.py`) | 5 s |
| **3. Controller state** | RetryGuard toggle timing | `retryguard.log` | 1 s samples. Shed and 0→1 use `interval_samples` (locked 20 s). Climbs 1→2 and 2→3 use `climb_interval_seconds` (locked 10 s). |

Each run folder also has `run_manifest.json` (scenario, condition, duration, collector flags).

---

## Layer 1 — Locust / TopFull API CSVs

**Writer:** TopFull’s `metric_collector.py` on master. It polls Locust every second and writes one row per second. **No timestamp column** — row index ≈ elapsed seconds since the collector started.

### Per-endpoint files (five)

| File | Locust request | Service it mainly loads |
|---|---|---|
| `getproduct.csv` | Browse product | `productcatalogservice` |
| `postcheckout.csv` | Submit checkout | `checkoutservice` (S3 / S4B bottleneck) |
| `getcart.csv` | View cart | `cartservice` read |
| `postcart.csv` | Add to cart | `cartservice` write |
| `emptycart.csv` | Empty cart | `cartservice` teardown |

These five files are **Locust APIs** (storefront actions), not one CSV per Boutique Deployment. `paymentservice` never appears as a Locust API; a Payment bottleneck only shows up here as worse `postcheckout`. For metrics that are actually per Kubernetes service (and how to add Envoy inbound RPS/errors/hop latency), see [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md).

### Columns (same on every Locust CSV)

| Column | Meaning |
|---|---|
| `RPS` | Offered requests/sec to that endpoint (also the best proxy for TopFull’s admitted load) |
| `Fail` | Requests/sec that missed the 1 s goodput SLO (`elapsed > 1 s`) **or** got a non-OK HTTP status. A slow 200 is a Fail. |
| `Goodput` | `RPS − Fail` — successful req/s. **Primary health metric.** |
| `Latency95` | 95th-percentile latency in **ms**. **The latency metric of record.** |
| `Latency99` | Always `0`. Hardcoded in TopFull. **Do not use.** P99 was dropped. |

Rejection rate is **not a stored column**. Analysis derives storefront rejection as `Fail / RPS` (0 when `RPS == 0`). That is the shopper-visible SLO-miss fraction, not the controller's input. Locked RetryGuard sheds on edge rpr from `service_edges.csv` and re-enables on inbound rejection from `service_inbound.csv` (see Layer 3 and [Derived metrics](#derived-metrics-analysis_scorepy)). S2 `Fail/RPS ≈ 1` with mesh 5xx = 0 is SLO-miss, not Boutique rejection. See [2026-09-11-slo-fail-and-mu-estimator-design.md](../docs/superpowers/specs/2026-09-11-slo-fail-and-mu-estimator-design.md).

### System-wide file: `total.csv`

Same five columns. Per second:

- `RPS` / `Fail` / `Goodput` = **sum** across the five endpoints
- `Latency95` = **mean** of the five endpoints’ P95s (not a true system-wide percentile)

Mentor charts use `total.csv` for the “whole system” goodput / P95 / rejection plots.

### Timing notes

- First rows often have `RPS=0` while Locust is still spawning — normal.
- A 10-minute run ≈ 600 rows; 15-minute (S5/S6) ≈ 900.

---

## Layer 1 — Envoy retries (retries per request)

**Writer:** `experiments/envoy_retry_collector.py` (both baseline and RetryGuard arms).

Retries are recorded on the **caller’s outbound** Envoy cluster, not the callee. We scrape:

| File | Sidecar scraped | Targets in the rows |
|---|---|---|
| `envoy_retries_frontend.csv` | `frontend` | cart, productcatalog, checkout |
| `envoy_retries_checkoutservice.csv` | `checkoutservice` | cart, productcatalog, **email** (needed for S4B) |

Changed from paymentservice on 2026-10-09; `campaign_48/` S4B runs used paymentservice and are not comparable.

### Columns (cumulative for the pod’s lifetime — Envoy never resets mid-run)

```
timestamp, target_service, upstream_rq_total, upstream_rq_retry,
upstream_rq_retry_success, upstream_rq_retry_limit_exceeded
```

| Column | Meaning |
|---|---|
| `upstream_rq_total` | Outbound requests to that target (cumulative) |
| `upstream_rq_retry` | Retry attempts (cumulative) |
| `upstream_rq_retry_success` | Retries that then succeeded |
| `upstream_rq_retry_limit_exceeded` | Gave up after max attempts |

**Retries-per-request is derived at analysis time**, not stored:

```
Δretry / Δtotal   between consecutive polls of the same target
```

Counters **accumulate across the whole campaign** on the cluster. Compare diffs **within a run**, not raw totals across folders.

Checkout sidecar `max_retry` is often 0 (few outbound retries there). Frontend `max_retry > 0` on baseline overload is the proof that stats-inclusion is working.

Prerequisite (runner does this automatically): Istio hides `upstream_rq_retry*` unless the pod has `sidecar.istio.io/statsInclusionRegexps`. `run_scenario.py` patches `frontend` / `checkoutservice` before every run.

> **Historical only.** The two per-caller files above exist in all 48 `campaign_48/` folders. Runs launched **after** the full-mesh collector landed (2026-09-08) write the new outputs below instead — they do **not** also emit `envoy_retries_*.csv`.

---

## Layer 1 — Full-mesh Envoy (per-service edges, inbound, capacity)

**Writer:** `experiments/envoy_retry_collector.py` on `topfull-master`
(`transport: network_prometheus`). Each poll is
`GET http://<pod_ip>:15020/stats/prometheus`. Files are written into the run
`record_path` on master during the run (no worker two-hop). **Writer for capacity:** `experiments/run_scenario.py::capture_service_capacity` (once per run, before `scale_constraints`).

**Present in every hold under `experiments/results/final results/`** and in other runs launched after this collector landed (2026-09-08). **Not** in `campaign_48/` or `august_38/`.

### `service_edges.csv` — outbound per (caller, target)

One row per `(timestamp, caller, target)` edge seen in that poll. Cumulative Envoy counters (same diff-at-analysis-time rule as legacy retry CSVs).

```
timestamp, caller, target, total, 2xx, 4xx, 5xx, retry, rq_time_sum_ms, rq_time_count
```

| Column | Meaning |
|---|---|
| `caller` | Service whose sidecar issued the outbound request |
| `target` | Callee service (parsed from `cluster.outbound\|...\|<target>`) |
| `total` / `2xx` / `4xx` / `5xx` | Outbound request counts by status (see live caveat below) |
| `retry` | Outbound retry attempts to that target |
| `rq_time_sum_ms` / `rq_time_count` | Cumulative sum (ms) / count from Envoy's `upstream_rq_time` latency histogram (`_sum`/`_count` series) — added 2026-09-16, **absent from any run pulled before that date**. **On this cluster these stay structurally zero:** Istio's default minimal proxy-stats excludes per-cluster `upstream_rq_time` (confirmed live 2026-09-16); enabling it needs a mesh-wide `proxyStatsMatcher` change. Parsing code is kept for forward compatibility. Estimator only reads inbound latency. |

Use for outgoing retries **and** for incoming retries at a service: sum `retry` (or `Δretry`) over all rows where `target = <service>` — Envoy has no inbound retry counter.

**Outbound class columns:** on `transport: network_prometheus`, `service_edges.csv` `2xx` / `4xx` / `5xx` are live (Prometheus `envoy_cluster_upstream_rq{response_code_class=…}`). The old admin-port gap (class columns always 0) does **not** apply to new runs. Do not claim `campaign_48/` or `august_38/` have those non-zero class columns — they predate this transport.

### `service_inbound.csv` — inbound per service

One row per `(timestamp, service)` — listener stats from that service's own sidecar.

```
timestamp, service, total, 2xx, 4xx, 5xx, resets, rq_time_sum_ms, rq_time_count, rq_time_buckets, grpc_2, grpc_4, grpc_13, grpc_14
```

| Column | Meaning |
|---|---|
| `total` | Inbound requests received (offered load at this hop) |
| `2xx` / `4xx` / `5xx` | Inbound status split |
| `resets` | `downstream_rq_rx_reset` — connection resets on this service's inbound listener. Inbound rejection is `(Δ5xx + Δresets) / Δtotal`, plus `Δgrpc_4 + Δgrpc_14` on the four read callees. |
| `rq_time_sum_ms` / `rq_time_count` | Cumulative sum (ms) / count from Envoy's inbound `downstream_rq_time` latency histogram — added 2026-09-16, **absent from any run pulled before that date**. `Δrq_time_sum_ms / Δrq_time_count` between polls = this service's own mean inbound sojourn time. Not the same as end-to-end/multi-hop Locust latency. **Live-verified 2026-09-16** on this cluster. `analysis_score.py` reports the hold's sojourn from these columns. `estimate_service_mu.py` (`mu_hat_w = lambda + 1/W`) is retired; frozen μ is in [experiments/capacity/README.md](../experiments/capacity/README.md). |
| `rq_time_buckets` | JSON object of cumulative histogram bucket counts keyed by Envoy `le` (ms, plus `+Inf`) — added 2026-09-16 (inbound only). The scorer's share of inbound requests above 500 ms is the complement of the `le=500` cumulative count, differenced between polls. Outbound edges CSV does **not** have this column (and outbound `upstream_rq_time` is excluded by Istio's default minimal proxy-stats on this cluster — structural zero). |
| `grpc_2` / `grpc_4` / `grpc_13` / `grpc_14` | Inbound `istio_requests_total` with HTTP 200 and one `grpc_response_status`: UNKNOWN (2), DEADLINE_EXCEEDED (4), INTERNAL (13), UNAVAILABLE (14). `grpc_4` and `grpc_14` are counted in inbound rejection on the four read callees. |

Derived goodput / RPS / rejection = diffs between consecutive polls of the same `service` row, same as Layer 2 CPU/memory.

### `service_capacity.json` — pre-constraint capacity snapshot

Written once at run start (before any scenario CPU-limit patch). JSON object keyed by service name:

```json
{
  "checkoutservice": {
    "cpu_limit_millicores": 2000,
    "cpu_request_millicores": 100,
    "replica_count": 1
  }
}
```

Missing or unparseable CPU values are `null`; services with no Deployment are omitted. Static for the run — captures **original** limits, not the constrained value applied during S3/S4 (checkout 200m, catalog 50m, email 50m).

### Chart pipeline caveat

`experiments/mentor_charts.py` / `mentor_charts_data.py` still read only the legacy `envoy_retries_{frontend,checkoutservice}.csv` shape. Wiring them to `service_edges.csv` / `service_inbound.csv` is a **follow-up, out of scope** for the collector implementation.

**Prerequisite (runner, post-2026-09-08):** widened stats-inclusion regex on **all 11** Deployments — `(cluster\.outbound.*upstream_rq.*)|(http\.inbound.*downstream_rq.*)` — via `run_scenario.py::ensure_envoy_stats_enabled`.

---

## Layer 2 — CPU and memory

**Writer:** `experiments/resource_usage_collector.py`. Scrapes the worker kubelet `stats/summary` API (via `kubectl get --raw`). App containers only — `istio-proxy` and pause (`POD`) are skipped.

**File:** `resource_usage.csv`

```
timestamp, service, cpu_millicores, memory_working_set_bytes, replica_count
```

Services scraped (11): frontend, cart, checkout, productcatalog, payment, recommendation, shipping, currency, email, ads, redis-cart.

| Column | Meaning |
|---|---|
| `cpu_millicores` | App-container CPU (`usageNanoCores` → millicores), summed across replicas |
| `memory_working_set_bytes` | App-container working-set memory |
| `replica_count` | Deployment `readyReplicas`. Frontend is HPA min 1 / max 4, or pinned at 4 for a hold. The other services stay at 1 unless a hold pins them. `cpu_millicores` is summed across replicas, so frontend can sit above its per-pod quota. |

Missing pods in a poll are omitted, not zero-filled.

TopFull’s own `resource_collector.py` still only feeds the RL loop in memory. It does **not** write per-run CPU/memory files. That is why we built this collector.

**Pod autoscaling / `num_instances.csv`:** never collected as its own series. `replica_count` in `resource_usage.csv` is the live ready count. Frontend runs under HPA (min 1 / max 4) or pinned at 4. S3/S4 constrain via an absolute CPU limit ([ADR 0006](../docs/adr/0006-absolute-bottleneck-cap-not-fraction.md)): checkout **200m**, catalog **50m** (S4A constrained), email **50m** (S4B). S4A unconstrained leaves the Paper-C1 table ([ADR 0009](../docs/adr/0009-paper-c1-default-cpu-table.md)). “Prevents over-scaling” is not a separate metric.

---

## Layer 3 supplement — TopFull throttle

**Writer:** `experiments/topfull_throttle_collector.py` on master. CSV rows stay on
1s wall-clock ticks shared with the mesh collector (`poll_interval_seconds`,
default 1). Live Layer A `GET /thresholds` + `GET /stats` attempts use
`layer_a_poll_interval_seconds` (default **5**, even when the scenario YAML
omits the key). `topfull_detect.csv` cadence is unchanged (still 1 s).

**Present in every `final results/` hold.** Not in `campaign_48/` or `august_38/`.

### `topfull_throttle.csv`
timestamp, api, threshold, admitted_rps, threshold_fresh, admitted_fresh

`threshold_fresh` / `admitted_fresh` are `1` when measured that tick, `0` when
the value is carried from an earlier successful scrape. After the split
cadence, `0` covers both "not attempted this tick by design" and "attempted
and timed out" — there is no third state. Filter `admitted_fresh==1` for a
true per-second admitted rate. Row cadence is still 1 s and still joinable
on `timestamp`; the live fraction of rows is lower by design under the
default. Genuine timeouts vs skips are in `topfull_throttle_collector.log`
(`WARNING  …fetch failed` only on failures).

When this cap is placed on the same 1 s clock as the other run metrics, a live
`threshold` of **10000** is no cap and is left off the series. It is the
proxy's passthrough sentinel, not a TopFull decision, and plotting it scales
the axis to 10000. A live **0** is an empty read and is left off the same way.
The file still stores both numbers. Between live reads, keep the last usable
cap for at most 6 s, which covers the default 5 s scrape. Do not carry it
across a longer hole, and do not keep a repeated value after live reads stop.

### `topfull_detect.csv`
timestamp, service, cadvisor_cpu, quota, alpha, utilization, overloaded

One row per `(timestamp, service)` for all 11 Boutique services. `cadvisor_cpu`
is a **direct** HTTP scrape of the cAdvisor DaemonSet (`cadvisor` namespace,
`GET :8080/api/v2.0/summary/<container_id>?type=docker`, container IDs from
`kubectl get po -o json`) — a different source than `resource_usage.csv`
(Layer 2, kubelet `stats/summary`); it exists specifically to approximate
what TopFull's own `Detector` sees. `quota` is `topfull_cpu_quotas.
paper_limit_for(service)`, overridden per-run by that run's
`effective_cpu_quotas` (Paper-C1 table plus any absolute
`cpu_limit_millicores` constraint — [ADR 0006](../docs/adr/0006-absolute-bottleneck-cap-not-fraction.md),
[ADR 0009](../docs/adr/0009-paper-c1-default-cpu-table.md))
— the same map written to `topfull_run_quotas.json` for the live Detector
overlay, so this column tracks what the detector was reconciled to that run,
not a stale hardcoded map. `alpha` approximates only the detector's
**main-loop** `detect(0.8)` check (`0.95` for `productcatalogservice`/
`cartservice`); real calls from `apply()`/`apply_v2()` also use `0.9` and are
not reconstructed. `overloaded` reconstructs `Detector.detect()` (cAdvisor
CPU vs quota × alpha). It is not kubelet `resource_usage.csv`. Layers C/D
are not collected. `mentor_charts.py` does not read these files.

After every run that writes this file, report Layer B **max utilization per
service**, **overloaded count**, **quota**, **α**, and the hottest services.
`cadvisor_cpu>0` / `overloaded=0` alone is not enough — those two can hold
while a service sits just under α (S1 run20 / S2 run17: frontend max util
0.727 / 0.737, overloaded=0). Checkpoint table:
[2026-09-13-s1-s2-baseline-metric-checkpoint.md](../docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md) §6.

---

## Layer 3 — RetryGuard decisions

**File:** `retryguard.log` (RetryGuard runs only). Canonical parameters: [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md) and [ADR 0008](../docs/adr/0008-locked-retryguard-parameters.md). Do not treat the numbers below as a second source of truth.

Locked runs use `retry_metric: edge_rpr`. The controller reads `service_edges.csv` every 1 s for **14** caller→callee edges (`CONTROLLED_EDGES`) and `service_inbound.csv` for re-enable. It does not patch `frontend` or `redis-cart`. The nine `CONTROLLED_SERVICES` are the HTTP backends those edges land on.

`rpr = Δretry / (Δtotal − Δretry)` on one edge (retries per first attempt). A tick with no first attempts is skipped.

| Step | Signal | Quiet time |
|---|---|---|
| any → 0 (shed) | edge rpr above `retries_threshold` (locked 0.4) | `interval_samples` (locked 20 s of row timestamps). Scenario 5 sweeps 10/20/30/60. |
| 0 → 1 | inbound rejection strictly under `reenable_rejection` (locked 0.25) | `interval_samples` |
| 1 → 2 | rpr ≤ `climb_rpr_1_to_2` (locked 0.16) | `climb_interval_seconds` (locked 10 s; code default `CLIMB_INTERVAL_SECONDS` is also 10). Holds that omitted the key before 2026-10-13 ran at 15 s. |
| 2 → 3 | rpr ≤ `climb_rpr_2_to_3` (locked 0.32) | `climb_interval_seconds` |

Inbound rejection is `(Δ5xx + Δresets) / Δtotal`, plus `Δgrpc_4 + Δgrpc_14` on the four read callees (`adservice`, `currencyservice`, `productcatalogservice`, `recommendationservice`). The scorer uses the same formula. HTTP-only (`5xx + resets`) is a companion table for those four. Storefront `Fail/RPS` is a third number and is not this signal.

Disable writes `retries: {attempts: 0}` plus a route `timeout` equal to `perTryTimeout` on that caller→callee route. Omitting the `retries` block falls back to Istio's default of 2 retries. Restore is a ramp (0→1→2→3), not a jump back to 3.

Burst mode (the three keys `burst_rpr` 2.0, `burst_window_seconds` 5, `burst_min_first_attempts` 20) is a second shed test beside the normal one. Normal mode omits those three keys. The burst bar at the current cap is `burst_rpr × attempts / attempts_on` (2.00 / 1.33 / 0.67 at 3 / 2 / 1 attempts). A burst shed goes to 0 (`metric=rpr_burst`) and recovers on the normal path. Bar 1.5 is dropped.

Holds before 2026-10-12, `campaign_48/`, and `august_38/` used older values (rejection mode or earlier edge-mode bars, `interval_samples` 30) and are not comparable.

| Log keyword | Meaning |
|---|---|
| `START` | Params. Includes `metric=edge_rpr`, `edges=14`, `attempts_on=3`, `rpr_threshold=` (the YAML key is `retries_threshold`), and the three burst keys when burst is on. |
| `OBSERVE` | One sample. Edge lines are `caller->callee` with `rpr=`, `attempts=`, `elapsed_s=`, `metric=rpr`, and `burst_rpr5=` when burst is on. Callee lines while an edge is at 0 are `metric=rejection`. |
| `ON→OFF` | Shed to 0 attempts. `metric=rpr` or `metric=rpr_burst`. Carries `from_attempts=` and `elapsed_s=`. |
| `OFF→ON` | 0→1. `metric=rejection`, `attempts=1`. |
| `0→1` / `1→2` / `2→3` | The ramp steps. `1→2` and `2→3` are `metric=rpr`. |
| `SKIP` / `PATCH_FAIL` / `EXIT` | No newer row / K8s patch failed / stop. |

Edge names inside lines use ASCII `->`. Transition arrows are unicode (`ON→OFF`, not `ON->OFF`). These timestamps are the overlay on the mentor Locust charts.

---

## Derived metrics (`analysis_score.py`)

`python experiments/analysis_score.py <run_dir>` prints the tables [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md) pastes. None of these are stored columns. The scorer uses every inbound row and every Locust row with `RPS > 0`. It does not drop the first 30 Locust rows or the last 5 polls (`s2_probe_tables.py` and the canon scorer trim `[30:-5]`).

When `retryguard.log` has no `START` line, the scorer falls back to shed bar 0.5 and re-enable bar 0.10. A `START` line wins, including older logs. `rpr_threshold` on `START` is YAML `retries_threshold`.

| Derived metric | Formula / source | Template item |
|---|---|---|
| Edge rpr | `Δretry / (Δtotal − Δretry)` on one `service_edges.csv` edge. A tick with no first attempts is skipped. | 3, 4 |
| Volume rpr | Hold's `Δretry / first attempts` on that edge. | 4 |
| File streak | Seconds from the first consecutive scored tick above the shed bar to the last. One tick is 0 seconds. Controller `high` on the same edge is a sample count, not seconds. Older guides that counted rows say so. | 4 |
| Storefront rejection | Locust `Fail / RPS` while `RPS > 0`. | 10 |
| Inbound rejection | `(Δ5xx + Δresets) / Δtotal`, plus `Δgrpc_4 + Δgrpc_14` on the four read callees. Same formula as `retryguard.measure_inbound_rejection`. Streaks above 0.20 and under `reenable_rejection`. | 5, 8 |
| HTTP-only rejection | `(Δ5xx + Δresets) / Δtotal` on those four callees only. Printed so guides before 2026-10-13 (HTTP-only in the main table) can be compared. Rescored copies end in `-rescored.md`. | 5 |
| `grpc_4` / `grpc_14` | Positive deltas summed per service. `grpc_4` is DEADLINE_EXCEEDED, `grpc_14` is UNAVAILABLE. The retry policy retries those codes on the four read callees. | 7 |
| Detector overloaded share | `overloaded=1` ticks over `topfull_detect.csv` rows. Bold at a share of at least 0.5. | 6 |
| Detector max utilization | Max `utilization` (`cadvisor_cpu / quota`) per service. | 16 |
| Inbound arrival rate | Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s. | 12 |
| Inbound sojourn | `Δrq_time_sum_ms / Δrq_time_count`, milliseconds. | 13 |
| Share above 500 ms | From the `le=500` bucket of `rq_time_buckets`. | 14 |
| Locust goodput / fail rate / P95 | Mean of `Goodput`, `Fail/RPS`, and `Latency95` while `RPS > 0`, per API. | 9–11 |
| Live throttle caps | `topfull_throttle.csv` rows with `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is an empty read. Last usable cap is held for at most 6 s. | 17 |
| Per-callee toggle stats | From the log: `ON→OFF` / `OFF→ON` counts, shed rpr, seconds to first shed, attempts after re-enable, time OFF, OFF-window rejection min/median, longest streak under `reenable_rejection`. A burst shed is tagged `b` and its value is the 5 s aggregate `ΣΔretry / ΣΔfirst`. | 8 |

---

## Also present, but not used as metrics

| File | What it is | Status |
|---|---|---|
| `run_manifest.json` | Scenario, condition, run number, duration, collector flags, `paper_cpu_quotas` / `effective_cpu_quotas` | Always |
| `service_capacity.json` | Per-service `cpu_limit_millicores` / `cpu_request_millicores` / `replica_count`, snapshotted **before** `scale_constraints` are applied | Always, 2026-09-08+ runs. Context for interpreting `resource_usage.csv` / `topfull_detect.csv`, not a time series itself. |
| `topfull_run_quotas.json` | Live-only on master (never copied into the run folder; deleted at teardown) — the *effective* per-run quota map read by a patched `Detector.__init__` overlay so K8s and TopFull's in-memory quotas match for that run | Not a collected artifact — see `run_manifest.json`'s `effective_cpu_quotas` for the persisted equivalent |
| `num_agent.csv` | TopFull RL admission / agent counts | **Empty** (almost all zeros). Use Locust `RPS` as admitted-load proxy. |
| `topfull_proxy.log` | Go proxy stdout and stderr. Each line starts with a UTC second stamp. `-------------------------` and one `<api>: <rps>` line per API come once a second from the proxy's own monitor. `Apply threshold to <api> : <cap>` appears when the RL loop sets a cap (Go prints the cap as `+1.230000e+002`) | Holds from 2026-10-15 on. Diagnostics only: read with `python experiments/topfull_health.py <run_dir>` |
| `topfull_rl.log` | `deploy_rl.py` stdout and stderr, same stamp. Ray startup, then the detector's CPU dict and overloaded list about every 2 s, and agent lines (`[...] running`, `All APIs clean`, `ttl done`) | TopFull-on holds from 2026-10-15 on. Diagnostics only. `num_agent.csv` has no timestamps; this log is the RL loop's clock |
| `envoy_retry_collector.log` / `resource_usage_collector.log` / `topfull_throttle_collector.log` | Collector start/stop/warnings | Diagnostics only |

Locust on `topfull-load` is not copied as its own stats files. All API numbers come through `metric_collector.py`.

---

## How analysis uses this (Phase 7 targets)

The comparison the project is built for:

**goodput · P95 latency · rejection rate · retries-per-request · CPU/memory · RetryGuard toggle events**

| Metric | Source | How |
|---|---|---|
| Goodput | Locust `Goodput` | Mean across 3 repeats, 5 s downsample |
| P95 | Locust `Latency95` | Same |
| Rejection | derived `Fail/RPS` | Same |
| Retries/request | Envoy edge rpr `Δretry / (Δtotal − Δretry)`, plus volume rpr | Per edge. Not `Δretry / Δtotal`. |
| CPU / memory | `resource_usage.csv` | Per service (the Layer 1 Locust columns are not). Mean and max millicores are summed across replicas. |
| Toggles | `retryguard.log` | `ON→OFF` / `OFF→ON` / `1→2` / `2→3`, including `metric=rpr_burst` |

Per-service RPS / errors / hop latency are scored from `service_inbound.csv` and `service_edges.csv` (see [Derived metrics](#derived-metrics-analysis_scorepy)). Feasibility: [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md).

---

## Clock alignment (important)

- Read every run on the **hold clock**: seconds since the first Locust row, in master's UTC. `experiments/hold_clock.py` adds a `hold_s` column to any source; `experiments/run_timeline.py` writes `timeline.png` (and `timeline_1s.csv` with `--csv`). Design and per-second rules: [2026-10-13-hold-clock-design.md](../docs/superpowers/specs/2026-10-13-hold-clock-design.md).
- Locust CSVs: rows are about 1.05–1.10 s apart, not 1 s, and the first row is the first poll with traffic. Folders without a Locust `timestamp` column use that run's Locust clock fit in `locust_clock.json` (start, spacing, anchors, correlation, flag). Holds after the 2026-10-13 patch have a `timestamp` column (last column, UTC milliseconds) and `locust_started_at` in `run_manifest.json`.
- Envoy mesh + throttle collectors stamp `floor(unix_time / interval) * interval` UTC seconds (aligned). `resource_usage.csv` uses interval=5 on the same grid. Throttle **rows** stay 1 s; Layer A live `/thresholds`+`/stats` attempts use `layer_a_poll_interval_seconds` (default 5) on that same aligned grid. Skipped ticks still write a `topfull_throttle.csv` row with `*_fresh=0`.
- Each collector starts on its own. On `final results/` holds the first mesh inbound poll is roughly 25–60 s before the first Locust row, and the throttle and CPU collectors start earlier still (up to about two minutes). A file's own first poll is not t = 0. Escape time is the exception: it keeps its first-mesh-poll definition.

---

## Campaign vs August vs final results

| | `final results/` (new holds) | `campaign_48/` (closed Phase 7) | `august_38/` (historical) |
|---|---|---|---|
| Locust CSVs + `total.csv` | Yes | Yes | Yes |
| `retryguard.log` | RG runs, edge mode, burst when the YAML sets it | RG runs, older controller | RG runs, older controller |
| Envoy retry CSVs (`envoy_retries_*.csv`) | **None** (legacy shape) | **All 48 folders** | **None** |
| Full-mesh Envoy (`service_edges.csv`, `service_inbound.csv`, `service_capacity.json`) | **Yes** | **None** (pre-dates collector) | **None** |
| TopFull throttle (`topfull_throttle.csv`, `topfull_detect.csv`) | **Yes** | **None** (pre-dates collector) | **None** |
| `resource_usage.csv` | **Yes** | **All 48 folders** | **None** |
| Re-enable (`OFF→ON`) | When the load recovers | S5 + S6 (and a few others) | **Never** |
