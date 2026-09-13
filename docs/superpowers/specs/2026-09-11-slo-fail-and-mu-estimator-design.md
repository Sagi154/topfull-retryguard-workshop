# SLO-Fail vs Boutique overload, and a best-effort μ estimator

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Run11 looked like “Locust Fail ≈ 100% and goproxy `/stats` timing out, but Boutique pods are not CPU-overloaded and mesh 5xx is ~0.” That is not a contradiction once Locust `Fail` is read correctly: it is TopFull’s **1-second goodput SLO**, not HTTP rejection. This spec (1) records that finding so we stop treating `Fail/RPS` as RetryGuard ρ, and (2) specifies an **analysis-only** per-service μ̂ / ρ estimator from mesh inbound + detector CPU. **No Locust user-count calibration in this work** — do not raise load until we decide whether S2 should target SLO-miss, CPU-quota overload, or HTTP 5xx.

Related: [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md), [METRICS-GATHERED.md](../../../Guides%20and%20Info/METRICS-GATHERED.md), [METRICS-CATALOG.md](../../../Guides%20and%20Info/METRICS-CATALOG.md), [TOPFULL-THROTTLE-METRICS.md](../../../Guides%20and%20Info/TOPFULL-THROTTLE-METRICS.md), RetryGuard ρ = λ/μ ([RetryGuard.pdf](../../../context/RetryGuard.pdf) §5). Discovery evidence: `experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run11/`. Current full-stack confirmation (same Fail / 5xx=0 / retry=0 picture): [2026-09-13-s1-s2-baseline-metric-checkpoint.md](2026-09-13-s1-s2-baseline-metric-checkpoint.md). Live mesh transport: [2026-09-13-mesh-collector-network-scrape-design.md](2026-09-13-mesh-collector-network-scrape-design.md). Layer A cadence: [2026-09-12-throttle-collector-split-intervals-design.md](2026-09-12-throttle-collector-split-intervals-design.md).

---

## 1. Purpose and scope

**In scope**

- Document Locust `Fail` as TopFull SLO-miss (`elapsed > goodput_threshold`, default **1 s** for all five Boutique APIs), not 5xx/timeout.
- Correct the Guides that currently call `Fail` “5xx / timeout.”
- A small offline script that reads one run folder and prints per-service λ, μ̂, ρ (CPU-linear and, when 5xx is present, saturated-goodput).
- State how goproxy admin timeouts relate to in-flight data-plane work (same process, 0.8 s scrape) — not as “the proxy is dropping Boutique HTTP.”

**Out of scope (explicit)**

- Changing Locust `user_counts` / `spawn_rate` / YAML load-calibration rules.
- Changing `goodput_threshold` in `locust_online_boutique.py`.
- Patching goproxy (out-of-band admin port, longer `/stats` timeout, side thread).
- Runtime `rho.csv` written by a collector during the run.
- Teaching RetryGuard to use ρ; it stays on inbound `Δ5xx/Δtotal`.
- Backfill of `campaign_48/` / `august_38/` (script runs against folders that already have mesh + `topfull_detect.csv`).

---

## 2. What Locust `Fail` actually is (run11 evidence)

TopFull’s Locust file, `TopFull/TopFull_loadgen/locust_online_boutique.py`:

```python
goodput_threshold = {
    "getcart": 1, "postcart": 1, "postcheckout": 1,
    "getproduct": 1, "emptycart": 1,  # seconds
}
# each task:
if response.elapsed.total_seconds() > goodput_threshold[name]:
    response.failure("Too long")
elif not response.ok:
    response.failure(response.status_code)
else:
    response.success()
```

`metric_collector.py` copies Locust’s success/failure listeners into `Fail` / `Goodput`. A **200 OK that took 1.1 s is a Fail.** Mesh inbound still counts that hop as `2xx`.

Run11 steady state (skip first 30 Locust rows):

| API | mean P95 | P95 > 1 s? | Fail/RPS | mean Goodput |
|---|---|---|---|---|
| getcart | 3094 ms | 100% of rows | 1.00 | 0 |
| getproduct | 2129 ms | 100% | 1.00 | 0 |
| postcheckout | 1716 ms | 100% | 1.00 | 0 |
| postcart | 594 ms | 0% | 0.002 | 61.8 |
| emptycart | 408 ms | 0% | 0.002 | 62.5 |

