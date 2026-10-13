# Per-service metrics vs Locust APIs

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Locust Layer 1 is **entry-API**, not per Kubernetes service. This note is whether we can still get **per-service** RPS, errors, latency, and retries, and how. What we already gather: [METRICS-GATHERED.md](METRICS-GATHERED.md); why we gather each one: [METRICS-CATALOG.md](METRICS-CATALOG.md). TopFull admission caps (also per Locust API, not per Deployment): [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md). Concrete collector design (outgoing/incoming retries, outgoing/incoming goodput, offered load, shared timestamps, and what we know about per-service capacity): [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md).

Locust is the wrong instrument for **the microservices themselves**. You can still get per-service metrics; most of them have to come from **Envoy sidecars** (and the CPU collector you already have), not from `metric_collector.py`.

Locust will never become per-service unless you stop using a storefront load and start calling each backend directly. That would no longer be Online Boutique as users hit it, and it would break TopFull (which throttles **entry APIs**). Keep Locust for client-visible outcomes; add a **service-level** layer next to it.

---

## What you already have that *is* per service

| Metric | File | Grain |
|---|---|---|
| CPU, memory, replica count | `resource_usage.csv` | All 11 deployments |
| Outbound edges (total / retry / status, all callers→targets seen) | `service_edges.csv` (every `final results/` hold; not in `campaign_48/` or `august_38/`) | All 11 deployments, every `(caller, target)` pair actually observed |
| Inbound offered load, status, resets, sojourn, gRPC codes | `service_inbound.csv` (same folders) | All 11 deployments |
| Pre-constraint CPU limit/request/replica snapshot | `service_capacity.json` (same folders) | All 11 deployments, once per run |
| ~~Outbound retries to a **target** (legacy, superseded)~~ | `envoy_retries_*.csv` | Historical only (`campaign_48/`, `august_38/`) — cart, catalog, checkout, payment, only as seen by frontend / checkout. Later holds have `service_edges.csv` / `service_inbound.csv` instead, never both. |
| RetryGuard sheds, climbs, re-enables | `retryguard.log` | 14 caller→callee edges. Shed is edge rpr. Re-enable is inbound rejection. Not frontend / redis-cart. |
| TopFull's own admission cap / admitted RPS (Locust-API grain, not per-service) | `topfull_throttle.csv` (every `final results/` hold; not in `campaign_48/` or `august_38/`) | 5 Locust APIs |
| Reconstructed overload-detector state (CPU vs quota × alpha) | `topfull_detect.csv` (same folders) | All 11 deployments |

Locked RetryGuard **sheds** on edge rpr from `service_edges.csv` (`Δretry / (Δtotal − Δretry)`). It **re-enables** on inbound rejection from `service_inbound.csv`, the same formula `analysis_score.py` prints. Locust `Fail/RPS` is the **storefront outcome**, not the controller input. `mentor_charts.py` still plots Locust only; wiring mesh into charts is a follow-up.

---

## What “per service” can mean (pick this first)

A Locust `postcheckout` failure is “the shopper’s checkout call failed.”  
A **per-service** number is “this **pod** was asked to do work, and it succeeded or not.”

Those disagree on purpose:

- `paymentservice` can be at 100% CPU while Locust still records some checkout successes (retries, timeouts elsewhere).
- `checkoutservice` inbound can look healthy while Locust `postcheckout` is red (frontend / TopFull / catalog).
- One service (`productcatalogservice`) is hit by **several** Locust APIs (`getproduct` and part of `postcheckout`).

So you want **both**: Locust = experiment outcome at the door; Envoy/kubelet = what each service experienced.

---

## What Envoy can give you, per service

Every Boutique pod already has `istio-proxy`. Envoy already counts **inbound** (work that landed on this service) and **outbound** (calls this service made).

Typical counters (same family as the retry collector):

