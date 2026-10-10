# RetryGuard Implementation

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Implementation notes for [`experiments/retryguard.py`](../experiments/retryguard.py) (Phase 5 / §6b).  
> Canonical experiment runner context: [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md).  
> Algorithm source of truth: RetryGuard paper, Sec. 4, Algorithm 1 (rejection-based).

---

## Deployment

| Location | Path |
|----------|------|
| Repo | `experiments/retryguard.py` |
| Master VM | `/home/idozacharia/experiments/retryguard.py` (`infra.retryguard_script`) |

```bash
# On master, with TopFull venv active
python3 /home/idozacharia/experiments/retryguard.py --params /tmp/retryguard_params.json
```

The experiment runner uploads params JSON and starts this script in tmux session `retryguard`.

Params JSON (Algorithm 1 knobs from YAML `retryguard:`; attempts/timeout from top-level `retries:`, mapped by `run_scenario.py`):
```json
{
  "rejection_threshold": 0.20,
  "sample_interval_seconds": 1,
  "interval_samples": 30,
  "retry_attempts_on": 3,
  "retry_attempts_off": 0,
  "per_try_timeout_ms": 500
}
```

---

## Algorithm mapping (paper Sec. 4, Algorithm 1)

```
1:  Initialize Consecutive_low ← 0, Consecutive_high ← 0, Retries ← OFF
2:  Set Threshold (parameter) and Interval (parameter)
3:  while true do
4:      Failures ← measure_value()
5:      if Failures < Threshold then
6:          Consecutive_low ← Consecutive_low + 1
7:          Consecutive_high ← 0
8:      else if Failures > Threshold then
9:          Consecutive_high ← Consecutive_high + 1
10:         Consecutive_low ← 0
11:     else
12:         Consecutive_low ← 0; Consecutive_high ← 0
13:     if Consecutive_low ≥ Interval then Retries ← ON
14:     else if Consecutive_high ≥ Interval then Retries ← OFF
```

| Algorithm 1 variable | Our param / behavior |
|----------------------|----------------------|
| `Failures` (`measure_value()`) | Inbound `Δ(5xx + resets) / Δtotal` from the newest unused `service_inbound.csv` row for that service (no averaging; 4xx ignored) |
| Loop cadence (implicit 1 measurement/iteration) | `sample_interval_seconds` (=1, one sample per second) |
| `Threshold` | `rejection_threshold` (e.g. 0.20) |
| `Interval` (lines 13 and 14 — symmetric, same value both directions) | `interval_samples` |
| `Retries ← ON` | Patch VirtualService `retries.attempts` → `retry_attempts_on` |
| `Retries ← OFF` | Disable retries on the VirtualService (see patch note below) |

One controller state machine runs per HTTP Boutique **backend** in `CONTROLLED_SERVICES` (9 services). `frontend` and `redis-cart` are not controlled.

---

## Metric source

Reads `{record_path}/service_inbound.csv` written every 1s by `envoy_retry_collector.py` (same `record_path` as Locust CSVs). Schema: `timestamp, service, total, 2xx, 4xx, 5xx, resets` (cumulative Envoy inbound listener counters).

Per controlled service, RetryGuard keeps the last consumed `(timestamp, total, 5xx, resets)` in memory:

```
Failures = Δ(5xx + resets) / Δtotal     if Δtotal > 0
Failures = 0.0                           if Δtotal <= 0 on a new timestamp
```

Where `resets` = `downstream_rq_rx_reset` from `service_inbound.csv` column `resets`. Rationale: per-try timeout aborts at the outbound Envoy cause `downstream_rq_rx_reset` at the backend inbound, not a 5xx HTTP response (see TOPFULL-ACTIVATION-DIAGNOSIS.md §7b).

A repeated timestamp (collector has not appended yet) is a SKIP — do not feed Algorithm 1. The first row for a service is stored and SKIP'd (cannot difference yet). Missing file / missing service / unreadable row → SKIP. `4xx` is never used. The default `rejection` mode does not read `service_edges.csv` (edge mode does; see below). Old CSVs without a `resets` column are read as `resets=0` (backward compatible).

Locust CSVs remain storefront **outcomes**. They are not the controller input.

---

## Controlled services

```python
CONTROLLED_SERVICES = (
    "adservice",
    "cartservice",
    "checkoutservice",
    "currencyservice",
    "emailservice",
    "paymentservice",
    "productcatalogservice",
    "recommendationservice",
    "shippingservice",
)
```

Excluded: `frontend` (ingress hop; its VS stays `attempts: 3`) and `redis-cart` (TCP, no HTTP inbound 5xx). Patching a service's VirtualService disables retries on **incoming** calls **to** that service (caller sidecars).

---

## VirtualService patch mechanics