Same run, mesh inbound (end−start over the file span): **5xx fraction = 0** on every HTTP service; frontend ~297 rps almost all 2xx; cartservice ~308 rps all 2xx; productcatalog ~1323 rps all 2xx. `service_edges.csv` retries = 0 on every busy edge.

So the Boutique environment **is** serving the storefront APIs. Locust “100% Fail” on getcart/getproduct/postcheckout means “almost every completed request missed TopFull’s 1 s SLO,” not “the pods rejected the work.”

`postcart` / `emptycart` are the control: same proxy, same cluster, P95 under 1 s → Fail ≈ 0. That is the SLO rule firing, not a broken Locust counter.

**Docs to fix when implementing:** [METRICS-GATHERED.md](../../../Guides%20and%20Info/METRICS-GATHERED.md), [METRICS-COLLECTION-GUIDE.md](../../../Guides%20and%20Info/METRICS-COLLECTION-GUIDE.md), [METRICS-CATALOG.md](../../../Guides%20and%20Info/METRICS-CATALOG.md) currently describe `Fail` as 5xx/timeout. Replace with: SLO-miss (`elapsed > 1 s`) **or** non-OK HTTP status. Derived `Fail/RPS` is **not** RetryGuard ρ and **not** mesh rejection.

**Still unmet (2026-09-13):** those three Guides still say `Fail` = “5xx / timeout.” That edit is still this spec’s remaining doc work. The later metrics refresh updated mesh/throttle collection text, not Fail semantics.

---

## 3. Where the extra latency / goproxy timeouts sit

Two separate effects, one process.

**A. Client SLO-miss (Locust Fail).**  
Wall-clock P95 is 1.7–3.1 s on the three “Failing” APIs while Layer B CPU utilization stays below α (frontend peak ~0.61, cart ~0.54, catalog ~0.56, checkout ~0.27). Frontend is waiting, not CPU-crunched: ~297 rps at ~610 millicores is not 2–3 s of compute. Istio retries are not adding the delay (retry counters 0). Likely contributors, not yet split:

- goproxy holding many in-flight requests (queueing before frontend).
- Frontend page fan-out (getproduct → catalog/currency/ads/recommendations; getcart → cart + catalog + shipping + …). Catalog inbound ~1323 rps vs Locust getproduct ~65 rps is that fan-out, and it is cheap CPU, so Layer B never marks catalog overloaded.

This spec does **not** require pinning A to one hop. A follow-up (not this implementation) is hop latency from Envoy histograms or a one-shot `curl -w` through vs around the proxy.

**B. goproxy `/stats` and `/thresholds` timeouts.**  
Admin GETs are OnRequest hooks on the **same** `:8090` process as the data plane, with a 0.8 s collector timeout. Concurrent in-flight ≈ Σ (API RPS × latency). With getcart ~125 rps × ~3 s plus getproduct ~65 × ~2 s, hundreds of requests occupy the proxy; admin GETs queue and time out. That is expected given A. It is **not** evidence that Boutique inbound 5xx is high, and last-good + `*_fresh` already handles it for Layer A.

Layer A **attempts** default to every **5 s** as of 2026-09-12 ([split-intervals design](2026-09-12-throttle-collector-split-intervals-design.md)); skipped ticks write `*_fresh=0` by design. Filter `*_fresh==1` when using Layer A. The ~24.6% freshness figure from 1 Hz attempts is historical — S2 checkpoint run17 is **1%** (55/3150), mostly not-attempted plus saturation. Do not quote 24.6% as the live number.

Do not treat B as a reason to raise Locust users. More users would likely lengthen in-flight time and make `/stats` worse without moving CPU over α.

---

## 4. What “overload the system under test” means (do not mix)

| Goal | Signal | Run11 |
|---|---|---|
| TopFull paper goodput (SLO) | Locust `Goodput` = requests with HTTP OK **and** `elapsed ≤ 1 s` | Three APIs already at Goodput 0 — SLO-overloaded at the client |
| TopFull detector / RL throttle | `cadvisor_cpu > quota × α` | Almost never; `threshold` stayed at proxy init **10000** |
| RetryGuard ρ > 1 (paper) | per-service λ/μ; surrogate `Δ5xx/Δtotal` | Mesh 5xx ~0 — RetryGuard would not disable |
| HTTP rejection at Boutique | inbound 5xx | ~0 |

Raising Locust users to chase Layer B `overloaded=1` is a **different experiment** from S2 already missing the 1 s SLO. This spec does not choose the load; it only makes the signals distinguishable and estimates μ so a later calibration (out of scope) has a denominator.

