# RetryGuard `measure_value()` — mesh inbound rejection rate

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Switch RetryGuard's Algorithm 1 input from Locust `Fail / RPS` (mapped through `ENDPOINT_SERVICE_MAP`) to each service's **Istio/Envoy inbound rejection rate**, read from the already-implemented mesh collector (`service_inbound.csv`). This is the paper's Istio signal (RetryGuard.pdf Sec. 6.2): the service mesh provides each microservice's rejection/error rate; if it stays above Threshold for Interval consecutive samples, disable retries on that service. **Spec only — not implemented yet.**

Related: [RETRYGUARD-IMPLEMENTATION.md](../../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md), [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md), [PER-SERVICE-METRICS.md](../../../Guides%20and%20Info/PER-SERVICE-METRICS.md). Algorithm 1 sampling/Interval fidelity: [2026-09-10-retryguard-paper-fidelity.md](../plans/2026-09-10-retryguard-paper-fidelity.md).

---

## 1. Purpose and scope

`measure_value()` in Algorithm 1 is unspecified as a formula. In the paper's Istio BookInfo experiment (Sec. 6.2) it is the **mesh-provided per-service error/rejection rate**, compared to Threshold 20% for Interval 30 s.

Today `experiments/retryguard.py` fills that placeholder with Locust `Fail / RPS` on storefront APIs, then infers three Kubernetes services via `ENDPOINT_SERVICE_MAP`. That is a Phase 5 convenience (Locust CSVs already existed). It is **not** the paper's Istio signal: Locust answers "did this shopper API fail?", not "did this pod reject inbound work?"

The mesh collector (2026-09-08) now writes that per-service series. This spec rewires the **controller input only**.

**In scope**

- Replace Locust CSV reading in `retryguard.py` with inbound `Δ5xx / Δtotal` from `service_inbound.csv`.
- Run one Algorithm 1 state machine per HTTP Boutique **backend** that has a VirtualService (see §3). **No `frontend`.** **No `redis-cart`.**
- Drop `ENDPOINT_SERVICE_MAP` and max-across-Locust-endpoints aggregation.
- Startup wait, SKIP rules, unit tests, and the live docs that still describe Locust as the controller source.

**Out of scope**

- Changing Algorithm 1 itself (`sample_interval_seconds`, `interval_samples`, Threshold, consecutive counters, initial `ON`).
- RetryGuard scraping Envoy / `kubectl exec` (collector already writes the file).
- `service_edges.csv` as a rejection source (live outbound `2xx`/`4xx`/`5xx` are 0 — documented collector gap).
- Including `4xx` in the numerator.
- Dual-source / Locust fallback / `max(Locust, inbound)`.
- Rewiring `mentor_charts.py` to plot `service_inbound.csv` / `service_edges.csv`. Those files are already intended as **per-service outcomes / insights** (see [PER-SERVICE-METRICS.md](../../../Guides%20and%20Info/PER-SERVICE-METRICS.md)); charting them is a separate follow-up, not part of this controller-input change.
- Backfill of `campaign_48/` or `august_38/`. First **new** run after implementation is the first paper-shaped `measure_value()`.
- Creating new VirtualServices (they already exist for every HTTP service listed in §3).
- Patching `frontend`'s VirtualService (it stays at default `attempts: 3`).

---

## 2. Metric: `Failures ← measure_value()`

**File:** `{record_path}/service_inbound.csv`  
**Schema:** `timestamp, service, total, 2xx, 4xx, 5xx`  
**Semantics:** cumulative Envoy inbound listener counters (`http.inbound_*.downstream_rq_*`), one row per `(timestamp, service)` per collector poll. Scenario YAMLs already set `envoy_retry_collector.poll_interval_seconds: 1`.

**Formula** (one raw sample, no averaging — same as the 2026-09-10 Interval work):

```
Failures = Δ5xx / Δtotal     if Δtotal > 0
Failures = 0.0               if Δtotal == 0   # no inbound ≠ overload
```

where `Δ` is the difference between the **newest row for that service** and the **previously consumed row for that service**.

