# gRPC statuses in the retry policy and the rejection rate

Two changes. They use the same gRPC codes and they do not share a counter.

Online Boutique calls between services are gRPC. A finished RPC is HTTP 200 with the result in `grpc-status`. Envoy's HTTP `5xx` class does not include that. A caller abort before any response is a reset, and that one is already counted.

## Why a gRPC error is HTTP 200

gRPC over HTTP/2 requires the response headers to carry `:status 200`. The outcome of the call is a second field, `grpc-status`, in the trailers. The gRPC protocol states this directly: the HTTP status of a gRPC response is `:status 200`, and an application or runtime error is delivered as `grpc-status` in the trailers. An immediate failure with no body is still HTTP 200. It is headers and trailers in one frame.

Headers go out before the body. The server often does not know whether the call succeeded until the handler has finished, and a streaming call may already have sent messages by then. Trailers are the HTTP/2 place for a result decided at the end of the stream, so the protocol puts the real status there and leaves the HTTP status at 200. The HTTP code answers "did a gRPC response arrive?" `grpc-status` answers "what did the service say?"

HTTP 5xx and resets are the cases where no gRPC response was produced. A proxy can return 503 because it never reached a backend. A caller that hits the 500 ms timeout aborts the stream, and then there is no HTTP status at all. The protocol reserves `RST_STREAM` for a broken frame stream, not for an application error. Those aborted calls show up as `response_code` 0 with no `grpc-status`, which is the reset count.

On `recommendationservice-76cb6c5975-6w4xw` the three rows are separate. The 75,363 resets are not inside the 155,750 deadline-exceeded calls.

| HTTP code | gRPC status | Count | What it is |
|---|---|---:|---|
| 200 | 0 (OK) | 145,881 | the service finished the call successfully |
| 200 | 4 (deadline-exceeded) | 155,750 | the service finished the call and reported the failure |
| 0 | none | 75,363 | the caller aborted before a response |

145,881 + 155,750 = 301,631, the Envoy `2xx` count. Adding the 75,363 resets gives the total, 376,994. Deadline-exceeded is inside `2xx` because the process completed the RPC and reported that status. The reset row has no gRPC status because the stream was torn down first.

The sidecar's `istio_requests_total` (`reporter="destination"`) is the series that records the gRPC status, including the trailer. Scraped 2026-10-07 from `/stats/prometheus` on the current pods. These are counters since the pod started, not one hold.

| Service | Pod | Total | HTTP 5xx | Resets (`rx_reset`) | gRPC errors inside the 2xx count |
|---|---|---:|---:|---:|---|
| checkoutservice | `checkoutservice-9c45f9dcb-2w9sj` | 34,460 | 0 | 7,385 | 6,688 deadline-exceeded (4), 178 unavailable (14), 88 internal (13) |
| recommendationservice | `recommendationservice-76cb6c5975-6w4xw` | 376,994 | 0 | 75,363 | 155,750 deadline-exceeded (4) |
| paymentservice | `paymentservice-7957995d8b-72gt7` | 132,826 | 0 | 3,478 | 183 deadline-exceeded (4), 587 unknown (2) |
| productcatalogservice | `productcatalogservice-77f5596b54-88jn6` | 4,321,019 | 0 | 13 | none |

On checkout and recommendations, `2xx + resets = total`. The gRPC errors are inside `2xx`. On checkout, `response_code="0"` in the Istio series equals `rx_reset` (7,385). On recommendations the same pair is 75,363. Payment does not partition that cleanly: `2xx + resets` is 592 above `total`, and `response_code="0"` is 2,886 against `rx_reset` 3,478.

Codes, from the gRPC HTTP mapping:

| Code | Name | HTTP class |
|---|---|---|
| 2 | UNKNOWN | 500 |
| 4 | DEADLINE_EXCEEDED | 504 |
| 13 | INTERNAL | 500 |
| 14 | UNAVAILABLE | 503 |

`CANCELLED` (1) is HTTP 499. `RESOURCE_EXHAUSTED` (8) is HTTP 429. Neither is a 5xx rejection. Neither showed up on these four pods.

## 1. Retry policy

Keep `attempts: 3` and `perTryTimeout: 500ms`. Change `retryOn` from `5xx,reset,connect-failure` to:

```text
5xx,reset,connect-failure,internal,unavailable,deadline-exceeded
```

`5xx` already retries an HTTP 500, 502, 503, or 504. On the Envoy in this cluster (1.25.10) it also already includes a reset, a connect failure, and HTTP/2 `REFUSED_STREAM`, which is why a try that passes 500 ms is retried today. `reset` and `connect-failure` stay so the string still contains the policy we run now.

