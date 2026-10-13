# Per-service mesh collector — design

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Design for gathering, **per Kubernetes service, with a shared timestamp**: outgoing retries, incoming retries, outgoing requests + status ("outgoing goodput"), incoming requests + status ("incoming goodput"), and offered load — plus what we know about each service's "capacity." Builds on [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md) (feasibility) and extends `experiments/envoy_retry_collector.py`. **Implemented.** The live scrape and the real CSV columns are in [Status](#status). `campaign_48/` and `august_38/` still have only the legacy two-caller files. Every hold under `experiments/results/final results/` has `service_edges.csv`, `service_inbound.csv`, and `service_capacity.json`.

Those five metrics map almost 1:1 onto Envoy stats, but two of them (incoming retries, incoming requests) need a different vantage point than the current collector uses.

---

## Where each metric actually lives in Envoy

The "Already collected?" column below is the gap as of the design (two callers, outbound retries only). The shipped collector covers all 11 services in both directions. See [Status](#status).

Envoy on **each** pod's sidecar exposes two families of counters: **outbound** (calls this pod *makes*) and **inbound/listener** (calls this pod *receives*).

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

Before the rewrite, `CALLER_TARGET_MAP` listed 2 callers. The shipped collector parses every outbound cluster it sees, so this table is the call graph, not a hardcoded target list:

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

The paragraphs in this section are the original sketch (one wide CSV, `kubectl exec`, `curl localhost:15000/stats`). What shipped is the two-CSV network scrape in [Status](#status): `GET http://<pod_ip>:15020/stats/prometheus`, with `resets`, `rq_time_*`, `rq_time_buckets`, and `grpc_*` on inbound. Do not implement the exec steps below.

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
| CPU limit + request | `kubectl get deployment <svc> -o jsonpath='{.spec.template.spec.containers[0].resources}'` | Paper-C1 ([ADR 0009](../docs/adr/0009-paper-c1-default-cpu-table.md)) on unconstrained services. A constrained service uses an absolute `cpu_limit_millicores` ([ADR 0006](../docs/adr/0006-absolute-bottleneck-cap-not-fraction.md)): S3 checkout **200m**, S4A-constrained catalog **50m**, S4B email **50m**. S4A unconstrained has no extra cap. |
| Replica count | Same `kubectl get deployment`, or the HPA | Frontend is HPA min 1 / max 4, or pinned at 4 for a hold. The other services stay at 1 unless a hold pins them. |

`run_scenario.py` reconciles every Boutique deployment to the Paper-C1 table before constraints, applies the absolute millicore cap on the bottleneck, snapshots `service_capacity.json` **before** constraints, writes `topfull_run_quotas.json` for Detector, and restores paper limits at teardown. Manifest fields `paper_cpu_quotas` / `effective_cpu_quotas` record the maps used for the run. The snapshot is the pre-constraint table, so an S3 file still shows checkout at the Paper-C1 limit, not 200m.

What we do **not** control or know:

- **No per-service request-rate or concurrency cap.** Istio/Envoy's circuit breaker (`DestinationRule.trafficPolicy.connectionPool`) is not configured anywhere in this stack — default is effectively unlimited pending requests/connections. There is no "max RPS `checkoutservice` can handle" number anywhere in the system; it's whatever CPU-bound throughput falls out of the effective CPU limit under that service's actual code path cost.
- **Detector quotas vs K8s limits.** Before the quota↔K8s sync work, `overload_detection.py`'s hardcoded map could disagree with live `resources.limits.cpu`. **After a run with the sync path**, K8s limits and Detector quotas are driven from the same Paper-C1 map plus any absolute `cpu_limit_millicores` for that run — they match by construction. Locust user counts are still not auto-adjusted when quotas change.

So: "capacity" in this project **only exists as a CPU ceiling** (and the live replica count). A truer notion of capacity (max sustainable RPS per service) is the frozen μ in [experiments/capacity/README.md](../experiments/capacity/README.md). `estimate_service_mu.py` is retired. `analysis_score.py` still reports inbound arrival rate and sojourn from the mesh CSVs.

---

## Status

**Implemented.** `experiments/envoy_retry_collector.py` runs on master
(`transport: network_prometheus`). Each poll GETs
`http://<pod_ip>:15020/stats/prometheus` for all 11 Boutique pods. It writes:

- `service_edges.csv`: `timestamp, caller, target, total, 2xx, 4xx, 5xx, retry, rq_time_sum_ms, rq_time_count`. Outbound `2xx`/`4xx`/`5xx` are live on this transport. Outbound `rq_time_*` stays 0.
- `service_inbound.csv`: `timestamp, service, total, 2xx, 4xx, 5xx, resets, rq_time_sum_ms, rq_time_count, rq_time_buckets, grpc_2, grpc_4, grpc_13, grpc_14`.

`run_scenario.py` patches the widened `sidecar.istio.io/statsInclusionRegexps`
annotation (`(cluster\.outbound.*upstream_rq.*)|(http\.inbound.*downstream_rq.*)`)
onto all 11 Deployments before every run (idempotent, not restored — see
`experiments/run_scenario.py::ensure_envoy_stats_enabled`), and snapshots each
service's original CPU limit/request/replica count into
`service_capacity.json` **before** any `scale_constraints` are applied
(`experiments/run_scenario.py::capture_service_capacity`).

**No backfill of the closed sets.** `campaign_48/` and `august_38/` still have
only `envoy_retries_{frontend,checkoutservice}.csv` (2 callers, outbound
retries only, no inbound, no capacity snapshot). Every hold under
`experiments/results/final results/` has the three mesh files. Derived
metrics from those files: [METRICS-GATHERED.md](METRICS-GATHERED.md#derived-metrics-analysis_scorepy).

**Outbound class columns:** on `transport: network_prometheus`,
`service_edges.csv` `2xx` / `4xx` / `5xx` are live. The 2026-09-08 admin-port
gap (class columns always 0) does not apply to new runs.
`campaign_48/` / `august_38/` still have whatever they had.

**Follow-up (not done here):** `experiments/mentor_charts.py` /
`mentor_charts_data.py` still only read the legacy
`envoy_retries_{caller}.csv` shape for chart generation. Wiring them to also
read `service_edges.csv` / `service_inbound.csv` for future campaigns is a
separate task.

**Network scrape (2026-09-13).** `experiments/envoy_retry_collector.py` runs
on `topfull-master` only (`transport: network_prometheus`). Each poll a
thread pool GETs `http://<pod_ip>:15020/stats/prometheus`. The orchestrator
seeds `service → pod_ip` once via kubectl; a fetch failure rate-limits a
per-service re-seed (Tier-2). CSVs land in `record_path` during the run, so
RetryGuard's `measure_value()` can read `service_inbound.csv` mid-run. Do not
treat this as a campaign-data change — `campaign_48/` / `august_38/` still
have whatever they had.