Do **not** use raw cumulative totals. Do **not** use `4xx`. Do **not** use Locust `Fail` / `RPS`. Do **not** use `service_edges.csv`.

Rationale:

- Sec. 6.2: mesh provides each service's rejection/error rate; Threshold in that experiment is 20%.
- Istio retry policy in this stack is `retryOn: "5xx,reset,connect-failure"`. Overload shows as 5xx/503. Mixing 4xx would count client errors as miscoordination.
- [PER-SERVICE-METRICS.md](../../../Guides%20and%20Info/PER-SERVICE-METRICS.md) already names inbound `5xx / total` (differenced) as the closest paper signal.

### 2.1 Do not double-count a poll

If RetryGuard wakes every 1 s and the collector has not appended a new row yet, the last two CSV rows are unchanged. Re-differencing them would apply the **same** sample twice and inflate `Consecutive_high` / `Consecutive_low`.

**Required:** keep, per service, the last consumed `(timestamp, total, 5xx)` in memory.

- New inbound row with a **newer `timestamp`** → compute `Δ`, update memory, feed Algorithm 1.
- No new timestamp (or file missing / unreadable) → **SKIP** that service this tick (counters unchanged). Same idea as today's "no CSV → skip".
- First row ever for a service → store it, **SKIP** (cannot difference yet).

`Δtotal == 0` on a *new* timestamp is a real sample of "no inbound this second" → `Failures = 0.0`, counters update (almost always toward re-enable / stay ON). That matches today's `RPS == 0 → 0.0`.

### 2.2 Stale or slow collector

Scraping 11 sidecars can take longer than 1 s. RetryGuard then sees a slightly late but complete poll. That is still one raw sample per new row — Algorithm 1 does not require the sample to be instantaneous. A dropped poll is a SKIP, not a fabricated zero (unless a new row actually has `Δtotal == 0`).

Inbound 5xx is hop-level. A caller timeout that never becomes a 5xx at the callee will not move this number. That is the paper's Istio signal, not a bug.

---

## 3. Which services get a controller

Paper Sec. 6.2 deploys RetryGuard **independently at each microservice**. We do that for every HTTP Boutique **callee** that already has a VirtualService in `experiments/virtual-services.yaml`, excluding ingress.

**Controlled (9):**

`adservice`, `cartservice`, `checkoutservice`, `currencyservice`, `emailservice`, `paymentservice`, `productcatalogservice`, `recommendationservice`, `shippingservice`

**Excluded:**

| Service | Why |
|---|---|
| `frontend` | Ingress hop, not a Boutique callee. Decision: do not include. Its VS stays at `attempts: 3`. |
| `redis-cart` | TCP. No HTTP inbound `downstream_rq_5xx`. No VS in `virtual-services.yaml`. |

This is the first design in which S4B can disable retries **on `paymentservice`** (the actual bottleneck). Today's Locust map never sees Payment as its own service.

Replace `ENDPOINT_SERVICE_MAP` with a constant `CONTROLLED_SERVICES` equal to the 9 names above. One `ServiceState` per listed service. `run()` iterates that list, not Locust endpoints.

If a service's VS is missing at patch time, keep today's `PATCH_FAIL` behavior: log, do **not** update `retries_state`.

---

## 4. Data flow (unchanged collector, new reader)

```
envoy_retry_collector.py  --1s-->  service_inbound.csv
                                      |
retryguard.py  read newest row per service, Δ vs in-memory previous
                                      |
                              Failures = Δ5xx / Δtotal
                                      |
                         apply_algorithm1(...)  [unchanged]
                                      |
                    patch VirtualService retries ON/OFF
```

RetryGuard does **not** call `kubectl exec` or curl Envoy. The collector remains the only scraper.