`internal`, `unavailable`, and `deadline-exceeded` are the Envoy names for gRPC 13, 14, and 4. They belong in the same `retryOn` string. Istio writes that string into Envoy's `retry_on`, which accepts the HTTP names and the gRPC names together. `UNKNOWN` (2) has no Envoy retry token, so a completed unknown status still will not be retried.

This only decides when a retry is sent, and only while the route has 1, 2, or 3 attempts. The off route is `retries: {attempts: 0}` plus a 500 ms route timeout. It has no `retryOn`, so these names do nothing there. The rejection rate does not read `retryOn`.

Envoy 1.25 applies the gRPC names only when the status is in the response headers. A normal finished RPC puts `grpc-status` in the trailers, and this Envoy will not retry that. The new tokens catch an early rejection, the kind a proxy or a server sends before a body. They do not catch an application error that completes the stream. The 500 ms timeout path is unchanged: that retry is a local reset, not a gRPC status.

Same string in:

- `experiments/virtual-services.yaml` (all 10 VirtualServices)
- `RETRY_ON` in `experiments/retryguard.py`
- both patch builders in `experiments/run_scenario.py` (`apply_per_try_timeout`, `restore_virtualservice_retries`)
- the tests that assert the current string

## 2. Rejection rate

The off-state signal stays a rejection rate, and it stays the thing consulted only while an edge is at 0 attempts. The numerator is what changes.

Today `measure_inbound_rejection` in `experiments/retryguard.py` computes `(Δ5xx + Δresets) / Δtotal` from `service_inbound.csv`. `5xx` and `resets` come from `downstream_rq{response_code_class="5xx"}` and `downstream_rq_rx_reset` in `experiments/envoy_retry_collector.py`. `connect-failure` is not in this ratio. It is only a retry token, and a connect failure never arrives at the callee, so the callee's inbound counters cannot record it.

HTTP `5xx` is 0 on all four pods above. Every failure the formula counts today is a reset. Deadline-exceeded, the largest gRPC failure on checkout and recommendations, is counted as a success. Recommendations is 75,363 / 376,994 (20%) with the current numerator and 231,113 / 376,994 (61%) once deadline-exceeded is included. Checkout is 7,385 / 34,460 (21%) and 14,339 / 34,460 (42%) once codes 4, 13, and 14 are included.

Add those completed gRPC failures to the numerator. Take them from `istio_requests_total` on the same `/stats/prometheus` scrape the collector already fetches, restricted to `reporter="destination"` and `grpc_response_status` in `2`, `4`, `13`, `14`. Store the sum as its own column on `service_inbound.csv` (appended, so readers that use column names keep working). The rate becomes:

```text
(Δ5xx + Δresets + Δgrpc_5xx) / Δtotal
```

`grpc_5xx` is that new column. `Δtotal` already includes these RPCs, because they completed as HTTP 200. Adding them to the numerator does not count them twice. Leave `response_code="0"` out of `grpc_5xx`. On checkout and recommendations that series is the reset count, and `resets` already has it.

`downstream_rq_*` cannot supply this split. The class counter has nowhere to put a gRPC status. `istio_requests_total` is the series that has it, and it is already in the scrape.

## Reasons to leave this unchanged

The retry-policy change does very little for the errors in the table above. The rejection-rate change changes a threshold that was tuned on the old numerator.

**Retry tokens.** The 155,750 deadline-exceeded calls on recommendations are finished RPCs. The status is in the trailers. Envoy 1.25 retries `deadline-exceeded`, `unavailable`, and `internal` only when the status is in the response headers, so those calls would still not be retried. The same is true of the checkout and payment rows. The tokens would catch an early rejection that arrives before a body, which is not the bulk of what the sidecars recorded. `UNKNOWN` (the 587 payment calls) has no retry token, so that row stays unretried either way.

Adding the tokens still changes every later hold. Both arms share `retryOn`, so baseline and RetryGuard retry counts stop being comparable to the runs already stored. A header-level `internal` or `deadline-exceeded` on `PlaceOrder` or `Charge` would also send the RPC again. Those calls are not idempotent, and the gRPC protocol does not treat them as safe to retry unless the method is marked that way. The 500 ms timeout path already retries the slow calls, which is the overload this project actually produces.

