# 600 req/s ceiling snapshot — run154

Both-off S2 **run154** (`baseline_no_topfull_sustained_overload_run154`) held mix **150 / 30 / 150 / 250 / 250** (getproduct / postcheckout / getcart / postcart / emptycart, configured sum 830) for 600 s on Paper-C1, with TopFull and RetryGuard off. The Go proxy stayed up, `paper_cpu_reconcile` stayed false, and the sidecar request stayed at 100 m.

Folder: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run154/`.

## Gates

`python experiments/ceiling_summary.py` on that folder exited 1.

| Gate | Result |
|---|---|
| `total.csv` rows ≥ 540 | PASS 559 |
| mesh span 480–900 s | PASS 702 |
| frontend inbound gap2 ≤ 10% | **FAIL 58.1%** |
| replica pin (frontend 4, others 1) | PASS |
| Layer A threshold below 10000 on ≤ 1% of rows | PASS 0.0% |

The failing gate counts a 2.0 s inbound step as a gap. Of 444 frontend intervals, 258 were exactly 2.0 s and 186 were exactly 1.0 s. The longest step is 2.0 s. There is no multi-second scrape hole. The 702 s span includes collector time before Locust. The hold does not count.

## Candidates

Readings are in `readings/`. Status is over, under, cleared, or inconclusive against the lines in the [snapshot spec](../docs/superpowers/specs/2026-10-05-600-rps-ceiling-snapshot-design.md) §5. These statuses are for the record. They do not name a limiter.

| Candidate | Reading | Line | Status |
|---|---|---|---|
| 1. Master | busy **1.94** of 8; `proxy_online_boutique` **33.3%** of one core | Over: busy ≥ 7.2 or proxy ≥ 80%. Cleared: busy < 6 and proxy < 50% | **cleared** |
| 2. Worker | busy **7.44** of 16; steal **0.11%** | Over: busy ≥ 14.4 or steal > 5%. Cleared: busy < 13 and steal ≤ 2% | **cleared** |
| 3. Envoy | `--concurrency 2` (line 2000 m). Hottest non-frontend `productcatalogservice` **662 m**. Frontend sidecars **377–447 m** | Over: a proxy within 10% of 2000 m (1800–2200 m). Absent concurrency → inconclusive | **under** |
| 4. Shared path | emptycart mean P95 **110 ms**; getproduct **546 ms**; getcart **484 ms** | Over: emptycart P95 > 200 ms. Cleared: emptycart P95 < 100 ms and getproduct or getcart P95 > 1000 ms | **under** |

Master process CPU over the same 60 s, percent of one core: `envoy_retry_collector.py` 48.3, `proxy_online_boutique` 33.3, `metric_collector.py` 6.7, `topfull_throttle_collector.py` 3.3, `resource_usage_collector.py` 0.0, `go run proxy_online_boutique.go` 0.0. The proxy figure used above is the built `proxy_online_boutique` child, not the `go run` parent.

Envoy on `frontend-85ff4b5b6d-8zjvs` and on `productcatalogservice-77f5596b54-dq8d6`: pid present, 12 threads, `--concurrency 2`. Other sidecar millicores: cart 297, recommendations 294, currency 231, checkout 189, shipping 95, ad 58, redis-cart 34, email 31, payment 25.

## Per tag

Means over Locust CSV rows 60 through end−5 (the summary window).

| Tag | Mean RPS | Mean P95 |
|---|---:|---:|
| getproduct | 108.0 | 546 ms |
| postcheckout | 22.0 | 439 ms |
| getcart | 107.9 | 484 ms |
| postcart | 180.2 | 204 ms |
| emptycart | 179.7 | 110 ms |

Sum of the five tag means: **597.8** req/s. The ceiling band is 450 through 705 (705 is 0.85 × 830). 597.8 sits in that band. Frontend inbound λ (mean of deltas) is **463.8** req/s.

## Verdict

The verdict is **gate failed**. The tag sum sits in the ceiling band and the four readings are on the record (master cleared, worker cleared, Envoy under, shared path under), and no limiter is named because the hold does not count. Isolation holds in spec §7 are deferred until a counted hold.

## What was measured

The planned window started about 120 s after Locust (`[21:20:14] Locust running`, local UTC+3, so 18:20:14Z). Worker and load CPU are 21:22:15–21:23:18. Proxies are the `kubectl top` sample at 21:22:45. The first master CPU sample at 21:22:14 failed: the process regex was passed unquoted, so `|` became a pipe. Master was retaken at 21:23:57–21:24:59, still inside the 600 s hold, and that retry is the file in the folder. The failed attempt was not copied in.

The 90 m sidecar fallback was not used. The replica pin passed with frontend at 4 and every other service at 1, and the sidecar request was left at 100 m with `proxyCPULimit` unset.

Load-generator CPU was recorded and is not a candidate: busy **1.07** of 8, steal **0.03%**, eleven Locust processes, the busiest two at 26.7% of one core. Per-tag RPS and P95 come from the pulled Locust CSVs over rows 60 through end−5, not from a live read of the stats ports. Layer A stayed at the 10000 passthrough (fraction of rows below 10000 is 0.0).