Startup: wait for `service_inbound.csv` to exist and contain at least one data row (same 60 s / 5 s poll budget as today's Locust wait). Per-service first-difference SKIP covers "file exists but this service has only one row."

`record_path` stays `global_config.json` → `record_path` (same directory the collector already writes into).

---

## 5. What does not change

| Piece | Stays |
|---|---|
| Algorithm 1 | Symmetric `interval_samples`, `sample_interval_seconds: 1`, Threshold 0.20, consecutive reset on the other side |
| Initial state | `ON` (workshop deviation: paper initializes `OFF`) |
| Patch mechanics | Omit `retries` block to disable; restore `attempts: 3` + `retryOn` to enable |
| Teardown | Runner still restores `attempts: 3` on Boutique VSes after a RetryGuard run |
| Storefront outcome charts (today) | Locust `total.csv` / per-API CSVs — goodput, P95, door-level rejection |
| Per-service outcomes / insights | `service_inbound.csv`, `service_edges.csv`, `resource_usage.csv`, `retryguard.log` — already collected for the report; this spec does not add or remove them |
| Scenario YAMLs (params) | `rejection_threshold`, `sample_interval_seconds`, `interval_samples` — no new RetryGuard keys required |
| Collector | `service_inbound.csv` schema and 1 s poll already match this spec |

`service_inbound.csv` is **both** things: RetryGuard's live `measure_value()` **and** a per-service outcome series we already gather to explain Locust. Locust stays the user-visible door. Mesh / CPU / toggle logs stay the “which service, and why” layer ([PER-SERVICE-METRICS.md](../../../Guides%20and%20Info/PER-SERVICE-METRICS.md) practical split). This spec only changes who **reads inbound for decisions**. It does not make mesh “controller-only.”

---

## 6. Tests

`experiments/test_retryguard.py` (kubernetes still stubbed):

- Latest two inbound rows for one service → `Δ5xx / Δtotal`.
- Ignores older rows; only the newest unused timestamp counts.
- `Δtotal == 0` → `0.0`.
- Same timestamp re-read → no second sample (SKIP / `None`).
- Missing file / missing service / single row → `None` (caller SKIPs).
- `4xx` must not enter the formula (fixture with large `4xx`, zero `5xx` → `0.0` if `Δ5xx == 0`).
- `apply_algorithm1` tests stay as they are (pure state machine).
- `REQUIRED_PARAMS` unchanged.
- Controlled-service list includes `paymentservice` and excludes `frontend` / `redis-cart`.

Do not require a live cluster or a real `service_inbound.csv` from `campaign_48/` (those runs do not have this file).

---

## 7. Docs to update when implementing

- [RETRYGUARD-IMPLEMENTATION.md](../../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md) — metric source, drop `ENDPOINT_SERVICE_MAP`, replace deviation #2 ("Locust, not Istio Prometheus") with inbound `Δ5xx/Δtotal`; list the 9 services; note frontend excluded.
- [AGENTS.md](../../../AGENTS.md) §4 — dated status bullet; this supersedes "RetryGuard reads Locust."
- [PER-SERVICE-METRICS.md](../../../Guides%20and%20Info/PER-SERVICE-METRICS.md) / [METRICS-GATHERED.md](../../../Guides%20and%20Info/METRICS-GATHERED.md) — any sentence that still says RetryGuard's per-service rejection is Locust `Fail/RPS`.
- [experiments/README.md](../../../experiments/README.md) / PHASE5 / SCENARIOS guides only where they describe RetryGuard's **decision** metric (Locust storefront results stay Locust).

Historical campaign READMEs and `campaign_48/` stay as-is (those runs used Locust).

---

## 8. Acceptance

Done when:

1. `retryguard.py` never opens Locust endpoint CSVs.
2. `measure_value()` for each §3 service is inbound `Δ5xx / Δtotal` with the no-double-count rule.
3. `frontend` and `redis-cart` are never in the state map and are never patched by RetryGuard.
4. `paymentservice` **is** in the state map (S4B can toggle the bottleneck).
5. Unit tests in §6 pass via `python -m unittest experiments.test_retryguard -v`.
6. Docs in §7 describe mesh inbound as RetryGuard's live `measure_value()`; Locust remains the storefront outcome; mesh/CPU stay per-service outcomes/insights.

Not required for this change: a new campaign, mentor-chart rewiring, or cluster smoke. Those follow after the code lands.