`threshold=10000` is the Go limiter’s startup value (`rate.NewLimiter(10000, 10000)`), not a paper Boutique rps table. It moves only after Detector fires and the RL writes `rate_config/` + `SIGUSR1`. Millicore quotas were already synced; they are not supposed to be copied into `threshold`.

---

## 5. μ̂ / ρ estimator (offline)

RetryGuard §5: `ρ_s = λ_s / μ_s` per downstream **Kubernetes service**, not per Locust API.

**Inputs (join on `timestamp`):**

- `service_inbound.csv` — cumulative `total`, `2xx`, `5xx` per service.
- `topfull_detect.csv` — `cadvisor_cpu`, `quota`, `utilization` per service (same wall-clock 1 s grid as mesh on 2026-09-11+ runs).

**Per tick, after differencing inbound counters** (`Δ` vs previous row for that service; skip first row):

```
λ_s(t) = Δtotal / Δt
```

`Δt` is the timestamp delta in seconds (usually 1). If `Δtotal == 0`, skip μ update for that tick (no information).

**Estimator B — CPU-linear (default when `Δ5xx == 0`):**

On ticks with `λ_s > 0` and `0 < utilization_s < α` (unsaturated):

```
μ̂_s,cpu = λ_s / utilization_s
```

Per service, report the **median** of those samples as `μ̂_s`. Then `ρ_s(t) = λ_s(t) / μ̂_s`.

If there are no unsaturated ticks with traffic, do not invent μ̂; print `n/a` and the max utilization.

**Estimator A — saturated goodput (only if `Δ5xx/Δtotal` is meaningfully high, e.g. ≥ 0.05 on a tick):**

```
μ̂_s,sat = Δ2xx / Δt
```

Median over those high-5xx ticks. If A and B both exist and disagree, **prefer A** (non-CPU bottleneck). Run11 will have A = n/a.

**CLI sketch:** `python experiments/estimate_service_mu.py <run_dir>` stdout table: service, λ mean, util peak, μ̂_cpu, μ̂_sat, ρ_cpu median, inbound 5xx fraction. Stdlib + csv only, unittest with tiny fixture CSVs. No YAML writes, no SSH. Prefer a later full-duration folder when available (`…_run17` checkpoint, else run11). Same formula.

**Do not** use Locust `Fail`, Locust `RPS`, or `topfull_throttle.csv` `threshold` / `admitted_rps` as μ or λ for a Boutique service. `admitted_rps` is proxy arrival (and `/stats` logs before `Allow()`), and `threshold` is an entry-API cap.

---

## 6. Tests and docs

- Unit tests: difference λ; CPU-linear μ̂ on a fixture where util=0.5 and λ=100 → μ̂=200; 5xx=0 → no sat estimator; high 5xx → sat estimator used; missing detect file → error, no silent Locust fallback. **Still unmet** — `experiments/estimate_service_mu.py` and its tests do not exist.
- Guide edits listed in §2 (`Fail` semantics; ρ vs Fail). **Still unmet** (2026-09-13).
- `AGENTS.md` remaining-work pointer added (2026-09-13 errata). Do not duplicate the formula there.

---

## 7. Success criteria

- Someone reading the Guides no longer treats run11 `Fail/RPS ≈ 1` as “Boutique returned 5xx.” **Unmet.**
- `estimate_service_mu.py` on run11 (or checkpoint S2 run17) prints CPU-linear μ̂ / ρ for services with mesh + detect data, and does not claim sat-μ from 5xx. **Unmet.**
- No scenario YAML load numbers change. **Held** (only `run_number` / `log_folder` / `transport` moved).

---

## 8. Latency split (2026-09-11 checks)

Checks run after restoring three VirtualServices that had retries omitted (`cartservice`, `checkoutservice`, `productcatalogservice` — leftover RetryGuard OFF). Paper CPU limits were already correct. No Locust / collectors were left running.

**Curl matrix** from `topfull-load` (`FRONTEND=http://10.128.0.3:30440`, `PROXY=http://10.128.0.3:8090`). Idle = no Locust. Loaded = during a short S2 baseline hold.

