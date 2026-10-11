# Recommendations stayed off: rejection, CPU, and the TopFull cap

Read with the Set A tables in [2026-10-09-s2-reenable-rejection-set-a.md](2026-10-09-s2-reenable-rejection-set-a.md). Holds are the locked S2 mix (275 / 90 / 100 / 90 / 5), Paper-C1, edge-mode RetryGuard. "Hot" means recommendations sojourn near 400 ms. "Cool" means it near 40–50 ms.

## What RetryGuard did

Edge mode watches one caller→callee edge. `rpr = Δretry / (Δtotal − Δretry)`.

| Step | Condition | Quiet time | Result |
|---|---|---|---|
| any → 0 | rpr > 0.5 | 30 s | attempts drop straight to 0, route timeout 500 ms |
| 0 → 1 | callee rejection strictly under the hold's bar (0.10, 0.15, or 0.20) | 30 s | 1 attempt, not 3 |
| 1 → 2 | rpr ≤ 0.17 | 15 s | 2 attempts |
| 2 → 3 | rpr ≤ 0.33 | 15 s | 3 attempts |

Rejection is `(Δ5xx + Δresets) / Δtotal` on that callee. Between the climb bar and 0.5 the attempt count holds. Above 0.5 for 30 s it sheds straight back to 0. TopFull's cap is not an input.

Recommendations shed on the hot holds and never came back. After the shed, OFF-window rejection sat near 0.27 for the rest of the hold (about 520 samples on the RetryGuard-only copies). Samples under the bar were scattered. The longest under-bar streak was 1–3 samples, against the 30 s the 0→1 step needs. HTTP 5xx on recommendations was 0. The rejection is resets from the 500 ms route timeout.

Checkout did re-enable on 010 off1 and 020 off1. Its sojourn fell to about 200 ms once retries were off, rejection went to 0.00, and it climbed 1→2→3.

## The postcheckout cap did not cool recommendations

Every both-on hold moved the postcheckout cap (about 10–99) for most of the 600 s. getproduct and getcart stayed at the 10000 passthrough except for short stretches on 010 on2 (13 and 12 fresh caps) and 015 on3 (27 and 24). Those browse caps sat near the configured 275 / 100.

Recommendations inbound arrival stayed about 310–450 req/s on every both-on hold, including while postcheckout was capped.

| Hold | postcheckout caps | recommendations sojourn during the cap | checkout sojourn |
|---|---|---|---|
| 010 on1, 015 on1, 015 on2, 020 on1, 020 on2, 020 on3 | 143–152 | 39–54 ms | 303–324 ms |
| 010 on2 (`rr010_rgtf1_rep3`) | 495, ending 38.5 | 406 ms | 109 ms |
| 015 on3 (`rr015_rgtf1_rep3`) | 452, ending 47.6 | 406 ms | 125 ms |

On the first row, recommendations was already fast and retries never left 3. On 010 on2 and 015 on3 the postcheckout cap was in force the whole hold and recommendations sojourn stayed about 406 ms. The same cap did cool checkout.

## TopFull did not see the rejection

TopFull marks a service overloaded when cAdvisor CPU / quota crosses 0.8. It then caps the entry API of the overloaded service that the fewest APIs use. It does not read RetryGuard's rejection rate.

| Hold | recommendations CPU median | ticks above 0.8 | checkout ticks above 0.8 |
|---|---|---|---|
| 010 on2 | 0.661 of 1150 m | 41/662 (6.2%) | 483/662 (73.0%) |
| 015 on3 | 0.673 of 1150 m | 46/662 (6.9%) | 470/662 (71.0%) |

Checkout is on the postcheckout path only. Recommendations is on getproduct, getcart, and the confirmation page. The sustained cut is postcheckout. About half of the short getproduct/getcart caps land within 2 s of a recommendations tick that actually crossed 0.8.

## Why rejection stays high while CPU stays near 0.66

The two numbers are about different resources.

On 010 on2 the pod used about 760 millicores (0.66 × 1150 m) at about 380 req/s. That is about 2 ms of CPU per request. Mean sojourn was 409 ms, so about 155 requests were in flight (`380 × 0.409`). One core serving them at 2 ms each is about 310 ms of waiting. The histogram matches that wait: 10% of requests finish by 250 ms, the median is between 250 and 500 ms, and 77% finish by 500 ms. Rejection is the share still waiting when the 500 ms timeout fires.

`recommendationservice → productcatalogservice` retries were 0, and productcatalog sojourn was 5 ms. The 400 ms is not time inside catalog.

The cool both-on hold 010 on1 ran at the same CPU (median 0.649) and almost the same arrival (about 345 req/s). Sojourn was 49 ms, about 17 requests in flight, and the median was at or under 25 ms. `recommendationservice` is the Python server `recommendation_server.py`, so those threads share one core. At 17 in flight the wait is on the order of `17 × 2 ms`. At 155 in flight it is on the order of `155 × 2 ms`. Same core, same CPU reading, two different waits. The re-enable bar sits on the long one, so recommendations stays at 0 attempts until the hold ends.