- API: `kubernetes.client.CustomObjectsApi`
- Resource: `networking.istio.io/v1alpha3` · plural `virtualservices` · namespace `default`
- Flow: GET existing VS → preserve `spec.http[0].route` → merge-patch the `http` rule
- **Disable (`retry_attempts_off: 0`):** `retries: {attempts: 0}` plus a route `timeout` equal to `per_try_timeout_ms` (500ms). Istio's webhook rejects `attempts: 0` combined with `retryOn` or `perTryTimeout`. Omitting the `retries` block falls back to Istio's default of 2 retries (verified 2026-10-06), so the bare block stays. The route timeout is what still cancels a slow request: with retries off and no timeout, the caller waits and the callee records a 2xx, so rejection stays 0 and re-enable cannot see overload (run13, 2026-10-07). The resulting RST is the same inbound `downstream_rq_rx_reset` the ON path produces via `perTryTimeout`.
- **Re-enable:** restore `retries.attempts` + `retryOn: "5xx,reset,connect-failure"` + `perTryTimeout: "{per_try_timeout_ms}ms"`, and drop the route `timeout` so the request may use every attempt.
- **Why `perTryTimeout`:** our overload produces slow HTTP 2xx responses (queuing in Envoy sidecars), not 5xx. Without a per-try timeout, no retry condition is ever met and the failure signal stays zero. `perTryTimeout: 500ms` (~SLO/attempts) makes a slow upstream call a retriable `reset`-timeout under the `retryOn` policy. The resulting RST is recorded at the backend's inbound Envoy as `downstream_rq_rx_reset` (not 5xx), which is why `measure_value()` uses `Δ(5xx + resets) / Δtotal`. See TOPFULL-ACTIVATION-DIAGNOSIS.md §7b.
- Route is preserved because Istio rejects an http rule with no route
- Patch failures (e.g. VS missing — see PHASE5 guide §6c) are logged as `PATCH_FAIL` and do **not** update internal state
- `run_scenario.py` applies `perTryTimeout` at run start via `apply_per_try_timeout()` (both arms) and re-applies `retries.attempts` + `perTryTimeout` on all Boutique VirtualServices at end of a RetryGuard run, so a kill mid-OFF cannot leave the mesh without retries

---

## Log format

Stdout (tmux session `retryguard`) and `{record_path}/retryguard.log`:

```
2026-08-04T18:30:00Z  START  threshold=0.20 sample_interval=1s interval_samples=30 (30s) services=['adservice', ..., 'shippingservice']
2026-08-04T18:30:01Z  OBSERVE  checkoutservice  rejection=0.3100  low=0 high=1  state=ON
2026-08-04T18:30:02Z  OBSERVE  paymentservice  rejection=0.2200  low=0 high=1  state=ON
2026-08-04T18:30:30Z  cartservice  ON→OFF   rejection=0.31  consecutive_high=30  attempts=0
2026-08-04T18:31:15Z  checkoutservice  OFF→ON   rejection=0.08  consecutive_low=30  attempts=3
```

---

## Startup / shutdown

- Waits up to 60s (poll every 5s) for `service_inbound.csv` to contain at least one data row.
- Handles `SIGTERM`/`SIGINT` (runner uses `pkill -f retryguard.py`) and logs `SHUTDOWN` / `EXIT`

---

## Deviations from the paper pseudocode

1. **Initial state `ON`** — Algorithm 1 initializes `Retries ← OFF`. We start `ON` so the controller matches the default VirtualService (`attempts: 3`) and Scenario 1 (healthy load) produces **zero** patches. Documented in code on `ServiceState.retries_state`.
2. **Mesh inbound `Δ5xx/Δtotal`** matches the paper's Istio experiment (Sec. 6.2): hop-level 5xx on each backend's inbound listener (4xx ignored). `frontend` is intentionally not controlled (ingress hop; its VS stays `attempts: 3`).

As of 2026-09-10, the `Interval` parameter is symmetric (single `interval_samples` value for both ON and OFF transitions, `sample_interval_seconds=1`) — a literal match to Algorithm 1. The previous `disable_windows`/`re_enable_windows` asymmetric split and `window_duration_seconds`-based averaging (a workshop extension) were removed; Scenario 5 now sweeps the single `interval_samples` value (10/20/30/60) symmetrically.

As of 2026-10-08, `interval_samples` is seconds of mesh-row timestamps, not a row count. A streak opens on the first row past the bar and fires when a later row's timestamp is at least that many seconds after the first. One row that misses the bar clears the streak. A skipped row (no new timestamp, or no first attempts) does not count and does not clear it. The log still prints `consecutive_high` / `consecutive_low` as the row count inside the streak, and `elapsed_s` as the timestamp span. Rows already in the file when the process starts are not replayed. At a 1-second scrape this is the paper's 30-second interval; at the current ~2-second scrape a 30-second streak contains about 15 rows.

---

## Edge mode (`retry_metric: edge_rpr`)

Workshop extension of Algorithm 1. The code default stays `retry_metric: rejection` (the loop above). Every YAML that starts RetryGuard sets `retry_metric: edge_rpr` and `retries_threshold: 0.5`. `run_scenario.py` passes both keys; `retries_threshold` is required only when the metric is `edge_rpr`.

What it measures, per controlled caller→callee edge, per 1 s tick:

```
rpr = Δretry / (Δtotal − Δretry)
```