| Cell | Idle median | Loaded (run12, collectors ON) | Loaded (run13, mesh+throttle OFF) |
|---|---|---|---|
| GET `/cart` **direct** (skip `:8090`) | 0.039 s | **1.84 s** (max 2.11, all 200) | **1.45 s** (max 1.82, all 200) |
| GET `/cart` **via proxy** | 0.036 s | timed out at 30 s mid-sample | **17.6 s** median (max 30 s / code 0) |
| POST `/cart` direct | 0.010 s | *(not finished — probe aborted on GET proxy timeout)* | 0.011 s |
| POST `/cart` via proxy | 0.010 s | *(same)* | 0.011 s |

**Locust P95** (steady rows) for the same short runs vs campaign:

| Run | Collectors | getcart P95 | getproduct P95 | postcart P95 |
|---|---|---|---|---|
| campaign run4 | resource only; envoy 5 s / 2 callers; no throttle | 1563 ms | 1303 ms | 217 ms |
| run11 (prior) | mesh 1 s + throttle 1 s | 3094 ms | 2129 ms | 594 ms |
| run12 (180 s) | mesh 1 s + throttle 1 s | 2648 ms | 1989 ms | 623 ms |
| run13 (180 s) | mesh+throttle **OFF** | 2462 ms | 1914 ms | 741 ms |

**Read:**

1. Idle GET `/cart` is ~40 ms either path — the cart page is fine with no Locust. The >1 s SLO miss is **under S2 load only**.
2. Under load, **direct** GET `/cart` is already **1.4–1.8 s** (HTTP 200). Boutique’s frontend path alone exceeds TopFull’s 1 s goodput bar. Envoy 2xx vs Locust Fail is expected: slow success.
3. Under load, **via proxy** GET `/cart` jumps to ~18–30 s. goproxy queueing **amplifies** latency on Locust’s real path; it is not the only cause.
4. POST `/cart` stays ~10 ms under load on both paths — API shape, not a dead cluster.
5. run12 ≈ run13 on Locust getcart P95 (~2.5–2.6 s). **1 s mesh + throttle collectors are not the main cause** of the SLO miss. They may still add a little (run11 was worse); they do not create the 1.5 s direct-path cost.
6. Both short runs are slower than campaign run4 (~1.6 s getcart). Something besides “collectors on/off” differs from early September (load mix, cluster age, or other process noise) — not isolated here.

**Next (out of scope for this check):** hop-level timing inside the frontend fan-out; whether to treat S2 as SLO-overload (already true for Locust path) vs chasing CPU/5xx; do **not** raise Locust users until that choice is explicit.

YAML after checks: `scenario_2_baseline.yaml` restored to `enabled: true` for mesh+throttle, `duration_seconds: 600`, next free slot **run14** *at the time*. **Do not launch run14 now** — current S2 baseline slot is **run18** (see Status).

### Addendum — 2026-09-12 collector-tax recheck

Phase 3 short S2 baseline pair after worker-local mesh + split Layer A: run15 (mesh + throttle **ON**) vs run16 (both **OFF**), compared to the 2026-09-11 pair run12 ON vs run13 OFF. Locust `user_counts` unchanged. 180 s scratch holds — **not** campaign S2, **not** a claim that S2 is fixed.

Pass/fail is a **smaller on-vs-off gap**, not zero collector cost.

| Metric | run12 ON | run13 OFF | gap | run15 ON | run16 OFF | gap |
|---|---|---|---|---|---|---|
| GET /cart direct loaded median | 1.84 s | 1.45 s | 0.39 s | 1.60 s | 1.36 s | 0.24 s |
| Locust getcart P95 | 2648 ms | 2462 ms | +186 ms | 2342 ms | 2532 ms | −190 ms |

**Direct-gap verdict:** shrank (0.39 s → 0.24 s).
**P95-gap verdict:** reversed (ON is faster this pair: −190 ms vs +186 ms).

Via-proxy 17–30 s remains extra context only. Both new loaded via-proxy medians (run15 and run16 ~0.039 s) are **teardown-contaminated** (samples landed at Locust stop) — do not use them as pass/fail.

Mesh CSVs (`service_edges.csv`, `service_inbound.csv`) landed on run15 via the two-hop worker → master copy. Run16 (collectors off) correctly has no mesh/throttle files.

Direct GET `/cart` under load is still **>1 s** with HTTP 200 on both new cells. Boutique path alone still misses TopFull's 1 s goodput bar; collectors are not the main cause. Do **not** raise Locust users from this recheck.

YAML after this recheck: `scenario_2_baseline.yaml` restored to mesh+throttle+resource **ON**, `duration_seconds: 600`, next free slot **run17** *at the time*. That slot was later used by the 2026-09-13 checkpoint. **Do not launch it.** Current S2 baseline is **run18**.