**Rejection rate.** The 20% to 61% figure is the recommendations pod's whole life, covering every hold since it started, mostly with retries on. The controller reads this rate only while an edge is at 0 attempts. In that state the route timeout aborts a slow call at 500 ms, and the abort is already a reset. The deadline-exceeded responses are the calls that finished. Many of those happen while retries are on, which is when the controller watches retries per request and ignores this rate. Putting the lifetime ratio into the off-state formula overstates how much the off window would move.

The off-state thresholds were set against `(Δ5xx + Δresets) / Δtotal`: shed behavior elsewhere uses 0.20, and the 0-to-1 step requires the rate to stay under 0.10. A larger numerator makes the same numbers mean a busier service. Re-enable gets harder, and a burst of `UNKNOWN` or deadline-exceeded from a short application deadline would hold retries off without the service being in the reset storm the threshold was chosen for.

`istio_requests_total` is also a different counter from `downstream_rq`. It has to be limited to `reporter="destination"` and to HTTP 200, or the reset rows get added twice. Payment already fails that partition: `2xx + resets` is 592 above `total`. A tick where the two counters disagree makes the ratio jump, including above 1.

The runs already scored — streaks, blend bars, RetryGuard logs — use the old numerator. A new column does not rewrite them, but a streak from a new hold is not the same measurement as a streak from run 89.

## Decision

The retry string and the rejection rate now differ per callee.

`adservice`, `currencyservice`, `productcatalogservice`, and `recommendationservice` use `retryOn: 5xx,reset,connect-failure,unavailable,deadline-exceeded` and count `grpc_4 + grpc_14` (deadline-exceeded and unavailable) in the rejection rate. `cartservice` and `shippingservice` stay on the current string, `5xx,reset,connect-failure`, and on `(Δ5xx + Δresets) / Δtotal`. So do `checkoutservice`, `paymentservice`, and `emailservice`. Each callee still has one route rule.

`service_inbound.csv` stores those codes as `grpc_2`, `grpc_4`, `grpc_13`, and `grpc_14`. Folders written before this change keep the single `grpc_5xx` column.

Both-off run158 is the live check of that split on run157's mix, with RetryGuard off. Mid-hold, the VirtualServices matched it. `recommendationservice` `grpc_4` rose by 246,525 and `grpc_14` stayed 0. frontend→recommendations retries were 286,332, against run157's 284,199. That is not a clear rise, so the new tokens did not add retries. frontend→checkout retries were 1,606, against 1,517. Hold B was not started. The rejection-rate half is in the controller for those four callees and was not exercised on this hold.

## Holds

Two RetryGuard-only holds of the run 89 mix (275/90/100/90/5), Paper-C1, TopFull off, 360 s cool-off between them. The controller is the same one as run15, including the 0→1 bar at rejection 0.10 and the 500 ms route timeout while attempts are 0. `grpc_5xx` is recorded and unused.

| | run16 | run17 |
|---|---:|---:|
| Locust `total.csv` lines | 566 | 567 |
| Total goodput (req/s) | 486 | 414 |
| Failure fraction | 0.081 | 0.189 |
| P95 (ms) | 384 | 665 |
| Frontend replicas | 4 on 139/139 | 4 on 138/138 |
| checkout Δresets / Δgrpc_5xx | 11,034 / 9,644 | 9,909 / 8,062 |
| recommendations Δresets / Δgrpc_5xx | 5,674 / 14,330 | 29,354 / 51,596 |
| frontend→checkout retries | 5,355 | 3,277 |
| frontend→recommendations retries | 14,078 | 59,617 |
| Shed / restore | checkout 3→0 and 1→0; recommendations 3→0 then restore to 1; checkout's second shed was not restored | checkout 3→0, restored to 1; recommendations stayed at 3 |

HTTP 5xx stayed 0 on checkout, recommendations, payment, and email. The gRPC column moved on its own: on run17, recommendations' completed gRPC failures (51,596) are larger than its resets (29,354). The controller still shed only from retries per request, and it restored on a rejection of 0.00. Folders: `experiments/results/campaign_48/S2_sustained_overload/run_retryguard_no_topfull_sustained_overload_run16` and `…_run17`.

### Both-off run157 (mix 340/115/150/5/5)

