# Metrics Catalog — what we collect, how, and why

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Purpose:** one place that answers, for **every** metric this project collects: *what it is*, *exactly how it's measured*, and *why we bother measuring it* (which open question or comparison it feeds). This is the "why" companion to [METRICS-GATHERED.md](METRICS-GATHERED.md) (file/column inventory) and [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) (operational how-to: pull/verify/load). Per-service feasibility background: [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md). Collector designs: [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md), [docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md](../docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md).
>
> Read this if you're writing the Phase 7 report and need to justify *why a number is in the paper at all* — every row below traces back to either the eval deck's open questions (context/Evaluating_RetryGuard_on_TopFull.md, slides 8–9) or a specific gap the project closed (PHASE7-DATA-GAPS.md).

---

## 1. The five vantage points, at a glance

Every metric in this project is measured from one of five vantage points in the stack. Understanding *which* vantage point a number comes from is the single most important thing for interpreting it correctly — the same word ("goodput", "rejection", "retries") means something different depending on where you stand.

```
Locust (topfull-load)
  │  HTTP calls to 5 storefront APIs
  ▼
frontend ──▶ TopFull proxy (rate limiter) ──▶ Istio sidecar (frontend) ──▶ backend services' sidecars ──▶ backend pods
  │                    │                              │                            │
  │                    │                              │                            │
Locust CSVs      topfull_throttle.csv          service_edges.csv /          resource_usage.csv
(client-visible   (what the RL loop           service_inbound.csv          (CPU/memory the pod
 outcome, after    actually admitted,          (mesh-level retries,         actually consumed)
 every retry)      before mesh retries)        offered load, status)
                                                        │
                                            topfull_detect.csv
                                            (reconstructed: did the
                                             detector think this pod
                                             was overloaded?)
```

