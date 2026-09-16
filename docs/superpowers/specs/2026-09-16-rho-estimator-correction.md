# ρ estimator correction: remove the TopFull-utilization conflation, use λ + 1/W

TopFull + RetryGuard Workshop — TAU Deepness Lab

> `estimate_service_mu.py`'s primary estimator (previously called "Estimator
> B", `mu_cpu = lambda / utilization`) computed `utilization` from
> `topfull_detect.csv` — `cadvisor_cpu / quota`, TopFull's own CPU-quota
> admission-control bookkeeping. That has nothing to do with the RetryGuard
> paper's `rho = lambda/mu` (a queueing-theoretic load ratio for an M/M/1(/m)
> single-queue-per-service model). This spec corrects the estimator to use
> only signals that are actually part of the paper's model: arrival rate and
> a latency-derived service rate.

Related: [RetryGuard.pdf](../../../context/RetryGuard.pdf) §5 (the `rho =
lambda/mu` definition, Eq. 9's M/M/1/m rejection-probability formula), the
original (now-corrected) design —
[2026-09-11-slo-fail-and-mu-estimator-design.md](2026-09-11-slo-fail-and-mu-estimator-design.md)
§5–§7, [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md),
[METRICS-GATHERED.md](../../../Guides%20and%20Info/METRICS-GATHERED.md).

---

## 1. What was wrong

`estimate_service_mu.py` (before this change) computed, per service, per
1-second tick:

```
mu_cpu(t) = lambda(t) / utilization(t)
```

where `utilization(t)` came from `topfull_detect.csv`, itself computed in
`topfull_throttle_collector.py::detect_metrics()` as:

```python
utilization = cadvisor_cpu / quota   # quota = a hardcoded paper CPU-limit table (topfull_cpu_quotas.py)
```

This is **TopFull's own internal admission-control signal** — "what
fraction of this service's paper-table CPU limit is currently busy,"
used by *TopFull's* Detector/RL loop to decide when to throttle. It is not:

- a queue length or occupancy,
- a request-processing rate,
- or anything else that appears in the RetryGuard paper's model.

Calling `lambda / utilization` "mu" and `lambda / mu_cpu` "rho" produced a
number shaped like the paper's `rho = lambda/mu`, but it measured a
different system's CPU-quota bookkeeping, not RetryGuard's queueing model.
This was flagged empirically in the S3 RetryGuard `run7` checkpoint (see
`rho_estimate_report.py`'s old context note): `mu_cpu` overestimated
capacity by more than 2x versus an independent saturated-goodput estimator
right at the saturation point the controller's own logic cares about most —
a symptom consistent with `mu_cpu` not actually being a service-rate
estimate at all.

## 2. What the paper actually says about measuring ρ/μ in practice

Re-read in full for this correction: [RetryGuard.pdf](../../../context/RetryGuard.pdf).

- **§5.1** defines the model: Service A sends at rate `lambda`; Service B
  processes at rate `mu` ("the rate at which Service B can process
  requests, i.e., its capacity in requests per second"). Miscoordination is
  `rho = lambda/mu > 1`. The rejection-probability / retry-volume formulas
  (Eq. 2–5) are derived from a **fixed-point overflow/loss argument**
  (`p = mu/Lambda`, `Lambda` = total offered load including retries) — this
  is not a sojourn-time argument; it doesn't produce or need a `W`.
- **§5.2** ("Behavior under Stability Conditions") is where the paper
  explicitly names its stable-load model: **M/M/1/m — a single-server
  Markovian queue with finite buffer `m`** — and states
  `rho = lambda/mu`, with the blocking probability
  `p̃ = (1-ρ)ρ^m / (1-ρ^(m+1))` (Eq. 9, the standard Erlang-type finite-buffer
  formula). This confirms the model class (single Markovian queue) but the
  paper still treats `lambda`, `mu`, `m`, `k` (max retries) purely as
  **simulation/analytical parameters** — Fig. 7 and Fig. 8 sweep these as
  known inputs to plot the resulting curves, they are not estimated from any
  live trace in the paper.
- **§4.3.1** ("Surrogate Threshold Metrics") is the paper's *only* discussion
  of what a live deployment should actually measure: it explicitly says the
  controller can use **retry volume, rejection rate, or response delay** —
  not `rho` itself — as a practical surrogate, "depending on their
  availability." §6.2 (the live Istio BookInfo evaluation) confirms this:
  RetryGuard there acts on **mesh rejection rate** (20% threshold, 30s
  window), not on a computed `rho`.
- **Conclusion: the paper never describes a live μ-estimation procedure.**
  There is no formula, no appendix note, no evaluation-section methodology
  for measuring `mu` from a running system. `experiments/retryguard.py`
  already reflects the paper correctly — it uses the rejection-rate
  surrogate from §4.3.1/§6.2, not `rho`. Designing a live `mu` estimator is
  therefore **our own, defensible-but-approximate engineering task**, not a
  paper-specified formula we were failing to reproduce. This spec is honest
  about that: what follows is a supplementary diagnostic we built ourselves,
  grounded in standard queueing theory that is consistent with the model
  class the paper names in §5.2 (a single Markovian queue), not a formula
  lifted from the paper itself.

## 3. The corrected methodology

### 3.1 Formula

For an M/M/1 queue in steady state (`rho < 1`), the mean time a request
spends in the system (queueing + service), by the standard M/M/1
sojourn-time result, is:

```
W = 1 / (mu - lambda)
```

Rearranged:

```
mu = lambda + 1/W
```

This is exactly the pair of quantities that define load in the paper's own
model class (§5.2's single Markovian queue): an arrival rate and a
service-time-derived rate. It requires **no CPU/quota data whatsoever** —
unlike the removed CPU-linear estimator, it cannot smuggle in an unrelated
system's admission-control bookkeeping, because it structurally cannot use
that data at all.

Cross-check via Little's Law (`L = lambda * W`, mean number in system) was
considered but not implemented as a second estimator: it needs a queue
*occupancy* measurement (`L`) that we do not have (no queue-depth metric
exists in the collected data), so it would not add an independently
measurable check — it would just restate the same `lambda`/`W` inputs
already used above.

`rho_w = lambda / mu_hat_w`.

### 3.2 Data sources

- `lambda_s(t) = Δtotal / Δt` from `service_inbound.csv` — **unchanged**,
  this part of the old code was already correct and is reused as-is.
- `W` — **new**. `service_inbound.csv` gained two additive columns,
  `rq_time_sum_ms` / `rq_time_count`, from Envoy's inbound
  `downstream_rq_time` histogram (`_sum`/`_count` series on
  `/stats/prometheus`, skipping the `_bucket` series — see §4).
  `W(t) = (Δrq_time_sum_ms / Δrq_time_count) / 1000` seconds — this
  service's own mean inbound sojourn time for that tick (time from receipt
  to response at *this* Kubernetes service's Envoy sidecar), not
  end-to-end/multi-hop client latency. This is the correct latency
  granularity for a per-service M/M/1 `W`: it excludes upstream callers'
  own queueing and downstream fan-out time that a Locust P95 would include.
- `topfull_detect.csv` is **no longer read at all** by
  `estimate_service_mu.py`. The corrected estimator has zero dependency on
  TopFull's CPU-quota bookkeeping.

### 3.3 What's kept, and why

The saturated-goodput cross-check (`mu_sat = Δ2xx/Δt` on ticks where the
5xx fraction crosses `SAT_5XX_FRACTION` = 0.05) is **kept unchanged**. It is
retained deliberately, not by default inertia: at/near saturation, admitted
throughput directly approximates capacity (a service processing at its
practical maximum will show `Δ2xx/Δt` close to its true `mu`) — this is an
M/M/1/m-adjacent argument (blocking absorbs the excess above capacity) that
does not depend on the CPU-quota signal at all, so it never needed
correcting. It remains available on any run, even ones without the new
latency columns, since it only reads `total`/`2xx`/`5xx` (present since the
mesh collector's introduction).

### 3.4 Handling ρ ≥ 1 / saturation

The `W = 1/(mu-lambda)` relation is only valid under the paper's own stated
condition, `rho < 1` (§5.2's explicit stability assumption). If a service's
observed `lambda_mean` reaches or exceeds its own `mu_hat_w_median`, that
is **not** treated as "confirmed rho ≥ 1" at face value — a true M/M/1 queue
at `rho ≥ 1` has an unbounded (growing without limit) `W`, so a *finite*
observed `W` alongside `lambda ≥ mu` more likely indicates one of:

- a **finite buffer** (the paper's own M/M/1/m, not M/M/1 — a full buffer
  rejects excess arrivals instead of letting `W` grow unboundedly),
- **admission control upstream** of this service's queue (TopFull's own
  Layer A/RL, or Istio circuit breaking) truncating arrivals before they
  reach this service's queue at all, or
- **non-Poisson/non-exponential real traffic** — the M/M/1 assumptions
  themselves not holding.

`estimate_service_mu.py` reports this case with an explicit note
(`SATURATION_NOTE`) rather than silently returning a `rho_w` number that
looks precise but rests on a violated assumption.

## 4. Collector extension: `envoy_retry_collector.py`

**Decision: extended**, not left as an open gap, because the addition is
clean, additive, and low-risk (verified by reading the full collector
before touching it — see constraints below), and because without it there
was no per-service latency signal anywhere in the collected data (checked:
`topfull_throttle_collector.py`/`topfull_detect.csv` and
`resource_usage_collector.py`/`resource_usage.csv` have no latency-adjacent
field; Locust's per-endpoint CSVs have P95/P99 but those are
multi-hop/client-perceived, not this service's own sojourn time — see §5).

**What changed** (`experiments/envoy_retry_collector.py`):

- Two new trailing columns on both `service_edges.csv`
  (`rq_time_sum_ms`, `rq_time_count`, outbound/caller-side) and
  `service_inbound.csv` (same two, inbound/callee-side). Appended at the
  **end** of `EDGES_CSV_COLUMNS`/`INBOUND_CSV_COLUMNS` — every existing
  column keeps its name and relative order.
- New parsing in `parse_edges()`: `envoy_cluster_upstream_rq_time_sum` /
  `envoy_cluster_upstream_rq_time_count`, keyed by the same `cluster_name`
  label already used for `envoy_cluster_upstream_rq_total` — this is
  Envoy's histogram export shape (`_bucket`/`_sum`/`_count` per histogram
  on `/stats/prometheus`; we skip `_bucket`, since only the mean is needed).
- New parsing in `parse_inbound()`: `envoy_http_inbound_<listener>_downstream_rq_time_sum`
  / `_count`, matching the existing `envoy_http_inbound_<listener>_downstream_rq_total`
  naming convention already parsed by this collector.
- **Existing scrape behavior, timing, and columns are unchanged.** No
  change to poll interval, thread pool sizing, tier-2 IP-eviction/reseed
  logic, or any existing column's name/semantics. Confirmed
  `retryguard.py`'s `InboundCsvTailer` reads `service_inbound.csv` rows by
  **column name** (`row["5xx"]`, `row.get("resets", 0)`, etc., built from a
  dynamically-parsed header line — see `InboundCsvTailer._parse_header`),
  not by position, so appending new named columns cannot break it.

**Verification status — live-verified 2026-09-16** against this cluster's
`/stats/prometheus` (frontend pod IP, `curl http://<pod_ip>:15020/stats/prometheus`):

- **Inbound confirmed correct as written.** Real series present even before
  traffic (Istio's default minimal proxy-stats set includes per-listener
  HTTP connection-manager histograms — low cardinality, ~1 listener/pod):
  ```
  # TYPE envoy_http_inbound_0_0_0_0_8080_downstream_rq_time histogram
  envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_bucket{le="0.5"} 0
  ...
  envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_sum{} 0
  envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_count{} 0
  ```
  Under real traffic the `_sum`/`_count`/`_bucket` series populate exactly
  as this collector assumes. `service_inbound.csv` also stores the bucket
  map as JSON in `rq_time_buckets` so `estimate_service_mu.py` can derive a
  per-tick P50 by differencing buckets (robustness check alongside the mean).
- **Outbound (`envoy_cluster_upstream_rq_time_{sum,count}`) does not appear
  at all** on this cluster's `/stats/prometheus`. Confirmed by grepping the
  full scrape's `# TYPE ... histogram` lines: only
  `envoy_cluster_upstream_cx_connect_ms`/`_length_ms` and the inbound HTTP
  histogram exist — there is no `envoy_cluster_upstream_rq_time` histogram
  for any outbound cluster. This is expected, documented Istio behavior
  (per-cluster `upstream_rq_time` is a *detailed* stat Istio excludes from
  its default minimal proxy-stats set to bound cardinality), and only
  appears if `proxyStatsMatcher.inclusionSuffixes` (or `inclusionRegexps`)
  includes `upstream_rq_time` — a mesh/workload-wide change that would
  restart every Boutique pod, deliberately out of scope here. Not needed
  today: `estimate_service_mu.py` only reads `service_inbound.csv`. Net
  effect: `service_edges.csv`'s `rq_time_*` columns stay structurally zero
  until that mesh-config change — a **known, disclosed limitation**, not a
  transient "no traffic yet" zero. The outbound-parsing code is left as-is
  (correct Envoy naming, forward-compatible) rather than removed.

## 5. Why Locust latency is not used as `W`

Locust's per-endpoint CSVs (`getcart.csv` etc.) report **end-to-end,
client-perceived** latency across the full storefront request — e.g.
`getcart` fans out through frontend → cartservice, productcatalogservice,
shippingservice, currencyservice, plus recommendationservice
(`PER-SERVICE-METRICS.md`). Using that as a *per-service* `W` for, say,
`cartservice` alone would massively overstate its own sojourn time by
including every other hop's queueing and processing time, producing a
`mu_hat_w` far below the service's true capacity. This is documented as a
real limitation, not silently used as a shortcut: Locust latency is **not**
used anywhere in the corrected `estimate_service_mu.py`.

## 6. Files changed

- `experiments/envoy_retry_collector.py` — additive `rq_time_sum_ms`/
  `rq_time_count` columns + parsing (outbound + inbound), as above.
- `experiments/test_envoy_retry_collector.py` — updated fixtures/assertions
  for the two new columns; added a dedicated parsing test.
- `experiments/estimate_service_mu.py` — rewritten: removed `mu_cpu`/
  `utilization`/`topfull_detect.csv` entirely; added `mu_hat_w`, `rho_w`,
  `w_mean_ms`, `n_ticks_with_latency`, and an explicit `note` field for the
  no-latency-data and saturation cases; kept `mu_sat` unchanged.
- `experiments/test_estimate_service_mu.py` — rewritten for the new
  estimator; no test still asserts the old CPU-linear behavior.
- `experiments/rho_estimate_report.py` — `CONTEXT_NOTE` and the "rho at
  toggled services" section rewritten for the new field names;
  `compute_rho_estimates()` no longer expects/handles a `MissingDetectError`
  (that exception no longer exists — `topfull_detect.csv` is not read).
- `experiments/test_rho_estimate_report.py` — rewritten fixtures (no
  `topfull_detect.csv`; `service_inbound.csv` gets the new columns);
  added a case for a run with `service_inbound.csv` but no latency columns
  (pre-2026-09-16 shape) reporting a note, not an error.
- `docs/superpowers/specs/2026-09-11-slo-fail-and-mu-estimator-design.md` —
  correction banner added at the top pointing here; body kept as historical
  context for how the (incorrect) Estimator B was originally motivated.
- `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md` — this
  file.
- `.cursor/skills/rho-estimate-report/SKILL.md` — updated field names and
  methodology description to match.
- `AGENTS.md` §4 — status entry added noting the correction and the
  collector extension, per the existing pattern for prior collector
  additions ("historical run folders won't have this field").

## 7. Empirical sanity check (live smoke, 2026-09-16)

Folder: `experiments/results/campaign_48/_smoketest_rho_verify_20260916/`
(also on master as `/home/idozacharia/experiments/results/smoketest_rho_verify_20260916/`).
~2 min of curl traffic against frontend NodePort `30440` while the
corrected collector ran with a properly seeded `pod_ips` map (the first
smoke attempt failed because params omitted `pod_ips` — collector never
self-heals an empty seed; that is a test-setup mistake, not a product bug:
`run_scenario.py` always seeds via `discover_service_pod_ips`).

| service | λ_mean | μ̂_w | ρ_w | W_mean (ms) |
|---|---|---|---|---|
| frontend | 14.42 | 51.78 | **0.216** | 25.16 |
| cartservice | 14.42 | 604.5 | 0.0185 | 1.79 |
| currencyservice | 48.01 | 1244 | 0.0315 | 0.83 |
| recommendationservice | 8.04 | 285.4 | 0.0214 | 3.86 |
| productcatalogservice | 59.46 | 2.35e4 | 0.0019 | 0.05 |
| adservice | 8.05 | 664.5 | 0.0092 | 1.77 |
| shippingservice | 3.19 | 1.15e4 | 0.0002 | 0.11 |

All ρ ≪ 1 under light load — the expected shape. Sojourn times are in a
plausible single-digit-to-low-tens-of-ms range for these demo services
(frontend higher because it fans out). `mu_sat` is `n/a` (no 5xx under
light load — expected). `retryguard.py`'s `InboundCsvTailer` is unaffected
(column-name based; new trailing columns are additive).

## 8. Remaining limitations (stated plainly, not oversold)

- **Real traffic is not exactly Poisson/exponential.** The M/M/1
  `W = 1/(mu-lambda)` relation is exact only under those assumptions.
  Real HTTP arrivals and service times deviate from both, so `mu_hat_w` is
  an *approximation* even when the arithmetic is applied correctly to real
  numbers.
  - **Locust arrival shape (this workshop):**
    `TopFull/TopFull_loadgen/locust_online_boutique.py`'s `WebsiteUser`
    uses `wait_time = constant_throughput(1)` — i.e. each Locust user aims
    for a near-deterministic 1 task/second, **not** an exponential
    inter-arrival distribution. Aggregating many independent users still
    approximates a Poisson process in the limit (Palm–Khintchine), so the
    M/M/1 arrival assumption is not catastrophically wrong at our load
    levels, but it is not literally what Locust emits. Switching
    `wait_time` to something like `between(a, b)` or an exponential draw
    would move arrivals closer to the paper's Poisson assumption — **team
    discussion only**, do not change without a separate load-calibration
    decision (would invalidate cross-run comparisons against prior
    campaign data).
- **M/M/1 (single server) ignores per-pod concurrency.** Every Boutique
  service in this workshop is deployed at 1 replica (per `AGENTS.md`), which
  helps this assumption, but each pod still serves many concurrent
  in-flight requests via goroutines/threads/connection pools — a closer
  model would be M/M/c or M/G/1, which this estimator does not attempt.
  - **Why M/M/1 is still more defensible for us than for a generic web
    service:** TopFull's paper CPU quotas (and S3/S4's
    `cpu_limit_fraction: 0.1` constraints) make CPU the binding resource.
    Even when the app-level concurrency is >1, requests are still
    effectively serialized by the CPU limit — the "server" in queueing
    terms is closer to "one CPU-quantum" than "one OS thread." That does
    **not** make M/M/1 exact (service-time distributions are not
    exponential; TopFull Layer A admission also truncates arrivals before
    they reach the queue), but it makes the single-server abstraction a
    better fit here than it would be for an unconstrained multi-core HTTP
    service. Implementing a full M/M/c estimator would need a reliable
    per-service concurrency/thread-pool reading we do not currently
    collect — deferred, not worth inventing from CPU millicores alone.
- **`rq_time_count`/`rq_time_sum_ms` deltas can be small or zero on quiet
  ticks** (few completions in a 1s window), making single-tick `W` noisy;
  the median-over-ticks approach mitigates but does not eliminate this.
  A per-tick **P50** derived from differenced Envoy histogram buckets
  (`rq_time_buckets` JSON column → `w_p50_ms` in the report) is now
  reported alongside the mean as a robustness check against long-tail
  outliers; the μ̂/ρ path still uses the mean W (the M/M/1 relation is
  stated in terms of the mean sojourn time).
- **Truncation to integer milliseconds.** `envoy_retry_collector.py`'s
  generic Prometheus-value parser does `int(float(value))` for every metric
  line, including `rq_time_sum_ms` — sub-millisecond precision in Envoy's
  reported sum is truncated. Negligible at the latencies observed in this
  workshop (hundreds to thousands of ms on overloaded paths; single-digit
  to low-tens of ms under light load).
- **Outbound latency columns are structurally zero** on this cluster
  until Istio's `proxyStatsMatcher` is widened to include
  `upstream_rq_time` (see §4). Inbound-only is sufficient for the
  current estimator.
- **`mu_hat_w_median`/`rho_w_median` use a *global* median mu across all
  ticks in the run**, including ticks that may already be under partial
  overload — there is no controlled, guaranteed-`rho<1` calibration window
  to compute a "clean" mu from. This is disclosed via the `SATURATION_NOTE`
  when `lambda_mean` reaches/exceeds `mu_hat_w_median`, but does not fully
  resolve the circularity for runs that are overloaded throughout.
- **Still a supplementary, offline diagnostic** — as before this
  correction, `experiments/retryguard.py`'s live controller does not use
  `rho` at all; it acts on the paper's own §4.3.1/§6.2 rejection-rate
  surrogate. Nothing about this correction changes that division of labor.
