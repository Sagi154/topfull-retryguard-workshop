# Metrics Collection Guide

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Scope:** This guide explains what data is collected during each experiment run, where it lives, how to pull it to your PC, and how to verify it's usable before moving on to the next run. Read this alongside [SCENARIOS-GUIDE.md](SCENARIOS-GUIDE.md) and [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md). For the full inventory of every metric and a rationale ("why we collect this") per metric, see [METRICS-GATHERED.md](METRICS-GATHERED.md) and [METRICS-CATALOG.md](METRICS-CATALOG.md).

---

## 1. What gets collected and by what tool

Every run produces output from up to six sources. API performance and the run manifest are always present; RetryGuard decisions only when RetryGuard is on; the Envoy mesh collector, CPU/memory collector, and TopFull throttle collector when their collectors are enabled (default `enabled: true` in all 16 scenario configs).

| Source | Written by | Format | Always collected? |
|--------|-----------|--------|------------------|
| **API performance** | `metric_collector.py` (TopFull, on master) | One CSV per Locust endpoint, one row per second | Yes |
| **Run manifest + capacity snapshot** | `run_scenario.py` at collection/start time | `run_manifest.json`, `service_capacity.json` | Yes |
| **RetryGuard decisions** | `retryguard.py` | `retryguard.log` text file | RetryGuard runs only |
| **Full-mesh Envoy (per-service edges + inbound)** | `envoy_retry_collector.py` (process on `topfull-master`; `GET http://<pod_ip>:15020/stats/prometheus`; files land in the master results folder during the run) | `service_edges.csv`, `service_inbound.csv` + `envoy_retry_collector.log` | When collector enabled (default), **runs after 2026-09-08** |
| **CPU/memory per service** | `resource_usage_collector.py` | `resource_usage.csv` + `resource_usage_collector.log` | When collector enabled (default) |
| **TopFull throttle + detector reconstruction** | `topfull_throttle_collector.py` | `topfull_throttle.csv`, `topfull_detect.csv` + `topfull_throttle_collector.log` | When collector enabled (default), **runs after 2026-09-09** |