from `service_edges.csv`. That is the paper's normalized retry rate (Λ − λ)/λ: `total` counts every attempt, `retry` counts the retried ones, so the denominator is first attempts. A tick with zero first attempts is skipped and changes no counter. `retries_threshold: 0.5` is our choice, derived from Fig. 7 (knee near ρ≈1.03–1.05) and scaled for `attempts: 3`. The paper does not state a per-edge value.

Disable is per edge. `rpr` above 0.5 for `interval_samples` seconds of row timestamps (Scenario 5's 10/20/30/60 are those seconds) sheds that edge to 0 attempts from whatever count it was on: the callee VirtualService gets a `sourceLabels: {app: <caller>}` route with `retries: {attempts: 0}` and `timeout: {per_try_timeout_ms}ms` ahead of the default route. Other callers keep their own counts. The shed is immediate (3→0, 2→0, or 1→0). There is no step down. The route timeout is only on the 0-attempt rule. Routes at 1, 2, or 3 attempts keep `perTryTimeout` and have no route timeout.

Restore is a ramp, so a recovered edge does not jump straight back to 3. While any edge of a callee is at 0, that callee's inbound rejection rate (`Δ(5xx + resets) / Δtotal`) is the fallback, because rpr is ~0 while retries are off. The 0-attempt route's timeout is what produces those resets when the callee is slow. The 0→1 step uses its own bar, `reenable_rejection` **0.10**, not `rejection_threshold` 0.20: rejection strictly under 0.10 for the quiet time below moves every 0-attempt edge of that callee to **1** attempt (full `retryOn` + `perTryTimeout`), not to 3. A sample at or above 0.10 resets that streak. `rejection_threshold` 0.20 stays the Algorithm 1 bar for rejection mode. An edge that never left 3 keeps its rpr streak. Climbs from 1 and 2 stay on rpr.

From 1 or 2, the edge is watched on rpr again. The climb bars are YAML keys on the scenario, `climb_rpr_1_to_2` and `climb_rpr_2_to_3`. The live scenario files set them to **0.17** and **0.33**, which is the old projection (`rpr_now × 3 / attempts_now`, rounded) at `retries_threshold` 0.5. A YAML that omits the keys still uses that formula. Quiet time at or under the bar for that step adds one attempt. Quiet time above 0.5 sheds to 0. In between, the attempt count holds and both streaks reset. Reaching 3 puts the caller back on the default route. Each edge ramps on its own.

| Step | Condition | Quiet time |
|---|---|---|
| 0 → 1 | inbound rejection under 0.10 | 30 s (`interval_samples`) |
| 1 → 2 | rpr ≤ `climb_rpr_1_to_2` (0.17) | 15 s (`CLIMB_INTERVAL_SECONDS`) |
| 2 → 3 | rpr ≤ `climb_rpr_2_to_3` (0.33) | 15 s (`CLIMB_INTERVAL_SECONDS`) |
| any → 0 (shed) | rpr > 0.5 | 30 s (`interval_samples`) |

The whole ramp from 0 to 3 now takes at least 60 s (was 90 s). The 15 s value is a constant in `retryguard.py`, not a YAML key. The two rpr bars are YAML keys.

`ON→OFF` and `OFF→ON` stay the shed and the 0→1 step, so the toggle parser still matches. `OFF→ON` logs `attempts=1`. Climbs log `1→2` and `2→3` and are not toggle events. The name field is `caller->target` on an edge line and the service name on a rejection line:

```
2026-10-06T20:00:00Z  START  metric=edge_rpr rpr_threshold=0.50 rejection_threshold=0.20 reenable_rejection=0.10 climb_rpr_1_to_2=0.17 climb_rpr_2_to_3=0.33 sample_interval=1s interval_samples=30 edges=14 attempts_on=3
2026-10-06T20:00:01Z  OBSERVE  frontend->recommendationservice  rpr=0.6200  low=0 high=1  attempts=3  state=ON  metric=rpr
2026-10-06T20:00:30Z  frontend->recommendationservice  ON→OFF   rpr=0.62  consecutive_high=30  attempts=0  from_attempts=3  metric=rpr
2026-10-06T20:01:00Z  OBSERVE  recommendationservice  rejection=0.0800  low=1 high=0  state=OFF  metric=rejection
2026-10-06T20:01:30Z  recommendationservice  OFF→ON   rejection=0.08  consecutive_low=30  attempts=1  from_attempts=0  metric=rejection
2026-10-06T20:01:45Z  frontend->recommendationservice  1→2   rpr=0.10  consecutive_low=15  attempts=2  from_attempts=1  metric=rpr
2026-10-06T20:02:00Z  frontend->recommendationservice  2→3   rpr=0.10  consecutive_low=15  attempts=3  from_attempts=2  metric=rpr
```

---

## Prerequisite for live runs

VirtualServices for **all nine** `CONTROLLED_SERVICES` must exist (`experiments/virtual-services.yaml`), not only catalog/checkout/cart (PHASE5 guide §6c) or patches return 404.