### Addendum — 2026-09-12 S1 collector-credit trio

Short S1 baseline holds after the S2 tax recheck, to split **mesh vs throttle** credit. Same Locust `user_counts` as deck S1. Resource-usage stayed **on** in every arm. Scratch slots — **not** campaign S1.

| Slot | Arm | duration | getcart P95 | getcart Fail | getproduct P95 | GET `/cart` direct median |
|---|---|---|---|---|---|---|
| run7 | both on (reference) | 300 s | 1374 ms | 29.2 | 1017 ms | *(no mid-hold probe)* |
| run8 | **mesh only** | 180 s | **1370 ms** | **26.7** | 1018 ms | 0.125 s *(noisy / soft)* |
| run9 | **throttle only** | 180 s | **912 ms** | **1.9** | 767 ms | 0.524 s |
| run10 | **both off** | 180 s | **900 ms** | **1.5** | 782 ms | 0.397 s |

Credit vs run10 (Locust, skip first 30 s):

- **mesh tax** ≈ run8 − run10: getcart P95 **+470 ms**, Fail **+25.2**
- **throttle tax** ≈ run9 − run10: getcart P95 **+12 ms**, Fail **+0.4**

**Verdict (historical for `docker_local` only):** on S1, the leftover collector tax was almost entirely the **worker-local mesh** scrape (`docker_local`, 11 sidecars / 1 s / pool 4). Throttle (Layer A every 5 s + Layer B every 1 s from master) is negligible here. run7 both-on ≈ run8 mesh-only, same story.

The 2026-09-13 `network_prometheus` transport superseded this leftover-tax story: S1 run20 vs run10 is ~**+6 ms** getcart P95; the cool credit pair (run18/19) is ~**+37 ms**. Do **not** use +470 ms as the live tax.

Campaign S1 run6 was still ~725 ms getcart with Fail ≈ 0. run10 both-off is ~900 ms — a **cluster-age / environment** gap remains with collectors off. Do **not** treat this as “turn off mesh and S1 is campaign-clean,” and do **not** raise Locust users from this trio.

Loaded GET `/cart` **direct** medians are secondary: run8’s 0.125 s looks like a soft window (Locust still showed ~1.4 s P95). Prefer Locust for the credit call.

YAML after this trio: `scenario_1_baseline.yaml` restored to mesh+throttle+resource **ON**, `duration_seconds: 300`, next free slot **run11** *at the time*. S1 then jumped through later 09-13 work. **Do not launch run11.** Current S1 baseline is **run21**.

---

## Status

**Still TODO (this spec’s implementation):** Guide `Fail` wording (§2) and `experiments/estimate_service_mu.py` (§5–§7). Load-calibration (raise users until ρ_cpu > 1 or inbound 5xx moves) stays a later spec, after we decide which row of the §4 table S2 is supposed to hit. Do not raise Locust users; do not teach RetryGuard ρ.

**Done (measurement / collector follow-ons — not the μ script):**

- Latency-path checks above (2026-09-11).
- S2 collector-tax recheck and S1 mesh-vs-throttle credit trio (2026-09-12). The +470 ms leftover tax in that trio is **`docker_local` history**.
- Layer A split interval (default **5 s**) landed — [2026-09-12-throttle-collector-split-intervals-design.md](2026-09-12-throttle-collector-split-intervals-design.md).
- Mesh transport: `docker_local` landed then was replaced by `network_prometheus` on master — [2026-09-13-mesh-collector-network-scrape-design.md](2026-09-13-mesh-collector-network-scrape-design.md).
- S1 run20 **PASS** / S2 run17 **FAIL on retry gates only** — [2026-09-13-s1-s2-baseline-metric-checkpoint.md](2026-09-13-s1-s2-baseline-metric-checkpoint.md). Same §2/§4 picture: Locust Fail is SLO-miss; inbound/outbound 5xx = 0; Envoy retry = 0; Layer B `overloaded=0` (frontend peak util 0.737). Leftover collector tax vs run10 ~**+6 ms**. Do **not** gate “collector stack works” on Envoy retry increment — Istio retries need 5xx.

**YAML now:** S1 baseline **run21**, S2 baseline **run18**. Do not launch the §8 “next slot” numbers (S1 run11 / S2 run14 / S2 run17). Discovery evidence stays run11. Prefer checkpoint S2 run17 as the first μ script target (full duration, live outbound 2xx).
