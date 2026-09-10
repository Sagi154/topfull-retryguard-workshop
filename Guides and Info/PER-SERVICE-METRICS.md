# Per-service metrics vs Locust APIs

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Locust Layer 1 is **entry-API**, not per Kubernetes service. This note is whether we can still get **per-service** RPS, errors, latency, and retries, and how. What we already gather: [METRICS-GATHERED.md](METRICS-GATHERED.md). TopFull admission caps (also per Locust API, not per Deployment): [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md). Concrete collector design (outgoing/incoming retries, outgoing/incoming goodput, offered load, shared timestamps, and what we know about per-service capacity): [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md).

Locust is the wrong instrument for **the microservices themselves**. You can still get per-service metrics; most of them have to come from **Envoy sidecars** (and the CPU collector you already have), not from `metric_collector.py`.

Locust will never become per-service unless you stop using a storefront load and start calling each backend directly. That would no longer be Online Boutique as users hit it, and it would break TopFull (which throttles **entry APIs**). Keep Locust for client-visible outcomes; add a **service-level** layer next to it.

---

## What you already have that *is* per service

| Metric | File | Grain |
|---|---|---|
| CPU, memory, replica count | `resource_usage.csv` | All 11 deployments |
| Outbound retries to a **target** | `envoy_retries_*.csv` | cart, catalog, checkout, payment (only those four, and only as seen by frontend / checkout) |
| RetryGuard ON/OFF | `retryguard.log` | 9 HTTP backends (not frontend / redis-cart) |

RetryGuard’s **decision** signal is Envoy inbound `Δ5xx / Δtotal` from `service_inbound.csv` (one Algorithm 1 loop per HTTP backend except `frontend`). Locust `Fail/RPS` is still the **storefront outcome**, not the controller input. Mesh inbound / edges / CPU remain per-service outcomes and insights — see the practical-split table below. `mentor_charts.py` still plots Locust only; wiring mesh into charts is a follow-up, not a claim that mesh is not an outcome.

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
| Offered load | `upstream_rq_total` on **inbound** | Requests that reached this service |
| Failures | `upstream_rq_5xx` / `4xx` / `cx_destroy` | Hop-level, not Locust Fail |
| Rejection rate | `5xx / total` (differenced) | Closest to the RetryGuard **paper** (mesh rejection, not Locust) |
| Hop latency | `upstream_rq_time` histogram → P95 | Time **at this service**, not end-to-end |
| Retries **to** it | caller’s outbound `upstream_rq_retry` | You already do this for 4 targets |
| Retries **from** it | this pod’s outbound retry stats | e.g. checkout → payment |

That is enough for: per-service RPS, error rate, P95 hop latency, retries. “Goodput” at a service is then `Δtotal − Δ5xx` on inbound — useful, but **not** the same column as Locust `Goodput`.

Boutique internals are mostly **gRPC**; Envoy still exposes cluster stats. `redis-cart` is TCP — HTTP 5xx will not exist there; stick to CPU/memory (already collected) or TCP counters if you care.

---

## How you would actually collect it

Same pattern as `envoy_retry_collector.py`, widened:

1. **Patch stats inclusion on every Deployment**, not only `frontend` / `checkoutservice`. Today Istio strips detailed cluster stats unless `sidecar.istio.io/statsInclusionRegexps` is set. Without that, you get all-zero CSVs (you already hit this once).
2. **`kubectl exec` each `istio-proxy`** on a 5 s poll (you already do this for two callers).
3. Parse **inbound** clusters for that pod’s service name, plus optional outbound to children.
4. Write e.g. `envoy_inbound.csv`:

```
timestamp, service, rq_total, rq_2xx, rq_5xx, rq_retry, ...
```

Derive RPS / rejection / retries-per-request by differencing, same as retries today.

You do **not** need Prometheus for this. A dedicated Prometheus + Istio telemetry is cleaner at scale; for 11 pods the exec scraper is consistent with what you already run.

---

## What you still should *not* expect

- **Locust P95 / goodput per microservice** — Locust never addresses `paymentservice`. No collector can invent that from Locust dumps.
- **One number that is both “user checkout” and “payment pod”** — those are different hops. Report them as two series.
- **Backfill of `campaign_48/`** — those runs did not scrape inbound. New collector → new runs (or a small extra campaign).
- **TopFull throttle per service** — TopFull caps **Locust APIs**, not Deployments. Per-service throttle does not exist; only `rate_config/getproduct` etc. See [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md).

---

## Practical split for the report

| Question | Instrument |
|---|---|
| Did RetryGuard help **users**? | Locust CSVs (`total` / `postcheckout` / …) |
| Which **service** was overloaded / relieved? | kubelet CPU + Envoy **inbound** |
| Did retries at that service drop? | Envoy **outbound** retries (extend to all callers/targets if needed) |
| What did RetryGuard decide? | `retryguard.log` |
| What did TopFull admit? | proxy `rate_config` + `/stats` (not per service) |

Locust APIs are a poor fit for **per-service** questions, and that is expected. Per-service RPS, errors, hop latency, and retries **are** possible from Envoy; CPU/memory you already have. The missing piece is an inbound (and optionally full-mesh outbound) scraper, plus stats annotations on all services — not a change to Locust.

If built, the natural implementation is to extend `envoy_retry_collector.py` (or a sibling `envoy_service_collector.py`) rather than patching TopFull’s `metric_collector.py`.