One 600 s hold with TopFull off and RetryGuard off. Retries stayed at 3 for the whole window. `grpc_5xx` is recorded and unused. Paper-C1 pin, frontend at 4 for every resource sample, Layer A stayed at the 10000 passthrough. Folder: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run157`.

| | run157 |
|---|---:|
| Locust `total.csv` rows | 560 |
| Total arrived / goodput (req/s) | 388 / 111 |
| Failure fraction | 0.71 |
| P95 (ms) | 1318 |
| Frontend replicas | 4 on 135/135 |
| checkout Δresets / Δgrpc_5xx | 1,000 / 1,120 |
| recommendations Δresets / Δgrpc_5xx | 108,865 / 281,669 |
| payment Δresets / Δgrpc_5xx | 581 / 326 |
| email Δresets / Δgrpc_5xx | 62 / 16 |
| frontend→checkout retries | 1,517 |
| frontend→recommendations retries | 284,199 |

HTTP 5xx stayed 0 on those four backends. Recommendations is the busy service: completed gRPC failures are about 2.6× the resets, and frontend→recommendations retries are 284k. Checkout stays light (about 1k resets and 1.1k `grpc_5xx`).

Longest streak of ticks with rejection > 0.20 (controller interval is 30). The second column is a reading of the CSV; the hold did not act on it.

| Service | `(Δ5xx+Δresets)/Δtotal` | `(Δ5xx+Δresets+Δgrpc_5xx)/Δtotal` | Partition ticks |
|---|---:|---:|---:|
| checkoutservice | 17 | 19 | 7 |
| recommendationservice | 24 | 553 | 1 |
| paymentservice | 3 | 6 | 2 |
| emailservice | 4 | 4 | 0 |

On recommendations, resets alone never clear a streak of 30. Adding `grpc_5xx` makes the same hold look like a near-continuous high streak (553 of 596 ticks). Checkout barely moves (17 → 19). That is the opposite shape from the RetryGuard-only runs 16 and 17, where `grpc_5xx` mainly mattered in short off windows and quiet restore tails.

### RetryGuard-only run18 (same mix as run157)

One 600 s hold with TopFull off and RetryGuard on (`edge_rpr`). Same mix as run157 (340/115/150/5/5). Paper-C1, frontend at 4 for every resource sample, Layer A stayed at the 10000 passthrough. `grpc_5xx` is recorded and unused. Folder: `experiments/results/campaign_48/S2_sustained_overload/run_retryguard_no_topfull_sustained_overload_run18`.

| | run157 (both-off) | run18 (RG-only) |
|---|---:|---:|
| Locust `total.csv` rows | 560 | 560 |
| Total arrived / goodput (req/s) | 388 / 111 | 521 / 261 |
| Failure fraction | 0.71 | 0.50 |
| P95 (ms) | 1318 | 493 |
| Frontend replicas | 4 on 135/135 | 4 on 139/139 |
| checkout Δresets / Δgrpc_5xx | 1,000 / 1,120 | 874 / 833 |
| recommendations Δresets / Δgrpc_5xx | 108,865 / 281,669 | 68,266 / 106,652 |
| frontend→checkout retries | 1,517 | 1,228 |
| frontend→recommendations retries | 284,199 | 23,402 |
| Shed / restore | (no controller) | `frontend→recommendationservice` 3→0 at rpr **1.47**; **no** OFF→ON |

HTTP 5xx stayed 0 on checkout, recommendations, payment, and email. Checkout never cleared a high streak of 30 (max `high` was 9). Recommendations shed once about 115 s after Locust started and stayed at 0 attempts for the rest of the hold: 262 callee `rejection` samples, every one ≥ 0.129, so the 0→1 bar at 0.10 never advanced (`low` stayed 0).

Longest streak of ticks with rejection > 0.20 (CSV reading only; controller decisions used rpr / reset rejection).

| Service | `(Δ5xx+Δresets)/Δtotal` | `(Δ5xx+Δresets+Δgrpc_5xx)/Δtotal` | Partition ticks |
|---|---:|---:|---:|
| checkoutservice | 8 | 8 | 5 |
| recommendationservice | 14 | 292 | 0 |
| paymentservice | 0 | 0 | 0 |
| emailservice | 2 | 3 | 0 |

Against run157, shedding recommendations cut frontend→recommendations retries from 284k to 23k and raised storefront goodput from 111 to 261 req/s. Resets alone still never clear a streak of 30 on recommendations; adding `grpc_5xx` still makes a long high streak (292). The live restore path never saw a quiet reset window, so `grpc_5xx` was not needed to keep the edge off.

### Both-off run158 (same mix, per-callee retryOn)

One 600 s hold with TopFull off and RetryGuard off. Same mix as run157 (340/115/150/5/5). Paper-C1, frontend HPA already min=max=4 (sidecar request left at 100m, `proxyCPULimit` unset). The four read-only callees retry on `unavailable,deadline-exceeded`; cart, shipping, checkout, payment, and email stay on `5xx,reset,connect-failure`. Folder: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run158`.