| Per-service metric | Envoy idea | Notes |
|---|---|---|
| Offered load | inbound `downstream_rq_total` | Requests that reached this service |
| Failures | inbound `5xx` / `4xx` / `resets`, plus `grpc_4` / `grpc_14` on four read callees | Hop-level, not Locust Fail |
| Rejection rate | `(Δ5xx + Δresets) / Δtotal`, plus the two gRPC codes on those four | What the controller and the scorer both use for re-enable. Not Locust `Fail/RPS`. |
| Hop sojourn | inbound `downstream_rq_time` → `Δsum / Δcount`, and the `le=500` bucket | Time **at this service**, not end-to-end. Outbound `upstream_rq_time` stays 0 on this cluster. |
| Retries **to** it | sum of callers' outbound `retry` where `target` is this service | `service_edges.csv`, all callers, not four targets |
| Retries **from** it | this pod’s outbound `retry` | e.g. checkout → email |

That is enough for: per-service RPS, error rate, sojourn, retries. “Goodput” at a service is then `Δ2xx` on inbound — useful, but **not** the same column as Locust `Goodput`.

Boutique internals are mostly **gRPC**; Envoy still exposes cluster stats. `redis-cart` is TCP — HTTP 5xx will not exist there; stick to CPU/memory (already collected) or TCP counters if you care.

---

## How it is collected (since 2026-09-13)

`experiments/envoy_retry_collector.py` scrapes every Boutique sidecar from master. Full design, including what changed from the first sketch: [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md).

1. **Stats inclusion patched on all 11 Deployments** via `run_scenario.py::ensure_envoy_stats_enabled()`, regex `(cluster\.outbound.*upstream_rq.*)|(http\.inbound.*downstream_rq.*)`.
2. **Network scrape, not exec.** Each 1 s poll GETs `http://<pod_ip>:15020/stats/prometheus`. There is no `kubectl exec` and no `curl localhost:15000/stats`.
3. Parses Prometheus outbound cluster stats and inbound listener stats, including `resets`, `rq_time_*`, `rq_time_buckets`, and `grpc_2` / `grpc_4` / `grpc_13` / `grpc_14`.
4. Writes two CSVs (edges and inbound stay separate so "who called whom" survives):
   - `service_edges.csv`: `timestamp, caller, target, total, 2xx, 4xx, 5xx, retry, rq_time_sum_ms, rq_time_count`
   - `service_inbound.csv`: `timestamp, service, total, 2xx, 4xx, 5xx, resets, rq_time_sum_ms, rq_time_count, rq_time_buckets, grpc_2, grpc_4, grpc_13, grpc_14`

On `transport: network_prometheus`, outbound `2xx` / `4xx` / `5xx` are live. The old admin-port gap (those columns always 0) does not apply to `final results/` holds. Outbound `rq_time_*` stays structurally 0. `campaign_48/` and `august_38/` still have only the legacy `envoy_retries_{frontend,checkoutservice}.csv` shape. `mentor_charts.py` still only reads that legacy shape.

RPS, rejection, and retries per first attempt are differenced at analysis time. `python experiments/analysis_score.py <run_dir>` prints them ([ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md), [METRICS-GATHERED.md](METRICS-GATHERED.md#derived-metrics-analysis_scorepy)).

---

## What you still should *not* expect

- **Locust P95 / goodput per microservice** — Locust never addresses `paymentservice`. No collector can invent that from Locust dumps.
- **One number that is both “user checkout” and “payment pod”** — those are different hops. Report them as two series.
- **Backfill of `campaign_48/` or `august_38/`** — those runs did not scrape the full mesh. The files exist on later holds under `final results/`.
- **TopFull throttle per service** — TopFull caps **Locust APIs**, not Deployments. See [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md).

---

## Practical split for the report

| Question | Instrument |
|---|---|
| Did RetryGuard help **users**? | Locust CSVs (`total` / `postcheckout` / …) |
| Which **service** was overloaded / relieved? | kubelet CPU + Envoy **inbound** + `topfull_detect.csv` |
| Did retries at that service drop? | Envoy **outbound** retries in `service_edges.csv` |
| What did RetryGuard decide? | `retryguard.log` (edge rpr shed, inbound-rejection re-enable) |
| What did TopFull admit? | `topfull_throttle.csv` (per Locust API, not per service) |

Locust APIs are a poor fit for **per-service** questions, and that is expected. Per-service RPS, errors, sojourn, and retries come from the mesh CSVs. CPU and memory come from `resource_usage.csv`.
