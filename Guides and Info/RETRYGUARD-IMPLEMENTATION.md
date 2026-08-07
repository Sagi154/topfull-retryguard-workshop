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
  "window_duration_seconds": 30,
  "disable_windows": 2,
  "re_enable_windows": 3,
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
| `Failures` (`measure_value()`) | Mean(`Fail / RPS`) over last `window_duration_seconds` CSV rows |
| `Threshold` | `rejection_threshold` (e.g. 0.20) |
| `Interval` (line 13, re-enable) | `re_enable_windows` (asymmetric extension of the paper's single Interval) |
| `Interval` (line 14, disable) | `disable_windows` |
| `Retries ← ON` | Patch VirtualService `retries.attempts` → `retry_attempts_on` |
| `Retries ← OFF` | Disable retries on the VirtualService (see patch note below) |

One controller state machine runs **per K8s service**, not per Locust endpoint.

---

## Metric source

Reads CSVs written every 1s by `metric_collector.py` under `global_config.json` → `record_path`:

```
{record_path}/getcart.csv
{record_path}/getproduct.csv
{record_path}/postcart.csv
{record_path}/postcheckout.csv
{record_path}/emptycart.csv
```

Columns used: `RPS`, `Fail`. Rejection rate for a window = mean(`Fail/RPS`) over the last N rows where N = `window_duration_seconds`. Rows with `RPS == 0` contribute 0 (no load ≠ overload). If a CSV is missing for a window, that service is **skipped** (counters unchanged).

---

## Endpoint → service map

```python
ENDPOINT_SERVICE_MAP = {
    "getproduct":   "productcatalogservice",
    "postcheckout": "checkoutservice",
    "getcart":      "cartservice",
    "postcart":     "cartservice",
    "emptycart":    "cartservice",
}
```

Aggregation: **max** rejection rate across endpoints that map to the same service (conservative — any hot path flags the service).

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
2026-08-04T18:30:00Z  START  threshold=0.20 window=30s ...
2026-08-04T18:30:30Z  OBSERVE  checkoutservice  rejection=0.3100  low=0 high=1  state=ON
2026-08-04T18:33:32Z  cartservice  ON→OFF   rejection=0.31  consecutive_high=2  attempts=0
2026-08-04T18:35:02Z  checkoutservice  OFF→ON   rejection=0.08  consecutive_low=3  attempts=3
```

---

## Startup / shutdown

- Waits up to 60s (poll every 5s) for at least one endpoint CSV before entering the main loop
- Handles `SIGTERM`/`SIGINT` (runner uses `pkill -f retryguard.py`) and logs `SHUTDOWN` / `EXIT`

---

## Deviations from the paper pseudocode

1. **Initial state `ON`** — Algorithm 1 initializes `Retries ← OFF`. We start `ON` so the controller matches the default VirtualService (`attempts: 3`) and Scenario 1 (healthy load) produces **zero** patches. Documented in code on `ServiceState.retries_state`.
2. **Asymmetric Interval** — paper uses one `Interval` for both directions; YAML splits it into `disable_windows` / `re_enable_windows` (workshop extension used by Scenario 5).
3. **Rejection metric from Locust CSVs**, not Istio Prometheus — same signal class as the paper's rejection-based controller; chosen because `metric_collector.py` already writes these files on our stack.

---

## Prerequisite for live runs

VirtualServices for `productcatalogservice`, `checkoutservice`, and `cartservice` must exist (PHASE5 guide §6c) or patches return 404.