| | run157 | run158 |
|---|---:|---:|
| Locust `total.csv` rows | 560 | 562 |
| Total arrived / goodput (req/s) | 388 / 111 | 380 / 135 |
| Failure fraction | 0.71 | 0.65 |
| P95 (ms) | 1318 | 1258 |
| Frontend replicas | 4 on 135/135 | 4 on 135/135 |
| recommendations Δresets / Δgrpc_4 / Δgrpc_14 | 108,865 / (grpc_5xx 281,669) | 109,469 / 246,525 / 0 |
| checkout Δresets / Δgrpc_4 / Δgrpc_14 | 1,000 / (grpc_5xx 1,120) | 1,094 / 1,077 / 32 |
| frontend→checkout retries | 1,517 | 1,606 |
| frontend→recommendations retries | 284,199 | 286,332 |

`service_inbound.csv` ends with `grpc_2,grpc_4,grpc_13,grpc_14`. HTTP 5xx stayed 0 on recommendations and checkout. Recommendations `grpc_4` is non-zero (246,525). The retry edge did not rise clearly above run157, so RetryGuard-only run19 was not started. Inbound timestamps run 2026-10-07T19:50:56Z to 20:02:35Z (413 polls). Retry counters were monotonic, so the holes do not shrink the retry delta.

## Conclusions

The live policy is the Decision section above: the retry string and the rate differ per callee, and cart and shipping stay on `5xx,reset,connect-failure`. The paragraphs below describe the earlier `grpc_5xx` observation holds, which predate that split.

HTTP 5xx is still 0, so the live numerator is the reset count. `grpc_5xx` is a second failure count of the same order. On checkout it was about 0.85 of the resets (9,644 / 11,034 on run16, 8,062 / 9,909 on run17). On recommendations in run17 it was larger than the resets (51,596 against 29,354). The lifetime scrape that put deadline-exceeded inside `2xx` is the same split, now measured on a single hold.

The 500 ms route timeout leaves that second count in place. Checkout's off windows are the minutes the controller consults the rejection rate. In those windows `grpc_5xx` was 0.129 of arrivals on run16 and 0.182 on run17, beside reset rates of 0.152 and 0.229. A call the service finishes as a gRPC error before 500 ms completes as HTTP 200 and lands in `grpc_5xx`. The timeout aborts a call that is still open at 500 ms, and that abort is the reset. Both endings happen while attempts are 0. The earlier reading, that deadline-exceeded belongs to the minutes when retries are on, does not fit these holds.

Adding the two endings would move the off-window average across the 0.20 line: checkout goes from 0.152 to 0.281 on run16 and from 0.229 to 0.411 on run17. The 0→1 step does not use that average. It waits for 30 samples under 0.10. The samples that restored checkout were already quiet on both counters. The run16 restore at 12:17:07 ends on 28 samples with resets and `grpc_5xx` both 0. The run17 restore at 12:43:21 ends on 30 samples with a reset rate of 0.002 and `grpc_5xx` of 0. The summed rate on those tails is the reset rate.

The one window where the streak length changes is recommendations on run16. That edge was off for 37 samples. The longest run under 0.10 is 31 samples on resets alone and 28 once `grpc_5xx` is included. Four samples are under 0.10 on resets and at or above 0.10 on the sum. The controller restored that edge at rejection 0.00. The summed rate stays short of 30 samples in that window.

The two counters also slip against each other. On checkout, 27 of 609 ticks in run16 and 13 of 611 in run17 have `Δresets + Δgrpc_5xx` above `Δtotal`, or `Δgrpc_5xx` above `Δ2xx`. Recommendations has 0 such ticks in run16 and 1 in run17. A ratio that adds them can step over 1 on those checkout ticks. That is the same partition failure the payment pod showed on the lifetime scrape, now on a per-tick checkout series.

The two holds used the same mix and the same controller, and recommendations did not repeat. run16 shed it once (14,078 retries, `grpc_5xx` at 5% of arrivals). run17 left it at 3 attempts (59,617 retries, `grpc_5xx` at 16%, reset rate 0.093). Storefront goodput was 486 req/s, then 414. The shed and the restore followed retries per request and then the reset rate. `grpc_5xx` rose and fell with that storm and stayed out of the decision.

On runs 16 and 17, `retryOn` was still `5xx,reset,connect-failure`. The failures in those holds completed as HTTP 200, which is the trailer case Envoy 1.25 leaves unretriable. Those holds did not produce a header-level gRPC status to retry. Run158 then added `unavailable,deadline-exceeded` on the four read-only callees, and frontend→recommendations retries still did not rise clearly above run157.
