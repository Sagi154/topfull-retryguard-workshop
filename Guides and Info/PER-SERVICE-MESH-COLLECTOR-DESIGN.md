# Per-service mesh collector — design

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Design for gathering, **per Kubernetes service, with a shared timestamp**: outgoing retries, incoming retries, outgoing requests + status ("outgoing goodput"), incoming requests + status ("incoming goodput"), and offered load — plus what we know about each service's "capacity." Builds on [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md) (feasibility) and extends `experiments/envoy_retry_collector.py`. **Implemented (2026-09-08)** — see [Status](#status) below; no campaign run yet has this data (`campaign_48/` / `august_38/` still use the legacy collector outputs).

Those five metrics map almost 1:1 onto Envoy stats, but two of them (incoming retries, incoming requests) need a different vantage point than the current collector uses.

---

## Where each metric actually lives in Envoy

Envoy on **each** pod's sidecar exposes two families of counters: **outbound** (calls this pod *makes*) and **inbound/listener** (calls this pod *receives*). The current `envoy_retry_collector.py` only reads outbound retry counters from two callers. To get all five metrics for all 11 services you need both families, from **every** pod, every poll.

| Requested metric | Envoy source | Whose sidecar | Already collected? |
|---|---|---|---|
| (a) outgoing retries count | `cluster.outbound\|...\|<target>.upstream_rq_retry` | **This** service's own sidecar (outbound) | Partial — only `frontend` + `checkoutservice` today |
| (b) incoming retries count | *(does not exist directly)* — derived by summing (a) from every caller that targets this service | **Every caller's** sidecar, filtered to `target = this service` | No |
| (c) outgoing requests + status ("outgoing goodput") | `cluster.outbound\|...\|<target>.upstream_rq_{total,2xx,4xx,5xx}` | This service's own sidecar (outbound) | No — collector today only pulls the 4 retry counters, not 2xx/4xx/5xx |
| (d) incoming requests + status ("incoming goodput") | `http.inbound_<port>.downstream_rq_{total,2xx,4xx,5xx}` (listener stats, not `cluster.inbound`) | This service's **own** sidecar (inbound listener) | No |
| (e) offered load | `http.inbound_<port>.downstream_rq_total` (same stat as (d), interpreted as "attempted", before success/fail split) | Same as (d) | No |

Key fact worth being explicit about: **(b) is not a real Envoy counter.** Envoy only ever records "I retried this call" on the **caller's** outbound cluster — the callee's sidecar has no idea a retry even happened; it just sees N separate inbound requests. So "incoming retries at `paymentservice`" isn't something you scrape from `paymentservice`'s pod — it's `Σ (a)` over every caller whose target is `paymentservice`. Practically: `checkoutservice`'s outbound retry counter to `paymentservice`, `frontend`'s outbound retry counter to `paymentservice` (if any), etc., all merged with `target_service = paymentservice`. Same data, just a groupby/relabel of (a) instead of a new scrape.

---

## What "everyone scrapes everyone" requires

Today's `CALLER_TARGET_MAP` only lists 2 callers. To get (a)–(e) for **all 11 services** you need the full call graph, both directions:

| Caller | Targets it calls |
|---|---|
| `frontend` | cartservice, productcatalogservice, currencyservice, recommendationservice, shippingservice, checkoutservice, adservice |
| `checkoutservice` | cartservice, productcatalogservice, currencyservice, shippingservice, paymentservice, emailservice |
| `recommendationservice` | productcatalogservice |
| `cartservice` | redis-cart (TCP, not HTTP — no `upstream_rq_*`; use TCP counters or just CPU/mem for this edge) |
| everyone else (payment, currency, catalog, shipping, email, ad, recommendation-as-callee) | leaf — no outbound HTTP calls |

Practically: scrape **every** pod's sidecar (not just frontend/checkout), and stop hardcoding a small target list — parse *every* `cluster.outbound|...` line that matches the stats regex, whatever the target is. That also future-proofs it if the call graph changes.

---

## Design: one unified per-service collector

Extend (or replace) `envoy_retry_collector.py` with a wider poller that, each cycle, for **every** service pod:

1. `kubectl exec ... istio-proxy -- curl localhost:15000/stats`
2. Parse **outbound** lines → per-target: `upstream_rq_total`, `upstream_rq_2xx`, `upstream_rq_4xx`, `upstream_rq_5xx`, `upstream_rq_retry`
3. Parse **inbound listener** lines → per-service: `downstream_rq_total`, `downstream_rq_2xx`, `downstream_rq_4xx`, `downstream_rq_5xx`
4. Stamp everything with the same `timestamp` for that poll cycle.

One CSV, one row per `(timestamp, service)`, wide columns:

```
timestamp, service,
in_total, in_2xx, in_4xx, in_5xx,
out_total, out_2xx, out_4xx, out_5xx, out_retry
```

That single wide schema gives you all five things at once:

| Requested item | Column(s) |
|---|---|
| (a) outgoing retries | `out_retry` |
| (b) incoming retries | not a column here — computed later as `Σ out_retry` from all rows where `target=this service`, if you keep target-level detail (see below) |
| (c) outgoing goodput / requests | `out_total`, `out_2xx` (goodput = `Δout_2xx`), status split via `out_4xx`/`out_5xx` |
| (d) incoming goodput / requests | `in_total`, `in_2xx`, status split via `in_4xx`/`in_5xx` |
| (e) offered load | `in_total` (or `out_total` from the caller's side, if you want "load offered to X" measured at the sender) |

**Caveat on "who it talked to":** the wide schema above collapses all outbound targets into one row per service. If you need "(c) to whom" as a real column (not just a total), you need a **second, long-format** table that keeps `target_service` per row — exactly like the existing `envoy_retries_*.csv` shape, just widened to include `_2xx/_4xx/_5xx` alongside `_retry`. That's the one you'd also use to compute (b) by grouping on `target_service` instead of on `caller`. Keep both:

- `service_edges.csv`: `timestamp, caller, target, total, 2xx, 4xx, 5xx, retry` — for (a)/(b)/(c)/"to whom"
- `service_inbound.csv`: `timestamp, service, total, 2xx, 4xx, 5xx` — for (d)/(e)

**All counters are cumulative** (Envoy never resets mid-run), same as today's retry collector — every derived metric (goodput, retries, RPS) is a **difference between consecutive polls of the same row**, not the raw value.

**Same timestamp discipline as requested:** stamp every row in a poll cycle with the same ISO timestamp string, so joining `service_edges.csv` and `service_inbound.csv` (and `resource_usage.csv`, which already does 5s polls) on `timestamp` gives the full-system snapshot at second *t* — a real-time flow reconstruction. This is the same clock-alignment caveat already documented in [METRICS-GATHERED.md](METRICS-GATHERED.md) (Envoy/CPU collectors use their own first-poll t0, not Locust's).

**Prerequisite:** today only `frontend`/`checkoutservice` get the `sidecar.istio.io/statsInclusionRegexps` annotation that unhides `upstream_rq_*`. This design needs to (a) patch **every** Deployment, and (b) broaden the regex to also include `downstream_rq_*` (inbound/listener stats), which the current regex (`cluster\.outbound.*upstream_rq.*`) does not capture at all.

---

## Capacity — do we know/control it?

**Yes, but only as a CPU ceiling — not as a request-rate or concurrency ceiling.**

What we control and can read right now:

| Knob | Where | Value |
|---|---|---|
| CPU limit + request | `kubectl get deployment <svc> -o jsonpath='{.spec.template.spec.containers[0].resources}'` | Boutique defaults everywhere except S3/S4's bottleneck target; `100m` on whichever service `scale_constraints.cpu_limit` patches (`checkoutservice`, `productcatalogservice`, or `paymentservice`, per scenario) |
| Replica count | Same `kubectl get deployment` | Fixed at **1** everywhere (`instance_scaling.py`), all scenarios |

`run_scenario.py`'s `apply_constraints()` already reads and stores the **original** resources blob before patching (`original_resources` in the restore record) — so the "before" capacity value already passes through the runner, it's just not written into the results folder today. Recording it (once per run, since it's static for the run's duration — patched before load starts, restored after) into `run_manifest.json` or a small `service_capacity.json` would be a small, safe addition to close this gap: one row per service, `cpu_limit_millicores`, `cpu_request_millicores`, `replica_count`.

What we do **not** control or know:

- **No per-service request-rate or concurrency cap.** Istio/Envoy's circuit breaker (`DestinationRule.trafficPolicy.connectionPool`) is not configured anywhere in this stack — default is effectively unlimited pending requests/connections. There is no "max RPS `checkoutservice` can handle" number anywhere in the system; it's whatever CPU-bound throughput falls out of the `100m`/default CPU limit under that service's actual code path cost.
- **`overload_detection.py`'s hardcoded CPU quotas** (`cpu_quota = 200`, plus a per-service dict like `cartservice: 1000`, `productcatalogservice: 500`) are TopFull's own *assumed* quotas for its RL state — not something we set on the cluster, and not necessarily matching the real K8s `resources.limits.cpu` on our deployments. Treat that as TopFull's internal belief about capacity, not ground truth; the ground truth is the `kubectl get deployment` resources blob above.

So: "capacity" in this project **only exists as a CPU ceiling** (and trivially, replica=1). A truer notion of capacity (max sustainable RPS per service) would have to be measured empirically — e.g. a per-service saturation test — not read off any config; nothing currently does that.

---

## Status

**Implemented (2026-09-08).** `experiments/envoy_retry_collector.py` now scrapes
all 11 Boutique pods every poll (outbound `upstream_rq_*` **and** inbound
`downstream_rq_*`), writing `service_edges.csv` (`timestamp, caller, target,
total, 2xx, 4xx, 5xx, retry`) and `service_inbound.csv` (`timestamp, service,
total, 2xx, 4xx, 5xx`) into the run's `record_path`. `run_scenario.py` patches
the widened `sidecar.istio.io/statsInclusionRegexps` annotation
(`(cluster\.outbound.*upstream_rq.*)|(http\.inbound.*downstream_rq.*)`) onto
all 11 Deployments before every run (idempotent, not restored — see
`experiments/run_scenario.py::ensure_envoy_stats_enabled`), and snapshots each
service's original CPU limit/request/replica count into
`service_capacity.json` before any `scale_constraints` are applied
(`experiments/run_scenario.py::capture_service_capacity`).

**No backfill.** As before, this does not apply to any existing run —
`campaign_48/` and `august_38/` still have only the old
`envoy_retries_{frontend,checkoutservice}.csv` shape (2 callers, outbound
retries only, no inbound, no capacity snapshot). A **new run** is required to
get `service_edges.csv` / `service_inbound.csv` / `service_capacity.json`.

**Follow-up (not done here):** `experiments/mentor_charts.py` /
`mentor_charts_data.py` still only read the legacy
`envoy_retries_{caller}.csv` shape for chart generation. Wiring them to also
read `service_edges.csv` / `service_inbound.csv` for future campaigns is a
separate task.
