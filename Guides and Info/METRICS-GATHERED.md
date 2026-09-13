# Metrics we gather

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Comprehensive inventory of every metric collected during experiment runs: sources, columns, derived values, clocks, and what is empty or unused. **For the "why do we collect this" narrative (rationale per metric, mapped to the eval deck's open questions), see [METRICS-CATALOG.md](METRICS-CATALOG.md) instead — that doc is the companion "how + why" read; this one stays the columns/files inventory.** Operational details (how to pull, verify, load) live in [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md). Gaps and what is answerable: [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md). RetryGuard’s use of these CSVs: [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md). Locust is **per entry API**, not per Kubernetes service — why, and how to get true per-service RPS/errors/latency/retries: [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md). Concrete collector design for per-service outgoing/incoming retries, goodput, offered load, and capacity: [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md). TopFull admission caps (also per Locust API): [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md).

We gather **three layers of measurement**, plus a run manifest. On the 48-run campaign (`campaign_48/`) every layer is present. The older August 38-run set only has Layer 1 Locust CSVs and RetryGuard logs.

The eval deck’s Layer 1 “retries per request” and Layer 2 CPU/memory do **not** come from TopFull’s original collectors. We added two scrapers for those.

---

## The three layers (what we actually collect)

| Layer | Deck said | What we actually write | Cadence |
|---|---|---|---|
| **1. API / system performance** | goodput, latency, rejection, retries/request | Locust CSVs from TopFull `metric_collector.py` + Envoy retry CSVs | 1 s (Locust), 1 s (Envoy mesh) |
| **2. Infrastructure** | CPU, memory, pod counts | `resource_usage.csv` via kubelet `stats/summary` (not TopFull’s in-memory `resource_collector.py`) | 5 s |
| **3. Controller state** | RetryGuard toggle timing | `retryguard.log` | every 30 s window |

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

Rejection rate is **not a stored column**. Analysis derives storefront rejection as `Fail / RPS` (0 when `RPS == 0`). RetryGuard does **not** use this; it uses inbound `Δ5xx / Δtotal` from `service_inbound.csv` (see Layer 3). S2 `Fail/RPS ≈ 1` with mesh 5xx = 0 is SLO-miss, not Boutique rejection. See [2026-09-11-slo-fail-and-mu-estimator-design.md](../docs/superpowers/specs/2026-09-11-slo-fail-and-mu-estimator-design.md).

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
| `envoy_retries_checkoutservice.csv` | `checkoutservice` | cart, productcatalog, **payment** (needed for S4B) |

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

**Present only in runs launched after this collector landed** — not in `campaign_48/` or `august_38/`. The next new experiment run will be the first folder with these files.

### `service_edges.csv` — outbound per (caller, target)

One row per `(timestamp, caller, target)` edge seen in that poll. Cumulative Envoy counters (same diff-at-analysis-time rule as legacy retry CSVs).

```
timestamp, caller, target, total, 2xx, 4xx, 5xx, retry
```

| Column | Meaning |
|---|---|
| `caller` | Service whose sidecar issued the outbound request |
| `target` | Callee service (parsed from `cluster.outbound\|...\|<target>`) |
| `total` / `2xx` / `4xx` / `5xx` | Outbound request counts by status (see live caveat below) |
| `retry` | Outbound retry attempts to that target |

Use for outgoing retries **and** for incoming retries at a service: sum `retry` (or `Δretry`) over all rows where `target = <service>` — Envoy has no inbound retry counter.

**Outbound class columns:** on `transport: network_prometheus`, `service_edges.csv` `2xx` / `4xx` / `5xx` are live (Prometheus `envoy_cluster_upstream_rq{response_code_class=…}`). The old admin-port gap (class columns always 0) does **not** apply to new runs. Do not claim `campaign_48/` or `august_38/` have those non-zero class columns — they predate this transport.

### `service_inbound.csv` — inbound per service

One row per `(timestamp, service)` — listener stats from that service's own sidecar.

```
timestamp, service, total, 2xx, 4xx, 5xx
```

| Column | Meaning |
|---|---|
| `total` | Inbound requests received (offered load at this hop) |
| `2xx` / `4xx` / `5xx` | Inbound status split |

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

Missing or unparseable CPU values are `null`; services with no Deployment are omitted. Static for the run — captures **original** limits, not the patched `100m` bottleneck value applied during S3/S4.

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
| `replica_count` | Deployment `readyReplicas` — **always 1** (fixed-replica design) |

Missing pods in a poll are omitted, not zero-filled.

TopFull’s own `resource_collector.py` still only feeds the RL loop in memory. It does **not** write per-run CPU/memory files. That is why we built this collector.

**Pod autoscaling / `num_instances.csv`:** never collected. Replicas are fixed at 1; S3/S4 constrain via CPU limit (`100m`), not replica count. “Prevents over-scaling” is not measurable in this setup.

---

## Layer 3 supplement — TopFull throttle (future runs)

**Writer:** `experiments/topfull_throttle_collector.py` on master. CSV rows stay on
1s wall-clock ticks shared with the mesh collector (`poll_interval_seconds`,
default 1). Live Layer A `GET /thresholds` + `GET /stats` attempts use
`layer_a_poll_interval_seconds` (default **5**, even when the scenario YAML
omits the key). `topfull_detect.csv` cadence is unchanged (still 1 s).

**Present only in runs launched after this collector landed** — not in
`campaign_48/` or `august_38/`.

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

### `topfull_detect.csv`
timestamp, service, cadvisor_cpu, quota, alpha, utilization, overloaded

One row per `(timestamp, service)` for all 11 Boutique services. `cadvisor_cpu`
is a **direct** HTTP scrape of the cAdvisor DaemonSet (`cadvisor` namespace,
`GET :8080/api/v2.0/summary/<container_id>?type=docker`, container IDs from
`kubectl get po -o json`) — a different source than `resource_usage.csv`
(Layer 2, kubelet `stats/summary`); it exists specifically to approximate
what TopFull's own `Detector` sees. `quota` is `topfull_cpu_quotas.
paper_limit_for(service)`, overridden per-run by that run's
`effective_cpu_quotas` (paper table + any active S3/S4 `cpu_limit_fraction`)
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

**File:** `retryguard.log` (RetryGuard runs only).

RetryGuard reads `{record_path}/service_inbound.csv` every 1 s. For each of the 9 `CONTROLLED_SERVICES` it computes inbound `Δ5xx / Δtotal` against the last consumed poll (SKIP if no newer timestamp). That rate is Algorithm 1 `measure_value()`. Locust CSVs are not opened.

It controls nine HTTP backends (including `paymentservice`). It does not patch `frontend` or `redis-cart`.

Default: disable after 30 consecutive 1 s samples ≥ 20% inbound 5xx; re-enable after 30 consecutive samples below 20% (Scenario 5 sweeps `interval_samples` 10/20/30/60).

| Log keyword | Meaning |
|---|---|
| `START` | Params + service list |
| `OBSERVE` | Window result: rejection, consecutive low/high, ON/OFF |
| `ON→OFF` | Disabled Istio retries on that service (`attempts` omitted) |
| `OFF→ON` | Restored `attempts: 3` |
| `SKIP` / `PATCH_FAIL` / `SHUTDOWN` | Missing CSV / K8s patch failed / stop |

These timestamps are the overlay on the mentor Locust charts.

---

## Also present, but not used as metrics

| File | What it is | Status |
|---|---|---|
| `run_manifest.json` | Scenario, condition, run number, duration, collector flags, `paper_cpu_quotas` / `effective_cpu_quotas` | Always |
| `service_capacity.json` | Per-service `cpu_limit_millicores` / `cpu_request_millicores` / `replica_count`, snapshotted **before** `scale_constraints` are applied | Always, 2026-09-08+ runs. Context for interpreting `resource_usage.csv` / `topfull_detect.csv`, not a time series itself. |
| `topfull_run_quotas.json` | Live-only on master (never copied into the run folder; deleted at teardown) — the *effective* per-run quota map read by a patched `Detector.__init__` overlay so K8s and TopFull's in-memory quotas match for that run | Not a collected artifact — see `run_manifest.json`'s `effective_cpu_quotas` for the persisted equivalent |
| `num_agent.csv` | TopFull RL admission / agent counts | **Empty** (almost all zeros). Use Locust `RPS` as admitted-load proxy. |
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
| Retries/request | Envoy Δretry/Δtotal | Per target + summed |
| CPU / memory | `resource_usage.csv` | Per service (the Layer 1 Locust columns are not) |
| Toggles | `retryguard.log` | `ON→OFF` / `OFF→ON` overlays |

Per-service RPS / errors / hop latency are **not** in this table today. Feasibility and how to scrape them from Envoy: [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md).

---

## Clock alignment (important)

- Locust CSVs: no clock; row *i* ≈ second *i* of the run. Toggle overlays line up with these charts. Locust CSVs remain index-based with no timestamp column.
- Envoy mesh + throttle collectors now stamp `floor(unix_time / interval) * interval` UTC seconds (aligned). `resource_usage.csv` uses interval=5 on the same grid. Throttle **rows** stay 1 s; Layer A live `/thresholds`+`/stats` attempts use `layer_a_poll_interval_seconds` (default 5) on that same aligned grid. Skipped ticks still write a `topfull_throttle.csv` row with `*_fresh=0`.
- Envoy + CPU/memory: UTC timestamps. Charts set *t* = 0 at **that file’s first poll**, which can be a few seconds before/after Locust. Do not treat “CPU dip at 60 s” as the same instant as “toggle at 60 s” on a Locust chart.

---

## Campaign vs August

| | `campaign_48/` (primary) | `august_38/` (historical) |
|---|---|---|
| Locust CSVs + `total.csv` | Yes | Yes |
| `retryguard.log` | RG runs | RG runs |
| Envoy retry CSVs (`envoy_retries_*.csv`) | **All 48 folders** | **None** |
| Full-mesh Envoy (`service_edges.csv`, `service_inbound.csv`, `service_capacity.json`) | **None** (pre-dates collector) | **None** |
| TopFull throttle (`topfull_throttle.csv`, `topfull_detect.csv`) | **None** (pre-dates collector) | **None** |
| `resource_usage.csv` | **All 48 folders** | **None** |
| Re-enable (`OFF→ON`) | S5 + S6 (and a few others) | **Never** |