| # | Vantage point | Measures | Files |
|---|---|---|---|
| 1 | **Client-visible outcome** (Locust, after every hop and every retry) | Did the *user's* request succeed, and how fast? | `getproduct.csv`, `postcheckout.csv`, `getcart.csv`, `postcart.csv`, `emptycart.csv`, `total.csv` |
| 2 | **TopFull's admission decision** (proxy layer, before mesh retries) | What did the RL rate-limiter actually let through? | `topfull_throttle.csv` |
| 3 | **Mesh / per-service hop** (Envoy sidecars) | Who called whom, how often, with what status, and how many retries — one hop at a time | `service_edges.csv`, `service_inbound.csv` (full mesh); `envoy_retries_{frontend,checkoutservice}.csv` (legacy, 2 callers only) |
| 4 | **Infrastructure** (kubelet, cAdvisor) | How much CPU/memory did each pod actually burn? | `resource_usage.csv` (kubelet, Layer 2 "official" number); `topfull_detect.csv`'s `cadvisor_cpu` (cAdvisor, reconstructs what TopFull's detector itself would see — a second, deliberately separate CPU reading) |
| 5 | **Controller state** (RetryGuard's own decisions) | What did *our* controller decide, and when? | `retryguard.log` |

Plus two **static context artifacts** that aren't time series but are needed to interpret the above: `run_manifest.json` (what config produced this folder) and `service_capacity.json` (what CPU ceiling each service had before any scenario constrained it).

---

## 2. Vantage point 1 — Client-visible outcome (Locust / TopFull `metric_collector.py`)

**Why this vantage point exists at all:** this is the number a real user would experience. It's downstream of *everything* — TopFull's admission control, Istio's retries, the backend's actual capacity — so it's the only metric that can answer "did RetryGuard (or TopFull) make the **system** better," independent of mechanism. It is the eval deck's primary "goodput / P95 latency / rejection rate" comparison.

**How it's collected:** TopFull's own `metric_collector.py` runs on master, polls the Locust HTTP stats endpoint every second, and appends one row per second per API to five separate CSVs (one per Locust "task" — not per Kubernetes Deployment; see §7 for why that distinction matters). No shared module is added by us here — we consume TopFull's collector as-is; our contribution is enabling/orchestrating it via `run_scenario.py` and adding the derived-metric conventions in §2b.

| File | Locust request | Storefront action | Backend load path |
|---|---|---|---|
| `getproduct.csv` | Browse product | View a product page | `productcatalogservice` |
| `postcheckout.csv` | Submit checkout | Complete an order | `checkoutservice` → cart, catalog, currency, shipping, **payment**, email |
| `getcart.csv` | View cart | Open the cart page | `cartservice` (read) |
| `postcart.csv` | Add to cart | Add an item | `cartservice` (write) |
| `emptycart.csv` | Empty cart | Session teardown | `cartservice` (write) |
| `total.csv` | — (derived by TopFull, same 5 columns) | System-wide sum/mean of the five above | — |

### Columns and why each exists

| Column | What it measures | Why we report it |
|---|---|---|
| `RPS` | Offered load to that endpoint that second | Denominator for rejection rate; sanity-checks Locust is actually driving load (`RPS=0` for the first few rows while spawning is normal, sustained `RPS=0` is a bug) |
| `Fail` | Failed requests/sec (5xx or timeout) at the client | Numerator for rejection rate; the eval deck's core "did the system reject users" signal |
| `Goodput` | `RPS − Fail` | **Primary health metric.** Directly comparable across scenarios/conditions; this is what "does RetryGuard help" ultimately has to move |
| `Latency95` | 95th-percentile client latency, ms | **The latency metric of record.** P95 was chosen over mean because tail latency is what the RetryGuard/TopFull papers and the eval deck actually care about (a slow tail is what retries create) |
| `Latency99` | Always `0` | Hardcoded no-op in TopFull's collector, never computed. Kept in the CSV only because it's TopFull's unmodified output — **do not use**. P99 was explicitly dropped as a target metric (2026-08-20): neither source paper needs it and P95 already satisfies the eval deck |

### Derived value we compute at analysis time — rejection rate

Not a stored column. `rejection = Fail / RPS` (0 when `RPS == 0`). **Why derive rather than store:** it's a pure function of two columns TopFull already gives us; storing a third redundant column risks it going stale relative to the other two. **Important distinction:** this Locust-level rejection is the *storefront* outcome. RetryGuard's own decision input is a *different* rejection rate — mesh inbound `Δ5xx/Δtotal` from `service_inbound.csv` (§4) — because RetryGuard needs a per-service signal, not a per-storefront-API one. Don't conflate the two when writing the report.

---

## 3. Vantage point 2 — TopFull's admission decision (`topfull_throttle_collector.py`)

**Why this exists:** Locust `RPS`/`Goodput` is measured *after* the whole request path, including any retries Istio performed underneath TopFull's radar. It answers "did the user succeed," not "what did the rate limiter actually decide." TopFull's own admission-count file (`num_agent.csv`) is permanently empty (see §8), so without this collector there was **no** visibility into the RL loop's actual behavior at all — this is the fix for that gap.

**How it's collected:** `experiments/topfull_throttle_collector.py` runs on master on a **wall-clock-aligned 1-second grid** (`sleep_until_next_tick()` / `tick_timestamp()` — sleeps until the next `t mod 1 == 0` second, not "now + 1s", so it never drifts relative to the other 1s collectors). Each tick it makes a proxied `GET :8090/thresholds` and `GET :8090/stats` call to TopFull's goproxy admin endpoints (in parallel, via `ThreadPoolExecutor`, with an 0.8s timeout tuned below the 1s tick so a slow scrape doesn't compound into the next one) and appends one row per Locust API.

| Column | Source | Why we keep it |
|---|---|---|
| `threshold` | goproxy `/thresholds` (fallback: `rate_config/<api>` file on disk) | The RL-set admission cap that second — the actual "action" TopFull's controller took, otherwise invisible |
| `admitted_rps` | goproxy `/stats` | What was actually forwarded past the proxy — the truest "admitted load" number in the whole pipeline, upstream of any Istio-level retries |
| `threshold_fresh` / `admitted_fresh` | collector bookkeeping (`1` = measured this tick, `0` = carried over) | Under heavy load the goproxy admin endpoints themselves can time out; without this flag a "stuck" value would silently masquerade as a fresh reading and bias any RL-vs-RetryGuard oscillation analysis. **Filter to `*_fresh == 1`** before treating a row as a real per-second sample |

**Why the paired Layer B file exists too:** `topfull_detect.csv` reconstructs whether TopFull's overload **detector** (not the admission proxy) thought a given service was overloaded that second — `cadvisor_cpu / quota > alpha`. This lets you ask "was TopFull's *detection* signal firing on a service RetryGuard also acted on" — the core "controller interaction" open question (AGENTS.md §8). It deliberately reads CPU from a **second, independent** source (direct cAdvisor DaemonSet scrape, not kubelet `stats/summary`) specifically so this reconstruction matches what TopFull's own `Detector` code would have seen, rather than reusing the Layer 2 number for convenience. Layers C (clustering) and D (RL action/state) were explicitly scoped out — reaching them means patching TopFull's own threads, which run on an irregular, non-wall-clock-aligned cadence that would break the exact-same-second join this whole collector exists to provide.

**No campaign data yet.** Implemented 2026-09-09, after `campaign_48/` was collected — no run anywhere has these files today.

---

## 4. Vantage point 3 — Mesh / per-service hop (Envoy sidecars)

**Why this exists:** Locust only ever addresses 5 storefront APIs; it has no way to say anything about `paymentservice`, `currencyservice`, `shippingservice`, etc. as *services* — a `postcheckout` failure could be caused by any of six downstream services, and Locust can't tell you which. This is the eval deck's "topology beneficiaries" and "chain propagation" open question: which **service** benefited from RetryGuard, and did relief at a bottleneck propagate upstream. It's also the direct input to RetryGuard's own control loop — Algorithm 1 needs a per-service rejection rate, and Locust cannot provide one.

**How it's collected:** `experiments/envoy_retry_collector.py` runs on master (`transport: network_prometheus`). On each 1s-aligned tick a thread pool GETs `http://<pod_ip>:15020/stats/prometheus` for every Boutique pod (all 11 services, including `redis-cart`) and parses two disjoint Prometheus families out of that page:

- **Outbound** (`envoy_cluster_upstream_rq_total` / `_retry`, plus `envoy_cluster_upstream_rq{response_code_class="2xx|4xx|5xx"}` with `cluster_name="outbound|<port>||<target>.default.svc.cluster.local"`) — calls *this* pod's sidecar made, broken down by target → written to `service_edges.csv`, one row per `(timestamp, caller, target)` pair actually observed.
- **Inbound listener** (`envoy_http_inbound_<listener>_downstream_rq_total` and `envoy_http_inbound_<listener>_downstream_rq{response_code_class="2xx|4xx|5xx"}`) — calls *this* pod's sidecar received, from anyone → written to `service_inbound.csv`, one row per `(timestamp, service)`.

Files land in the run `record_path` on master during the run, so RetryGuard's `measure_value()` can read `service_inbound.csv` mid-run.

**Why both directions, not just one:** Envoy fundamentally only records "I retried this call" on the **caller's** outbound stats — the callee never knows a retry happened, it just sees extra inbound requests. So:
- Outgoing retries/goodput for a service = read its own row in `service_edges.csv` where it's the `caller`.
- **Incoming** retries at a service (not a real Envoy counter — has to be derived) = sum `retry` over every `service_edges.csv` row where it's the `target`, across *all* callers.
- Per-service offered load / rejection = differenced `service_inbound.csv` rows for that service. This is the exact signal RetryGuard's `measure_value()` reads (`Δ5xx/Δtotal`).

**Why a prerequisite patch is needed:** Istio's default stats reduction strips these counters from the plain `/stats` dump to save memory. `run_scenario.py::ensure_envoy_stats_enabled()` patches a `sidecar.istio.io/statsInclusionRegexps` annotation onto all 11 Deployments before every run — without it, every column here reads `0` regardless of load (a failure mode we hit and had to diagnose once already).

**Outbound class columns:** on this transport, `service_edges.csv` `2xx` / `4xx` / `5xx` are live. The old admin-port gap (class columns always 0) does **not** apply to new runs. Do not claim `campaign_48/` or `august_38/` have those non-zero class columns — they predate both the full-mesh files and this transport.

### Legacy shape (historical only — `campaign_48/`, `august_38/`)

Before 2026-09-08 the collector only scraped two caller sidecars (`frontend`, `checkoutservice`) and wrote `envoy_retries_frontend.csv` / `envoy_retries_checkoutservice.csv` (`timestamp, target_service, upstream_rq_total, upstream_rq_retry, upstream_rq_retry_success, upstream_rq_retry_limit_exceeded`). **Why it was narrow:** it only needed to cover the three services RetryGuard could toggle plus `paymentservice` for Scenario 4B — a minimum viable "retries per request" signal to close Gap 3 from the August audit. It was superseded, not extended — a run has either the legacy files or the full-mesh files, never both, and no folder anywhere yet has the full-mesh files (next new run will be first).

---

## 5. Vantage point 4 — Infrastructure: CPU and memory

Two independent CPU readings exist in this project, on purpose, for two different jobs. Do not merge them.

### 5a. `resource_usage.csv` — the "official" per-run CPU/memory number

**Why it exists:** the eval deck's Layer 2 asks for CPU/memory per service to see whether RetryGuard/TopFull change *resource pressure*, not just request outcomes — e.g. does disabling retries on an overloaded service measurably lower its CPU. TopFull's own in-memory `resource_collector.py` only feeds its RL loop; it never wrote a per-run file, so without this collector Layer 2 simply didn't exist for analysis.

**How it's collected:** `experiments/resource_usage_collector.py` runs on master, polls the worker node's kubelet `stats/summary` API via `kubectl get --raw /api/v1/nodes/<node>/proxy/stats/summary` every 5s, and sums app-container `usageNanoCores`/`workingSetBytes` per pod → per service (skipping `istio-proxy` and the pause container, since we care about application load, not mesh overhead). Also reads `kubectl get deploy -o json` for `readyReplicas` (always `1` in this fixed-replica design, kept as a column for completeness/future-proofing rather than because it varies).

### 5b. `topfull_detect.csv`'s `cadvisor_cpu` — the detector-reconstruction number

**Why a second CPU source, not a reuse of 5a:** the goal of `topfull_detect.csv` (§3) is to reconstruct what TopFull's *own* `Detector` believed, and TopFull reads cAdvisor directly, not kubelet `stats/summary`. Using the kubelet number here would silently change what's being reconstructed and could disagree with TopFull's real internal state for reasons that have nothing to do with the experiment (e.g. kubelet vs cAdvisor accounting differences). So this collector scrapes the `cadvisor` DaemonSet's per-container HTTP API directly (`GET :8080/api/v2.0/summary/<container_id>?type=docker`), matching TopFull's own vantage point at the cost of a second, separate scrape path.

---

## 6. Vantage point 5 — Controller state (`retryguard.log`)

**Why it exists:** every other metric is an *effect*; this is the *cause*. Without a timestamped record of when RetryGuard flipped a service ON/OFF, none of the other time series can be attributed to RetryGuard's actions rather than to TopFull, load randomness, or coincidence. It's also the primary evidence for the "controller interaction" and "interval sensitivity" open questions (does the paper's 30s default hold up, does RetryGuard oscillate against TopFull's 1s loop).

**How it's collected:** `experiments/retryguard.py` (only running in RetryGuard-condition runs) reads `service_inbound.csv` every 1s for each of `CONTROLLED_SERVICES` (9 HTTP backends — every Boutique service with an Istio VirtualService except `frontend`, which is the ingress, not a callee, and `redis-cart`, which is TCP, not HTTP). For each service it computes `Δ5xx/Δtotal` since the last consumed row (Algorithm 1's `measure_value()`, applied literally to the paper: 1 raw sample per second, no averaging, one symmetric `interval_samples` window — default 30 — for both the disable and the re-enable transition). When `interval_samples` consecutive samples cross the `rejection_threshold` (default 20%), it patches that service's Istio VirtualService (`retries.attempts` omitted to disable, `= 3` to restore) and logs the transition.

| Log keyword | Why we log it |
|---|---|
| `START` | Records the exact params in effect — makes the log self-describing without cross-referencing the YAML |
| `OBSERVE` | One line per sample per service — lets you reconstruct the exact rejection trace RetryGuard saw, not just the moments it acted, useful for debugging "why didn't it toggle" |
| `ON→OFF` / `OFF→ON` | The actual controller actions — the timestamps every other CSV gets overlaid against in charts |
| `SKIP` | No newer `service_inbound.csv` row yet this tick — distinguishes "controller is idle because there's nothing new" from "controller is broken" |
| `PATCH_FAIL` | The Kubernetes API patch itself failed — surfaces infra problems (permissions, apiserver hiccups) separately from control-logic problems |

---

## 7. Static context artifacts (not time series, but needed to interpret the rest)

| File | Why it exists |
|---|---|
| `run_manifest.json` | Makes every result folder self-describing (scenario, condition, run number, duration, which collectors were on, and — since 2026-09-10 — `paper_cpu_quotas`/`effective_cpu_quotas`) so nobody has to cross-reference a YAML (which may have since been bumped to a new `run_number`) to know what produced a given folder |
| `service_capacity.json` | Snapshotted once per run, **before** any `scale_constraints` are applied. Without it, "checkoutservice was constrained to 100m in S3" has no baseline to compare against — you'd have to know the paper's original 1000m limit from memory |
| `topfull_run_quotas.json` (master-only, not copied into results) | Not a metric — it's the mechanism that keeps K8s CPU limits and TopFull's in-memory `Detector` quotas in agreement for a given run (a small overlay patched into `Detector.__init__`). Recorded here because `topfull_detect.csv`'s `quota` column and `run_manifest.json`'s `effective_cpu_quotas` are both downstream of this file, and without knowing it exists the `quota` column looks like a mystery constant |

---

## 8. Deliberately not collected (and why)

| Thing | Why we don't have it | Where documented |
|---|---|---|
| `Latency99` (true P99 client latency) | Hardcoded `0` in TopFull's own collector; P99 dropped as a target metric on 2026-08-20 — neither the RetryGuard paper (average-latency-based), the TopFull paper (goodput-based), nor the eval deck ("generic API latency") required it, and P95 already satisfies all three | [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 2 |
| `num_agent.csv` (TopFull's own RL admission counts) | Always empty in TopFull's own implementation — not something we broke, and not revivable without patching TopFull internals we've chosen not to touch. `topfull_throttle.csv` (§3) is the replacement signal | [METRICS-GATHERED.md](METRICS-GATHERED.md) |
| Per-service **Locust-grain** goodput/P95 (e.g. "Locust P95 for `paymentservice`") | Locust never addresses backend services directly — it only calls the 5 storefront APIs a real shopper would call. Inventing a per-service Locust number would mean changing what's being load-tested (no longer "Online Boutique as users hit it") and would break TopFull, which throttles entry APIs, not Deployments | [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md) |
| Per-service **admission throttle** (e.g. "TopFull capped `checkoutservice` to X rps") | TopFull's rate limiter caps Locust APIs, not Kubernetes Deployments — there is no `rate_config/checkoutservice`, only `rate_config/postcheckout`. `topfull_detect.csv` gives a per-service *overload* signal (CPU vs quota) but that's a different thing from an admission cap | [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md) |
| TopFull's Layer C (clustering) / Layer D (RL action/state) internals | Reaching the real values means patching `Detector.clustering()` / `Agent.run()`, which run on TopFull's own irregular per-thread cadence — not phase-aligned to wall-clock seconds or to each other. Patching them would break the exact-same-second join every other 1s collector in this project relies on | [docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md](../docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md) §1 |
| Pod autoscaling / instance counts over time | Replica count is fixed at 1 everywhere by experimental design (`instance_scaling.py`); Scenarios 3/4 constrain via CPU limit, not replica count, so there is nothing to measure here | [METRICS-GATHERED.md](METRICS-GATHERED.md) Layer 2 |

---

## 9. Metric → open question map

Cross-reference against AGENTS.md §8 / the eval deck (slides 8–9):

| Open question | Metric(s) that answer it |
|---|---|
| Does RetryGuard help at the **system level**? | Locust `total.csv` `Goodput`/`Latency95`/derived rejection (§2) |
| Does RetryGuard help at the **per-microservice level**, and which services benefit most? | `service_inbound.csv` (per-service rejection), `resource_usage.csv` (per-service CPU/memory), `service_edges.csv` (per-service retries) (§4, §5a) |
| **Chain propagation** — does relief at a bottleneck propagate upstream to callers? | `service_edges.csv` joined across hops, cross-referenced with the 5 Locust endpoint CSVs (coarse — only 5 storefront APIs) (§2, §4) |
| **Controller interaction** — how do TopFull's RL loop and RetryGuard interact? | `topfull_throttle.csv` (RL admission), `topfull_detect.csv` (RL's overload belief), `retryguard.log` (RetryGuard's own actions), joined on their shared 1s wall-clock grid (§3, §6) |
| **Topology position sensitivity** (S4A vs S4B) | `postcheckout.csv` / `getproduct.csv` (§2) plus `service_inbound.csv` at `paymentservice` vs `productcatalogservice` (§4) |
| **Interval sensitivity** (paper's 30s default) | `retryguard.log` toggle counts/timing across Scenario 5's `interval_samples` sweep (10/20/30/60), cross-referenced with `postcheckout.csv` recovery time (§2, §6) |

---

## 10. Clock alignment — the one thing to always double-check

Three different clock conventions exist in this project's files. Getting this wrong silently misaligns a chart.

| Files | Clock | Practical effect |
|---|---|---|
| Locust CSVs (`getproduct.csv`, …, `total.csv`) | **No timestamp column.** Row index *i* ≈ second *i* since `metric_collector.py` started | Toggle overlays on Locust charts are index-based, not timestamp-based |
| `resource_usage.csv`, legacy `envoy_retries_*.csv` | UTC ISO timestamp, stamped at **loop-iteration start**, then `time.sleep(interval)` — drifts a few seconds relative to Locust's t0, and two such collectors started seconds apart drift relative to *each other* over a long run | Don't assume "CPU dip at 60s" and "toggle at 60s" on a Locust chart are the same instant |
| `service_edges.csv`, `service_inbound.csv`, `topfull_throttle.csv`, `topfull_detect.csv` | UTC ISO timestamp, **wall-clock-aligned** via `sleep_until_next_tick()`/`tick_timestamp()` — every row is stamped with `floor(unix_time / interval) * interval`, so any two of these four files share exactly the same timestamp string for the same second, directly joinable with a plain merge on `timestamp` | This is the one guarantee in the whole system: join these four on `timestamp` with no fuzzy-matching needed |

All counters that are **cumulative** (every Envoy stat, in both the legacy and full-mesh shapes) must be **differenced between consecutive polls of the same row** before use — the raw value is a lifetime total across the whole pod's uptime (which can span multiple runs on the same cluster), not a per-run figure.