> **Legacy note (superseded, not additive):** Before 2026-09-08, `envoy_retry_collector.py` only scraped two caller sidecars (`frontend`, `checkoutservice`) and wrote `envoy_retries_frontend.csv` / `envoy_retries_checkoutservice.csv`. That code path no longer exists — the collector now *always* scrapes all 11 Boutique sidecars and writes `service_edges.csv` / `service_inbound.csv` instead. A run either has the legacy files (all of `campaign_48/` and `august_38/`, collected before the rewrite) **or** the full-mesh files (any run launched after 2026-09-08) — never both. See §5.
>
> **Layer 2 note:** `resource_usage_collector.py` (kubelet `stats/summary` via `kubectl get --raw`) closes the *instrumentation* half of the CPU/memory gap. TopFull's in-memory `resource_collector.py` still feeds the RL loop only — it is not patched. The existing 38 matrix folders predate this collector; new runs will produce `resource_usage.csv`. Pod replica counts in the CSV will be `1` for every service (fixed-replica experimental design). See [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md).
>
> **Gap 3 note:** The Envoy retry collector closes the *instrumentation* half of the "retries per request" gap. The existing 38 matrix folders were collected *before* this collector existed, so they still have no retry-count series. New runs (including the Gap 1 recovery-phase re-runs) will produce the CSVs. See [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 3.
>
> **No campaign data yet for the newest collectors.** `service_edges.csv` / `service_inbound.csv` / `service_capacity.json` (full mesh, 2026-09-08) and `topfull_throttle.csv` / `topfull_detect.csv` (TopFull throttle, 2026-09-09) are implemented and unit-tested but **no run in `campaign_48/` or `august_38/` has them** — both predate the collectors. The next new experiment run is the first that will.

---

## 2. Folder structure per run

The runner (`run_scenario.py`) creates one folder per run on the master VM under `results_base_path`:

```
/home/idozacharia/experiments/results/
  <log_folder>/
    getproduct.csv
    postcheckout.csv
    getcart.csv
    postcart.csv
    emptycart.csv
    total.csv                            ← always (system-wide sum of the five)

    # Envoy mesh — runs BEFORE 2026-09-08 have the two legacy files;
    # runs AFTER have the three full-mesh files. Never both.
    envoy_retries_frontend.csv           ← LEGACY, when envoy_retry_collector enabled
    envoy_retries_checkoutservice.csv    ← LEGACY, when envoy_retry_collector enabled
    service_edges.csv                    ← FULL MESH, when envoy_retry_collector enabled
    service_inbound.csv                  ← FULL MESH, when envoy_retry_collector enabled
    envoy_retry_collector.log            ← when envoy_retry_collector enabled

    resource_usage.csv                   ← when resource_usage_collector enabled
    resource_usage_collector.log         ← when resource_usage_collector enabled

    topfull_throttle.csv                 ← when topfull_throttle_collector enabled (2026-09-09+)
    topfull_detect.csv                   ← when topfull_throttle_collector enabled (2026-09-09+)
    topfull_throttle_collector.log       ← when topfull_throttle_collector enabled (2026-09-09+)

    retryguard.log                       ← RetryGuard runs only
    num_agent.csv                        ← always written by TopFull, always empty — not a metric
    run_manifest.json                    ← always
    service_capacity.json                ← always (2026-09-08+), pre-constraint CPU/replica snapshot
```

`log_folder` comes directly from the YAML config (e.g. `baseline_topfull_no_retryguard_sustained_overload_run1`). Each run has a unique folder name because the run number is embedded in it — runs never overwrite each other. With `transport: network_prometheus` (current YAML default), `service_edges.csv` / `service_inbound.csv` / `envoy_retry_collector.log` are written into this master folder during the run. RetryGuard's `measure_value()` can read `service_inbound.csv` mid-run because the file is on master. Do not treat `campaign_48/` or `august_38/` as having these mesh files.

### All results for a scenario (multiple runs + both conditions) look like:

```
/home/idozacharia/experiments/results/
  baseline_topfull_no_retryguard_sustained_overload_run1/
  baseline_topfull_no_retryguard_sustained_overload_run2/
  baseline_topfull_no_retryguard_sustained_overload_run3/
  run_topfull_retryguard_sustained_overload_run1/
  run_topfull_retryguard_sustained_overload_run2/
  run_topfull_retryguard_sustained_overload_run3/
```

---

## 3. The API performance CSVs

### Files

One file per Locust endpoint — five files per run:

| File | Locust endpoint | What it measures |
|------|----------------|-----------------|
| `getproduct.csv` | Browse product page | `productcatalogservice` load path |
| `postcheckout.csv` | Submit checkout | `checkoutservice` load path (critical for S3) |
| `getcart.csv` | View cart | `cartservice` read path |
| `postcart.csv` | Add to cart | `cartservice` write path |
| `emptycart.csv` | Empty cart | `cartservice` session teardown |

### Columns

```
RPS, Fail, Goodput, Latency95, Latency99
```

| Column | Meaning |
|--------|---------|
| `RPS` | Requests per second sent to this endpoint (offered load) |
| `Fail` | Requests/sec that missed the 1 s goodput SLO (`elapsed > 1 s`) **or** got a non-OK HTTP status. A slow 200 is a Fail. |
| `Goodput` | `RPS - Fail` — successful requests per second (the primary health metric) |
| `Latency95` | 95th-percentile response latency in milliseconds — **the latency metric of record** (see [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 2) |
| `Latency99` | Always `0` — hardcoded in TopFull's `metric_collector.py`, never actually computed. **Do not use.** P99 was dropped as a target metric on 2026-08-20: neither RetryGuard's paper (average-latency-based), TopFull's paper (goodput-based), nor the eval deck (generic "API latency") requires it. Column left as-is because it's written by TopFull's unmodified collector. |

### Timing

- **One row = one second.** A 10-minute run produces ~600 rows per file.
- Rows are written from when `metric_collector.py` starts. The first few rows may show `RPS=0` while Locust is still spawning — this is normal.
- There is no absolute timestamp column. The row index is seconds elapsed since the collector started (approximately aligned with run start).

### What healthy data looks like (Scenario 1 — Normal Op)

```
RPS,Fail,Goodput,Latency95,Latency99
13.2,0,13.2,42,0
13.5,0,13.5,40,0
...
```

`Fail=0` throughout, `Goodput≈RPS`. During the smoke run, S1 baseline had 273 rows with `Fail=0` and total goodput ≈390.

### What overloaded data looks like (Scenario 2/3 baseline)

```
RPS,Fail,Goodput,Latency95,Latency99
20.1,19.6,0.5,4200,0
20.3,20.3,0.0,9999,0
...
```

`Fail` approaches `RPS`, `Goodput` near zero, latency spikes.

---

## 4. The RetryGuard log

**File:** `retryguard.log` (present only in RetryGuard-condition runs)

**Also visible live** during a run:
```bash
ssh topfull-master "tmux attach -t retryguard"   # Ctrl+B, D to detach
```

### Log line types

| Keyword | Meaning |
|---------|---------|
| `START` | Controller initialized — shows all params |
| `OBSERVE` | End of each 1 s sample — reports rejection rate + counters for every service |
| `ON→OFF` | RetryGuard disabled retries on a service (VirtualService patched) |
| `OFF→ON` | RetryGuard re-enabled retries on a service |
| `SKIP` | No new inbound row this tick |
| `PATCH_FAIL` | Kubernetes API patch failed (logged, state not updated) |
| `SHUTDOWN` / `EXIT` | Controller received stop signal |

### Example log

```
2026-08-04T13:20:00Z  START  threshold=0.20 sample_interval=1s interval_samples=30 (30s) services=['adservice', 'cartservice', 'checkoutservice', 'currencyservice', 'emailservice', 'paymentservice', 'productcatalogservice', 'recommendationservice', 'shippingservice']
2026-08-04T13:20:01Z  OBSERVE  cartservice         rejection=0.0100  low=1 high=0  state=ON
2026-08-04T13:20:30Z  OBSERVE  checkoutservice     rejection=0.3800  low=0 high=1  state=ON
2026-08-04T13:20:30Z  OBSERVE  productcatalogservice  rejection=0.0200  low=1 high=0  state=ON
2026-08-04T13:21:00Z  OBSERVE  checkoutservice     rejection=0.4100  low=0 high=2  state=ON
2026-08-04T13:21:00Z  checkoutservice  ON→OFF   rejection=0.41  consecutive_high=2  attempts=0
2026-08-04T13:24:00Z  OBSERVE  checkoutservice     rejection=0.0500  low=3 high=0  state=OFF
2026-08-04T13:24:00Z  checkoutservice  OFF→ON   rejection=0.05  consecutive_low=3  attempts=3
```

### Reading an ON→OFF event

`checkoutservice  ON→OFF   rejection=0.41  consecutive_high=2  attempts=0`

- `checkoutservice` rejection rate stayed above 20% for `interval_samples` consecutive 1 s inbound samples (default 30)
- RetryGuard patched the VirtualService to remove the `retries` block
- From this timestamp, Istio no longer retries failed `checkoutservice` calls

Cross-reference this timestamp with `postcheckout.csv` — you should see `Fail` drop and/or `Goodput` recover shortly after.

---

## 5. The Envoy mesh CSVs (retries per request, per-service goodput, offered load)

**Files** (when `envoy_retry_collector.enabled: true`, default `poll_interval_seconds: 1` in current scenario YAMLs):

`experiments/envoy_retry_collector.py` `kubectl exec`s into **every** Boutique pod's `istio-proxy` sidecar (`ALL_BOUTIQUE_SERVICES`, 11 services including `redis-cart`) each poll, runs `curl localhost:15000/stats`, and parses two families of counters out of the same dump:

| File | Grain | Columns | What it answers |
|------|-------|---------|-----------------|
| `service_edges.csv` | one row per `(timestamp, caller, target)` outbound edge actually seen that poll | `timestamp, caller, target, total, 2xx, 4xx, 5xx, retry` | Who calls whom, how many outbound retries per edge (`retry`) |
| `service_inbound.csv` | one row per `(timestamp, service)` | `timestamp, service, total, 2xx, 4xx, 5xx` | Offered load and status split *at that service's own sidecar* |
| `envoy_retry_collector.log` | — | `START` / `WARNING` / `SHUTDOWN` / `EXIT` lines | Diagnostics |

**Why scrape both directions.** Envoy only ever records "I retried this call" on the **caller's** outbound cluster stats (`cluster.outbound|…|<target>.…upstream_rq_retry`) — the callee's sidecar has no idea a retry happened, it just sees N separate inbound requests. So:
- **Outgoing retries** for a service = `service_edges.csv` rows where `caller = <service>`.
- **Incoming retries** at a service (not a real Envoy counter) = `Σ retry` over all `service_edges.csv` rows where `target = <service>`.
- **Per-service offered load / goodput / rejection** = differences between consecutive `service_inbound.csv` rows for that service (`Δtotal`, `Δ2xx`, `Δ4xx+Δ5xx`).

**Live gap (2026-09-08 smoke, still true):** live outbound `cluster.outbound|…upstream_rq_*` on our Istio/Envoy build exposes `total` and `retry` but not `2xx`/`4xx`/`5xx` — those class columns in `service_edges.csv` stay `0` even under load. Use `service_inbound.csv`'s `2xx`/`4xx`/`5xx` for per-hop goodput/rejection instead; use `service_edges.csv`'s `total`/`retry` for outgoing volume and retries.

All counters are **cumulative** for the pod's lifetime (Envoy never resets mid-run). Every derived value (retries-per-request, RPS, rejection) is a **diff between consecutive polls of the same row**, never the raw value.

```python
# service_edges.csv, consecutive rows for the same (caller, target)
d_retry = row_n["retry"] - row_n1["retry"]
d_total = row_n["total"] - row_n1["total"]
retries_per_request = (d_retry / d_total) if d_total > 0 else 0.0

# service_inbound.csv, consecutive rows for the same service
d_5xx = row_n["5xx"] - row_n1["5xx"]
d_total_in = row_n["total"] - row_n1["total"]
rejection = (d_5xx / d_total_in) if d_total_in > 0 else 0.0   # what RetryGuard actually reads
```

Join against `retryguard.log` toggle timestamps to show that `ON→OFF` reduces the retry rate / rejection on that service.

> **Prerequisite (handled automatically):** Istio's default stats reduction hides `upstream_rq_retry*` / `downstream_rq_*` from the plain `/stats` dump unless the pod carries a `sidecar.istio.io/statsInclusionRegexps` annotation. `run_scenario.py::ensure_envoy_stats_enabled()` patches **all 11** Deployments with `(cluster\.outbound.*upstream_rq.*)|(http\.inbound.*downstream_rq.*)` before every run (idempotent — a no-op rollout after the first time).

### Legacy per-caller files (historical only — `campaign_48/` and `august_38/`)

Before 2026-09-08 the collector only scraped two caller sidecars and wrote:

| File | Caller sidecar scraped | Target services in rows |
|------|------------------------|-------------------------|
| `envoy_retries_frontend.csv` | `frontend` | `cartservice`, `productcatalogservice`, `checkoutservice` |
| `envoy_retries_checkoutservice.csv` | `checkoutservice` | `cartservice`, `productcatalogservice`, `paymentservice` |

Columns: `timestamp, target_service, upstream_rq_total, upstream_rq_retry, upstream_rq_retry_success, upstream_rq_retry_limit_exceeded` — same cumulative/diff rule as above. **This code path no longer exists** in `envoy_retry_collector.py`; a run either has these two files (collected before the rewrite) or the two full-mesh files above — never both. `mentor_charts.py` / `mentor_charts_data.py` still only read this legacy shape; wiring them to the full-mesh files is a documented follow-up, not evidence that mesh data is unavailable.

> The August 38 and `campaign_48/` folders have only the legacy files. No folder anywhere has the full-mesh files yet — the next new run will be the first.

---

## 6. The resource usage CSV (CPU/memory per service)

**Files** (when `resource_usage_collector.enabled: true`):

| File | Source | Content |
|------|--------|---------|
| `resource_usage.csv` | kubelet `stats/summary` via `kubectl get --raw` | Per-service CPU and memory, one row per service per poll |
| `resource_usage_collector.log` | — | `START` / `WARNING` / `SHUTDOWN` / `EXIT` lines |

Scrapes the worker node's kubelet summary API. App-container usage only (`istio-proxy` and `POD` pause containers are skipped). Services with no matching pod in a given poll are omitted (not zero-filled).

### Columns

```
timestamp, service, cpu_millicores, memory_working_set_bytes, replica_count
```

| Column | Meaning |
|--------|---------|
| `timestamp` | UTC ISO time of the poll |
| `service` | Deployment name (`checkoutservice`, `paymentservice`, …) |
| `cpu_millicores` | Sum of app-container `usageNanoCores` across replicas, in millicores |
| `memory_working_set_bytes` | Sum of app-container working-set memory across replicas |
| `replica_count` | `readyReplicas` from the Deployment status (always `1` in this workshop's fixed-replica setup) |

Default poll interval: **5s**. A 600s run produces ~120 rows per service.

Join against `retryguard.log` toggle timestamps to show CPU/memory dropping after `ON→OFF` on a service.

> The existing 38 matrix folders do **not** contain this file — they predate the collector.

---

## 7. The TopFull throttle CSVs (Layer A cap/admitted, Layer B detector reconstruction)

**Files** (when `topfull_throttle_collector.enabled: true`, `poll_interval_seconds: 1`, all 16 scenario YAMLs since 2026-09-09):

`experiments/topfull_throttle_collector.py` runs **on master**, on the same wall-clock-aligned 1s grid as the mesh collector (both use `sleep_until_next_tick()` / `tick_timestamp()`, so a row's `timestamp` in `topfull_throttle.csv` lines up exactly with the same-second row in `service_edges.csv` / `service_inbound.csv` / `resource_usage.csv`).

### `topfull_throttle.csv` — Layer A: what TopFull actually admitted

One row per `(timestamp, api)` for the 5 Locust APIs:

```
timestamp, api, threshold, admitted_rps, threshold_fresh, admitted_fresh
```

| Column | Source | Meaning |
|---|---|---|
| `threshold` | proxied `GET :8090/thresholds` (fallback: `cat rate_config/<api>` under `proxy_dir`) | The RL-set admission cap for that API this tick |
| `admitted_rps` | proxied `GET :8090/stats` | What the goproxy actually forwarded — a truer "admitted load" than Locust `RPS`, which is measured *after* the proxy |
| `threshold_fresh` / `admitted_fresh` | collector bookkeeping | `1` if measured this tick, `0` if carried forward from the last successful scrape (goproxy times out under heavy load) — **filter to `*_fresh == 1` for a true per-second series** |

Why measure this at all: Locust `RPS` (Layer 1) is *completed* traffic after every hop, including retries — a weak proxy for what TopFull's RL loop actually let through. `num_agent.csv` (TopFull's own admission counter) is empty in every run and won't be revived. This collector answers "what did the controller admit," independent of what came back successful.

### `topfull_detect.csv` — Layer B: reconstructed overload-detector state

One row per `(timestamp, service)` for the 11 Boutique services:

```
timestamp, service, cadvisor_cpu, quota, alpha, utilization, overloaded
```

| Column | Source | Meaning |
|---|---|---|
| `cadvisor_cpu` | direct HTTP scrape of the **cAdvisor DaemonSet** (`cadvisor` namespace) — `GET http://<cadvisor-pod-ip>:8080/api/v2.0/summary/<container_id>?type=docker`, container IDs discovered via `kubectl get po -o json` | CPU usage as TopFull's own `Detector` would see it — **not** the same source as `resource_usage.csv` (which reads kubelet `stats/summary`, Layer 2) |
| `quota` | `topfull_cpu_quotas.paper_limit_for(service)`, overridden per-run by the `cpu_quotas` param (= that run's `effective_cpu_quotas`, i.e. the paper table with the S3/S4 bottleneck fraction applied) | The CPU ceiling the detector compares against — kept in sync with whatever `run_scenario.py` actually reconciled onto the live Deployment that run (see §7b) |
| `alpha` | `0.95` for `productcatalogservice` / `cartservice`, else `0.8` | The detector's main-loop threshold fraction (`Detector.detect(0.8)`); this is an *approximation* — real calls from `apply()`/`apply_v2()` also use `0.9`, not reconstructed here |
| `utilization` | `cadvisor_cpu / quota` | — |
| `overloaded` | `utilization > alpha` | Reconstructed overload bool |

**Out of scope, by design:** Layers C (clustering) and D (RL action/state) are not collected — getting TopFull's *real* internal values would require patching `Detector.clustering()` / `Agent.run()`, which run on TopFull's own irregular per-thread cadence and would break the same-second-join guarantee this collector exists to provide. `mentor_charts.py` does not read either of these files yet.

> No campaign folder has this data yet (implemented 2026-09-09, after `campaign_48/` was collected). See [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md) for the full inventory this collector was designed against.

---

## 7b. Capacity and quota artifacts (not time series)

Two artifacts record what CPU ceiling was in effect for a run — useful context for interpreting `resource_usage.csv` / `topfull_detect.csv`, but not themselves a metric to chart over time.

| File | Written by | When | Content |
|---|---|---|---|
| `service_capacity.json` | `run_scenario.py::capture_service_capacity()` | Once, **before** any `scale_constraints` are applied | `{service: {cpu_limit_millicores, cpu_request_millicores, replica_count}}` — the *original* (paper-reconciled) limits, so you can see what an S3/S4 bottleneck was constrained *from* |
| `topfull_run_quotas.json` (on master only, **not** copied into the run folder) | `run_scenario.py::write_run_quotas_json()` | At run start; deleted at teardown | The *effective* per-run quota map (paper table + any active `cpu_limit_fraction`), read by a small overlay `Detector.__init__` patches in so its in-memory quotas match K8s for that run |

`run_manifest.json`'s `paper_cpu_quotas` / `effective_cpu_quotas` fields (see §8) are the same maps, persisted for after-the-fact reference once `topfull_run_quotas.json` itself has been deleted from master.

---

## 8. The run manifest

**File:** `run_manifest.json` — written by `run_scenario.py` at the end of collection.

```json
{
  "scenario_id": 2,
  "scenario_name": "sustained_overload",
  "condition": "baseline",
  "run_number": 1,
  "duration_seconds": 600,
  "retryguard": { "enabled": false, ... },
  "envoy_retry_collector": { "enabled": true, "poll_interval_seconds": 1 },
  "resource_usage_collector": { "enabled": true, "poll_interval_seconds": 5 },
  "topfull_throttle_collector": { "enabled": true, "poll_interval_seconds": 1 },
  "scale_constraints": [],
  "paper_cpu_quotas": { "cartservice": 1000, "currencyservice": 1000, "frontend": 1000, "adservice": 1000, "productcatalogservice": 500, "checkoutservice": 1000, "recommendationservice": 2000, "paymentservice": 1000 },
  "effective_cpu_quotas": { "cartservice": 1000, "currencyservice": 1000, "frontend": 1000, "adservice": 1000, "productcatalogservice": 500, "checkoutservice": 1000, "recommendationservice": 2000, "paymentservice": 1000 },
  "log_folder": "baseline_topfull_no_retryguard_sustained_overload_run1",
  "collected_at": "2026-08-11T10:00:00Z"
}
```

This makes each folder self-describing — you don't need to look up the YAML to know what produced it.

---

## 9. How to pull results to your PC

After each run completes, the runner prints the `scp` command for you — it already resolves the correct scenario subfolder (e.g. `S2_sustained_overload/`) from the run's `scenario_id`/`scenario_name`:

```powershell
# Pull one run folder into the campaign tree (Phase 7 primary), routed into its scenario subfolder
scp -r topfull-master:/home/idozacharia/experiments/results/<log_folder> experiments/results/campaign_48/<Sx_scenario_name>/
```

Master still stores a flat `/home/idozacharia/experiments/results/<log_folder>/`. **Do not** `scp -r` the entire remote `results/` tree onto the laptop — that would dump campaign and August folders into one mix again.

Local layout — `campaign_48/` is organized into one subfolder per scenario, each holding that scenario's baseline + RetryGuard run folders (S5 is RetryGuard-only):

```
experiments/results/
  campaign_48/                          ← 48-run Phase 7 campaign (primary analysis)
    S1_normal_op/
    S2_sustained_overload/
    S3_targeted_bottleneck/
    S4A_topology_position_A/
    S4B_topology_position_B/
    S5_interval_tuning/
    S6_forced_recovery/
      baseline_topfull_no_retryguard_forced_recovery_run1/
        getproduct.csv
        postcheckout.csv
        envoy_retries_frontend.csv       ← legacy shape; future runs get service_edges.csv / service_inbound.csv instead
        resource_usage.csv
        ...
        run_manifest.json
        service_capacity.json
  august_38/            ← historical August 38 (goodput/P95/rejection only, still flat — not reorganized)
```

See [experiments/results/README.md](../experiments/results/README.md) and [experiments/results/campaign_48/README.md](../experiments/results/campaign_48/README.md) for the full scenario→folder map.

---

## 10. Verifying a run after collection

Before moving on to the next run or repeating, do a quick sanity check:

```powershell
# On your PC — check row counts (should be ~duration_seconds rows)
(Get-Content experiments\results\<log_folder>\postcheckout.csv | Measure-Object -Line).Lines

# Or on master before pulling
ssh topfull-master "wc -l /home/idozacharia/experiments/results/<log_folder>/*.csv"
```

| Check | Expected | If wrong |
|-------|----------|----------|
| Row count ≈ `duration_seconds` | ~300 for S1, ~600 for S2–5 | Locust didn't start, or metric_collector died early |
| `RPS > 0` in most rows | Consistently positive after first ~10 rows | Locust spawn took too long, or connectivity issue |
| `Fail` near zero for S1 | `0` every row | Something wrong with the cluster — investigate before running S2+ |
| `Fail` elevated for S2/3 baseline | High throughout overload period | Expected and correct |
| `retryguard.log` exists (RetryGuard runs) | File present, `START` line at top | RetryGuard didn't start — check `tmux` session |
| `run_manifest.json` exists | Always | Runner aborted before collection step |
| `service_capacity.json` exists | Always (2026-09-08+ runs) | `capture_service_capacity()` failed before `scale_constraints` ran |
| `resource_usage.csv` has rows (when enabled) | `memory_working_set_bytes > 0` for `frontend` under any load | kubelet `stats/summary` blocked — check collector log on master |
| `service_edges.csv` / `service_inbound.csv` have rows (when enabled, 2026-09-08+ runs) | Non-empty, `total` columns increasing across polls | Stats-inclusion annotation not applied yet, or `kubectl exec` blocked — check `envoy_retry_collector.log` |
| `topfull_throttle.csv` / `topfull_detect.csv` have rows (when enabled, 2026-09-09+ runs) | `admitted_fresh`/`threshold_fresh` mostly `1`; `cadvisor_cpu > 0` under load | goproxy `/stats`/`/thresholds` timing out, or cAdvisor DaemonSet unreachable — check `topfull_throttle_collector.log` |
| After every run: Layer B max util / overloaded / hottest (`topfull_detect.csv`) | Per-service max `utilization`, `overloaded` count, `quota`, `alpha`, hottest services. Do not stop at `overloaded=0` / `cadvisor_cpu>0` | Missing table hides “almost fired” (e.g. frontend 0.74 vs α=0.8 on S2 run17) |

---

## 11. Collecting across runs for analysis (Phase 7 preview)

Each run folder is independent. For Phase 7, you'll load all runs for a given scenario+condition together.

**Pattern (Python):**

```python
import pandas as pd
from pathlib import Path

results = Path("experiments/results/campaign_48/S2_sustained_overload")

# Load all baseline runs for Scenario 2, postcheckout endpoint
runs = sorted(results.glob("baseline_topfull_no_retryguard_sustained_overload_run*/postcheckout.csv"))
dfs = [pd.read_csv(r) for r in runs]

# Per-run aggregate: mean goodput over the run
mean_goodputs = [df["Goodput"].mean() for df in dfs]

# Time-series average across runs (truncate to shortest run first)
min_len = min(len(df) for df in dfs)
avg_series = pd.concat([df["Goodput"].iloc[:min_len] for df in dfs], axis=1).mean(axis=1)
```

**Cross-referencing RetryGuard decisions with metrics:**

1. Find an `ON→OFF` timestamp in `retryguard.log` (e.g. `13:21:00Z`)
2. Estimate the row index: seconds since run start (check `run_manifest.json` `collected_at` and subtract)
3. Look at `postcheckout.csv` rows around that index — expect `Fail` to decrease and `Goodput` to rise within 1–2 rows (the controller acts at 30s granularity; the CSV records at 1s granularity)

---

## 12. Quick reference — per-scenario focus metrics

| Scenario | Primary files | What to look for |
|----------|--------------|-----------------|
| 1 — Normal Op | all 5 CSVs | `Fail=0` everywhere; `retryguard.log` shows zero `ON→OFF` lines |
| 2 — Sustained Overload | `postcheckout.csv`, `getproduct.csv` | Baseline: `Fail` high throughout. RetryGuard: `Fail` dips after toggle events |
| 3 — Targeted Bottleneck | `postcheckout.csv` (primary), all others (propagation) | Baseline: `postcheckout` rejection spikes. RetryGuard: toggle events in log align with goodput recovery |
| 4A — Topology: ProductCatalog | `getproduct.csv` | Same structure as S3 but at `getproduct` |
| 4B — Topology: Payment | `postcheckout.csv` | Payment is reached via checkout path — rejection appears in `postcheckout` |
| 5 — Interval Tuning | `postcheckout.csv` + `retryguard.log` | Count toggle events per run; compare time-to-recovery across interval configs |

---

*Related guides: [SCENARIOS-GUIDE.md](SCENARIOS-GUIDE.md) (how to run), [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md) (log format detail), [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md) §4 (data collection mechanics), [METRICS-GATHERED.md](METRICS-GATHERED.md) (full metric inventory), [METRICS-CATALOG.md](METRICS-CATALOG.md) (why each metric is collected).*
