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

Params JSON (from the YAML `retryguard:` block):
```json
{
  "rejection_threshold": 0.20,
  "sample_interval_seconds": 1,
  "interval_samples": 30,
  "retry_attempts_on": 3,
  "retry_attempts_off": 0
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
| `Failures` (`measure_value()`) | Inbound `Δ5xx / Δtotal` from the newest unused `service_inbound.csv` row for that service (no averaging; 4xx ignored) |
| Loop cadence (implicit 1 measurement/iteration) | `sample_interval_seconds` (=1, one sample per second) |
| `Threshold` | `rejection_threshold` (e.g. 0.20) |
| `Interval` (lines 13 and 14 — symmetric, same value both directions) | `interval_samples` |
| `Retries ← ON` | Patch VirtualService `retries.attempts` → `retry_attempts_on` |
| `Retries ← OFF` | Disable retries on the VirtualService (see patch note below) |

One controller state machine runs per HTTP Boutique **backend** in `CONTROLLED_SERVICES` (9 services). `frontend` and `redis-cart` are not controlled.

---

## Metric source

Reads `{record_path}/service_inbound.csv` written every 1s by `envoy_retry_collector.py` (same `record_path` as Locust CSVs). Schema: `timestamp, service, total, 2xx, 4xx, 5xx` (cumulative Envoy inbound listener counters).

Per controlled service, RetryGuard keeps the last consumed `(timestamp, total, 5xx)` in memory:

```
Failures = Δ5xx / Δtotal     if Δtotal > 0
Failures = 0.0               if Δtotal <= 0 on a new timestamp
```

A repeated timestamp (collector has not appended yet) is a SKIP — do not feed Algorithm 1. The first row for a service is stored and SKIP'd (cannot difference yet). Missing file / missing service / unreadable row → SKIP. `4xx` is never used. `service_edges.csv` is never used.

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
- **Disable (`retry_attempts_off: 0`):** omit the `retries` block entirely. Istio's validation webhook rejects `retries.attempts: 0` while `retryOn` (or any retry policy) is still present (`http retry policy configured when attempts are set to 0`). Merge-patch replaces the `http` array, so omitting `retries` drops it.
- **Re-enable:** restore `retries.attempts` + `retryOn: "5xx,reset,connect-failure"`
- Route is preserved because Istio rejects an http rule with no route
- Patch failures (e.g. VS missing — see PHASE5 guide §6c) are logged as `PATCH_FAIL` and do **not** update internal state
- `run_scenario.py` also re-applies `retries.attempts=3` on all Boutique VirtualServices at end of a RetryGuard run, so a kill mid-OFF cannot leave the mesh without retries

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

---

## Prerequisite for live runs

VirtualServices for **all nine** `CONTROLLED_SERVICES` must exist (`experiments/virtual-services.yaml`), not only catalog/checkout/cart (PHASE5 guide §6c) or patches return 404.
