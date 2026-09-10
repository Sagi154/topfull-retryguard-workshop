# RetryGuard Mesh `measure_value()` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch RetryGuard's Algorithm 1 `measure_value()` from Locust `Fail / RPS` (via `ENDPOINT_SERVICE_MAP`) to each controlled service's Envoy inbound rejection rate `Δ5xx / Δtotal` from `service_inbound.csv`.

**Architecture:** `retryguard.py` tails the mesh collector's `service_inbound.csv` (already written every 1 s). Per service it keeps the last consumed `(timestamp, total, 5xx)` in memory, differences against the newest row, and feeds that rate into the unchanged `apply_algorithm1`. One state machine per HTTP Boutique backend VirtualService (9 services). No `frontend`, no `redis-cart`. RetryGuard does not scrape Envoy.

**Tech Stack:** Python 3 stdlib `unittest` (no pytest), kubernetes client stubbed in tests as today. Branch: **`retryguard-paper-fidelity`** (already checked out — do not create a new branch).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-10-retryguard-mesh-measure-value-design.md`. Follow it literally.
- Work **only** on branch `retryguard-paper-fidelity`.
- Formula: `Failures = Δ5xx / Δtotal` if `Δtotal > 0`, else `0.0` when `Δtotal <= 0` on a **new** timestamp. Do **not** use `4xx`. Do **not** use Locust `Fail` / `RPS`. Do **not** use `service_edges.csv`.
- No double-count: if there is no newer `timestamp` for that service, return `None` (caller SKIPs). First row ever → store, return `None`.
- `CONTROLLED_SERVICES` is exactly: `adservice`, `cartservice`, `checkoutservice`, `currencyservice`, `emailservice`, `paymentservice`, `productcatalogservice`, `recommendationservice`, `shippingservice`. Must include `paymentservice`. Must exclude `frontend` and `redis-cart`.
- Do not change `apply_algorithm1`, `REQUIRED_PARAMS`, scenario YAML RetryGuard keys, or `mentor_charts.py`.
- Do not touch `experiments/results/campaign_48/` or `experiments/results/august_38/`.
- Do not rewrite historical/checklist docs (`PHASE5-PHASE6-RUNLIST.md`, `PHASE7-DATA-GAPS.md`, `EXPERIMENT-READINESS-WORKPLAN.md`, `SETUP-GUIDE.md`).
- Test runner: `python -m unittest experiments.test_retryguard -v` (and `experiments.test_run_scenario` if you touch the runner — you should not need to).
- `kubernetes` is not installed locally; keep the existing `sys.modules` stub at the top of `experiments/test_retryguard.py`.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `experiments/retryguard.py` | Replace Locust reader + 3-service map with inbound Δ reader + `CONTROLLED_SERVICES`; wire `run()` / startup wait |
| `experiments/test_retryguard.py` | Replace Locust reader tests with inbound / allow-list / wait tests; keep Algorithm 1 + params tests |
| `Guides and Info/RETRYGUARD-IMPLEMENTATION.md` | Canonical mapping: mesh inbound as `measure_value()` |
| `Guides and Info/PER-SERVICE-METRICS.md` | RetryGuard now *does* measure at the service (inbound); Locust stays storefront outcome |
| `Guides and Info/METRICS-GATHERED.md` | Layer 3 + the “RetryGuard uses Fail/RPS” sentence |
| `Guides and Info/METRICS-COLLECTION-GUIDE.md` | RetryGuard log section: 1 s samples, 9 services, inbound source |
| `AGENTS.md` | §4 status bullet once the code lands (mentor_charts follow-up is already written) |

`run_scenario.py` and scenario YAMLs do **not** change (params JSON is unchanged; collector already writes `service_inbound.csv`).

---

## Locked interfaces (every later task uses these names)

```python
INBOUND_CSV_NAME = "service_inbound.csv"

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

@dataclass(frozen=True)
class InboundSnapshot:
    timestamp: str
    total: float
    five_xx: float

def read_latest_inbound_row(csv_path: Path, service: str) -> Optional[InboundSnapshot]:
    """Newest row for `service` in service_inbound.csv, or None."""

def measure_inbound_rejection(
    previous: Optional[InboundSnapshot],
    current: Optional[InboundSnapshot],
) -> tuple[Optional[float], Optional[InboundSnapshot]]:
    """
    One paper measure_value() step.
    Returns (rate_or_None, new_previous).
    None rate => caller SKIPs (do not call apply_algorithm1).
    """

def wait_for_inbound_csv(
    record_path: Path,
    timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
    poll_seconds: float = STARTUP_POLL_SECONDS,
) -> None:
    """Block until service_inbound.csv exists and has ≥1 data row."""
```

`measure_inbound_rejection` rules:

1. `current is None` → `(None, previous)`
2. `previous is None` → `(None, current)` — first row, store, cannot difference
3. `current.timestamp <= previous.timestamp` → `(None, previous)` — no new poll
4. else compute `delta_total = current.total - previous.total`, `delta_5xx = current.five_xx - previous.five_xx`
   - `delta_total <= 0` → `(0.0, current)`
   - else → `(delta_5xx / delta_total, current)`

---

### Task 1: Failing tests for inbound `measure_value()` and the 9-service allow-list

**Files:**
- Modify: `experiments/test_retryguard.py`
- Read (no code changes yet): `experiments/retryguard.py`

**Interfaces:**
- Consumes: existing kubernetes stub + `import retryguard` at the top of the test file (leave those as they are).
- Produces: failing tests that define the locked interfaces above. `TestApplyAlgorithm1Symmetric` and `TestLoadParamsRequiredKeys` stay.

- [ ] **Step 1: Replace the Locust helper and the two Locust test classes**

Delete `_write_csv`, `TestReadRejectionRateSingleSample`, and `TestServiceRejectionRateSingleSample`. Insert this helper and these classes **above** `TestApplyAlgorithm1Symmetric` (leave Algorithm 1 / params tests untouched):

```python
INBOUND_FIELDS = ["timestamp", "service", "total", "2xx", "4xx", "5xx"]


def _write_inbound(path: Path, rows):
    """rows: iterable of dicts with INBOUND_FIELDS keys."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INBOUND_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _row(ts, service, total, five_xx, four_xx=0, two_xx=0):
    return {
        "timestamp": ts,
        "service": service,
        "total": total,
        "2xx": two_xx,
        "4xx": four_xx,
        "5xx": five_xx,
    }


class TestControlledServices(unittest.TestCase):
    def test_includes_paymentservice_and_the_eight_other_backends(self):
        expected = (
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
        self.assertEqual(retryguard.CONTROLLED_SERVICES, expected)

    def test_excludes_frontend_and_redis_cart(self):
        self.assertNotIn("frontend", retryguard.CONTROLLED_SERVICES)
        self.assertNotIn("redis-cart", retryguard.CONTROLLED_SERVICES)


class TestReadLatestInboundRow(unittest.TestCase):
    def test_returns_newest_row_for_that_service_only(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [
                    _row("2026-09-10T18:30:01Z", "checkoutservice", 100, 10),
                    _row("2026-09-10T18:30:01Z", "paymentservice", 50, 40),
                    _row("2026-09-10T18:30:02Z", "checkoutservice", 180, 40),
                ],
            )
            snap = retryguard.read_latest_inbound_row(path, "checkoutservice")
            self.assertEqual(snap.timestamp, "2026-09-10T18:30:02Z")
            self.assertEqual(snap.total, 180.0)
            self.assertEqual(snap.five_xx, 40.0)

    def test_missing_file_returns_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            self.assertIsNone(
                retryguard.read_latest_inbound_row(path, "checkoutservice")
            )

    def test_service_absent_from_file_returns_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path, [_row("2026-09-10T18:30:01Z", "cartservice", 10, 0)]
            )
            self.assertIsNone(
                retryguard.read_latest_inbound_row(path, "paymentservice")
            )


class TestMeasureInboundRejection(unittest.TestCase):
    def test_delta_5xx_over_delta_total(self):
        prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        curr = retryguard.InboundSnapshot("2026-09-10T18:30:02Z", 200.0, 30.0)
        rate, new_prev = retryguard.measure_inbound_rejection(prev, curr)
        self.assertAlmostEqual(rate, 0.20)
        self.assertEqual(new_prev, curr)

    def test_zero_delta_total_is_zero_not_none(self):
        prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        curr = retryguard.InboundSnapshot("2026-09-10T18:30:02Z", 100.0, 10.0)
        rate, new_prev = retryguard.measure_inbound_rejection(prev, curr)
        self.assertEqual(rate, 0.0)
        self.assertEqual(new_prev, curr)

    def test_same_timestamp_does_not_double_count(self):
        prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        curr = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        rate, new_prev = retryguard.measure_inbound_rejection(prev, curr)
        self.assertIsNone(rate)
        self.assertEqual(new_prev, prev)

    def test_first_row_stores_and_skips(self):
        curr = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        rate, new_prev = retryguard.measure_inbound_rejection(None, curr)
        self.assertIsNone(rate)
        self.assertEqual(new_prev, curr)

    def test_missing_current_skips_and_keeps_previous(self):
        prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        rate, new_prev = retryguard.measure_inbound_rejection(prev, None)
        self.assertIsNone(rate)
        self.assertEqual(new_prev, prev)

    def test_four_xx_does_not_enter_the_formula(self):
        """4xx lives on the CSV row but must not affect Failures."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [
                    _row("2026-09-10T18:30:01Z", "paymentservice", 100, 0, four_xx=50),
                    _row("2026-09-10T18:30:02Z", "paymentservice", 200, 0, four_xx=90),
                ],
            )
            first = retryguard.read_latest_inbound_row(path, "paymentservice")
            # After only the latest row exists in-file, reconstruct the
            # previous snapshot the controller would have stored at t1.
            prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 0.0)
            rate, _ = retryguard.measure_inbound_rejection(prev, first)
            self.assertEqual(rate, 0.0)
```

- [ ] **Step 2: Run the new tests and confirm they fail**

```powershell
python -m unittest experiments.test_retryguard -v
```

Expected: `AttributeError` (no `CONTROLLED_SERVICES` / `InboundSnapshot` / `read_latest_inbound_row` / `measure_inbound_rejection`). Algorithm 1 and params tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add experiments/test_retryguard.py
git commit -m "test: fail inbound measure_value and 9-service allow-list"
```

---

### Task 2: Implement inbound reader + allow-list (make Task 1 green)

**Files:**
- Modify: `experiments/retryguard.py`

**Interfaces:**
- Consumes: Task 1 test signatures.
- Produces: `INBOUND_CSV_NAME`, `CONTROLLED_SERVICES`, `InboundSnapshot`, `read_latest_inbound_row`, `measure_inbound_rejection` as locked above. Leave `run()` / `ENDPOINT_SERVICE_MAP` / Locust readers in place until Task 3 (intermediate unused new API is OK).

- [ ] **Step 1: Add the dataclass import if needed and the new constants / types / functions**

In `experiments/retryguard.py`, keep `from dataclasses import dataclass` (already present). Add `Tuple` only if you do not use `tuple[...]` (the file already has `from __future__ import annotations` — use `tuple[Optional[float], Optional[InboundSnapshot]]`).

Replace the Locust map comment block's *neighbors* by **inserting after** `ENDPOINT_SERVICE_MAP` (do not delete the map yet):

```python
INBOUND_CSV_NAME = "service_inbound.csv"

# HTTP Boutique callees that already have a VirtualService.
# frontend (ingress) and redis-cart (TCP) are excluded — see the
# 2026-09-10 mesh measure_value spec.
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

Add, after `ServiceState`:

```python
@dataclass(frozen=True)
class InboundSnapshot:
    timestamp: str
    total: float
    five_xx: float
```

Add these two functions in the Metric reading section (keep the old Locust functions until Task 3):

```python
def read_latest_inbound_row(csv_path: Path, service: str) -> Optional[InboundSnapshot]:
    if not csv_path.is_file():
        return None
    try:
        with open(csv_path, "r", newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None
    latest = None
    for row in rows:
        if row.get("service") != service:
            continue
        try:
            latest = InboundSnapshot(
                timestamp=str(row["timestamp"]),
                total=float(row["total"]),
                five_xx=float(row["5xx"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
    return latest


def measure_inbound_rejection(
    previous: Optional[InboundSnapshot],
    current: Optional[InboundSnapshot],
) -> tuple[Optional[float], Optional[InboundSnapshot]]:
    if current is None:
        return None, previous
    if previous is None:
        return None, current
    if current.timestamp <= previous.timestamp:
        return None, previous
    delta_total = current.total - previous.total
    delta_5xx = current.five_xx - previous.five_xx
    if delta_total <= 0:
        return 0.0, current
    return delta_5xx / delta_total, current
```

- [ ] **Step 2: Run tests**

```powershell
python -m unittest experiments.test_retryguard -v
```

Expected: all tests PASS (including the new inbound ones).

- [ ] **Step 3: Commit**

```powershell
git add experiments/retryguard.py
git commit -m "feat: read mesh inbound Δ5xx/Δtotal for measure_value"
```

---

### Task 3: Wire `run()` to inbound; drop Locust map and readers

**Files:**
- Modify: `experiments/retryguard.py`
- Modify: `experiments/test_retryguard.py`

**Interfaces:**
- Consumes: Task 2 functions + `CONTROLLED_SERVICES`.
- Produces: `wait_for_inbound_csv(...)` as locked above. `run()` iterates `CONTROLLED_SERVICES`, never opens Locust `*.csv`. `ENDPOINT_SERVICE_MAP`, `service_endpoint_map`, `read_rejection_rate`, `service_rejection_rate`, and `wait_for_csvs` are **gone**.

- [ ] **Step 1: Add failing tests for wait + for the deleted Locust API**

Append to `experiments/test_retryguard.py`:

```python
class TestWaitForInboundCsv(unittest.TestCase):
    def test_returns_immediately_when_file_has_a_data_row(self):
        with TemporaryDirectory() as tmp:
            record_path = Path(tmp)
            _write_inbound(
                record_path / retryguard.INBOUND_CSV_NAME,
                [_row("2026-09-10T18:30:01Z", "checkoutservice", 10, 1)],
            )
            retryguard.wait_for_inbound_csv(
                record_path, timeout_seconds=0.2, poll_seconds=0.05
            )

    def test_times_out_when_file_missing(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                retryguard.wait_for_inbound_csv(
                    Path(tmp), timeout_seconds=0.15, poll_seconds=0.05
                )


class TestLocustReaderRemoved(unittest.TestCase):
    def test_locust_helpers_and_endpoint_map_are_gone(self):
        self.assertFalse(hasattr(retryguard, "ENDPOINT_SERVICE_MAP"))
        self.assertFalse(hasattr(retryguard, "read_rejection_rate"))
        self.assertFalse(hasattr(retryguard, "service_rejection_rate"))
        self.assertFalse(hasattr(retryguard, "service_endpoint_map"))
        self.assertFalse(hasattr(retryguard, "wait_for_csvs"))
```

- [ ] **Step 2: Run to confirm RED**

```powershell
python -m unittest experiments.TestWaitForInboundCsv experiments.TestLocustReaderRemoved -v
```

If that module path fails, run:

```powershell
python -m unittest experiments.test_retryguard.TestWaitForInboundCsv experiments.test_retryguard.TestLocustReaderRemoved -v
```

Expected: `AttributeError` (`wait_for_inbound_csv` missing) and/or `test_locust_helpers_and_endpoint_map_are_gone` FAIL because the old names still exist.

- [ ] **Step 3: Implement `wait_for_inbound_csv` and rewrite `run()`**

Replace `wait_for_csvs` with:

```python
def wait_for_inbound_csv(
    record_path: Path,
    timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
    poll_seconds: float = STARTUP_POLL_SECONDS,
) -> None:
    """Poll until service_inbound.csv exists and has ≥1 data row."""
    deadline = time.time() + timeout_seconds
    csv_path = record_path / INBOUND_CSV_NAME
    log.info(
        "%s  WAITING  for %s (timeout=%ss)",
        utc_now(),
        csv_path,
        timeout_seconds,
    )
    while time.time() < deadline:
        if _shutdown:
            raise SystemExit(0)
        if csv_path.is_file():
            try:
                with open(csv_path, "r", newline="") as f:
                    rows = list(csv.DictReader(f))
            except OSError:
                rows = []
            if rows:
                log.info("%s  READY  found %s (%d rows)", utc_now(), INBOUND_CSV_NAME, len(rows))
                return
        time.sleep(poll_seconds)
    raise SystemExit(
        f"[retryguard] ERROR: no data in {csv_path} "
        f"after {timeout_seconds}s — is envoy_retry_collector running?"
    )
```

Rewrite `run()` so the loop uses inbound (keep patch / OBSERVE / PATCH_FAIL logging the same). Exact replacement for the start of `run()` through the per-service `rejection = ...` block:

```python
def run(params: dict, record_path: Path, api: client.CustomObjectsApi) -> None:
    sample_interval = int(params["sample_interval_seconds"])
    interval = int(params["interval_samples"])
    threshold = float(params["rejection_threshold"])
    attempts_on = int(params["retry_attempts_on"])
    attempts_off = int(params["retry_attempts_off"])

    wait_for_inbound_csv(record_path)

    states = {svc: ServiceState() for svc in CONTROLLED_SERVICES}
    previous: Dict[str, Optional[InboundSnapshot]] = {
        svc: None for svc in CONTROLLED_SERVICES
    }
    inbound_path = record_path / INBOUND_CSV_NAME
    log.info(
        "%s  START  threshold=%.2f sample_interval=%ss interval_samples=%d "
        "(%ds) services=%s",
        utc_now(),
        threshold,
        sample_interval,
        interval,
        sample_interval * interval,
        list(CONTROLLED_SERVICES),
    )

    while not _shutdown:
        time.sleep(sample_interval)
        if _shutdown:
            break

        for service in CONTROLLED_SERVICES:
            current = read_latest_inbound_row(inbound_path, service)
            rejection, previous[service] = measure_inbound_rejection(
                previous[service], current
            )
            if rejection is None:
                log.info(
                    "%s  SKIP  %s  no metric data this sample",
                    utc_now(),
                    service,
                )
                continue
            # ... existing apply_algorithm1 / OBSERVE / patch block unchanged,
            #     still using `state = states[service]` etc.
```

Keep the rest of the loop (Algorithm 1, OBSERVE, patch, PATCH_FAIL) as it is today.

Then **delete** `ENDPOINT_SERVICE_MAP`, `service_endpoint_map`, `read_rejection_rate`, and `service_rejection_rate`. If `defaultdict` is unused after that, drop `from collections import defaultdict`.

Update the module docstring to say it reads `{record_path}/service_inbound.csv` (`Δ5xx / Δtotal` per service), not Locust endpoint CSVs.

- [ ] **Step 4: Run the full RetryGuard suite**

```powershell
python -m unittest experiments.test_retryguard -v
```

Expected: all tests PASS.

- [ ] **Step 5: Confirm retryguard.py no longer mentions Locust CSVs as a source**

```powershell
Select-String -Path experiments\retryguard.py -Pattern "getproduct|ENDPOINT_SERVICE_MAP|read_rejection_rate|Fail / RPS"
```

Expected: no matches (docstring/comments must not still describe Locust as the metric source).

- [ ] **Step 6: Commit**

```powershell
git add experiments/retryguard.py experiments/test_retryguard.py
git commit -m "feat: drive RetryGuard from service_inbound.csv per backend"
```

---

### Task 4: Update `RETRYGUARD-IMPLEMENTATION.md`

**Files:**
- Modify: `Guides and Info/RETRYGUARD-IMPLEMENTATION.md`

**Interfaces:** none (docs).

- [ ] **Step 1: Apply these replacements**

Algorithm mapping table — change the `Failures` row to:

```
| `Failures` (`measure_value()`) | Inbound `Δ5xx / Δtotal` from the newest unused `service_inbound.csv` row for that service (no averaging; 4xx ignored) |
```

Change “One controller state machine runs **per K8s service**, not per Locust endpoint.” to:

```
One controller state machine runs per HTTP Boutique **backend** in `CONTROLLED_SERVICES` (9 services). `frontend` and `redis-cart` are not controlled.
```

Replace the entire **Metric source** and **Endpoint → service map** sections with:

```markdown
## Metric source

Reads `{record_path}/service_inbound.csv` written every 1s by `envoy_retry_collector.py` (same `record_path` as Locust CSVs). Schema: `timestamp, service, total, 2xx, 4xx, 5xx` (cumulative Envoy inbound listener counters).

Per controlled service, RetryGuard keeps the last consumed `(timestamp, total, 5xx)` in memory:

```
Failures = Δ5xx / Δtotal     if Δtotal > 0
Failures = 0.0               if Δtotal <= 0 on a new timestamp
```

A repeated timestamp (collector has not appended yet) is a SKIP — do not feed Algorithm 1. The first row for a service is stored and SKIP'd (cannot difference yet). Missing file / missing service / unreadable row → SKIP. `4xx` is never used. `service_edges.csv` is never used.

Locust CSVs remain storefront **outcomes**. They are not the controller input.

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
```

Startup / shutdown bullet: “Waits up to 60s (poll every 5s) for `service_inbound.csv` to contain at least one data row.”

Deviation #2 — replace with:

```
2. **Initial `ON`** is still the only Algorithm 1 deviation (paper initializes `OFF`). The rejection signal is mesh inbound `Δ5xx/Δtotal`, matching the paper's Istio experiment (Sec. 6.2). `frontend` is intentionally not controlled.
```

(Keep deviation #1 as the initial-state `ON` note — do not duplicate it. If #1 already covers initial ON, make #2 only about frontend exclusion / hop-level 5xx, not a second “initial ON”.)

Prerequisite: VirtualServices for **all nine** `CONTROLLED_SERVICES` must exist (`experiments/virtual-services.yaml`), not only catalog/checkout/cart.

Log example `START` line: list can show the 9 names or `services=['adservice', ..., 'shippingservice']`. Toggle examples may keep checkout; add one `paymentservice` OBSERVE line so S4B is visible.

- [ ] **Step 2: Commit**

```powershell
git add "Guides and Info/RETRYGUARD-IMPLEMENTATION.md"
git commit -m "docs: RetryGuard measure_value is mesh inbound Δ5xx/Δtotal"
```

---

### Task 5: Update metrics guides (decision source vs outcomes)

**Files:**
- Modify: `Guides and Info/PER-SERVICE-METRICS.md`
- Modify: `Guides and Info/METRICS-GATHERED.md`
- Modify: `Guides and Info/METRICS-COLLECTION-GUIDE.md`

**Interfaces:** none (docs).

- [ ] **Step 1: `PER-SERVICE-METRICS.md`**

In the “what we already have” table, change the RetryGuard grain from `cart, checkout, catalog` to `9 HTTP backends (not frontend / redis-cart)`.

Replace this paragraph:

```
RetryGuard’s “per-service rejection” is **not** measured at the service. It is Locust `Fail/RPS` on `getproduct` / `postcheckout` / cart APIs, then mapped with `ENDPOINT_SERVICE_MAP`. That is the mismatch: Layer 1 CSVs answer “did this **storefront action** fail?”, not “did **this pod** fail?”
```

with:

```
RetryGuard’s **decision** signal is Envoy inbound `Δ5xx / Δtotal` from `service_inbound.csv` (one Algorithm 1 loop per HTTP backend except `frontend`). Locust `Fail/RPS` is still the **storefront outcome**, not the controller input. Mesh inbound / edges / CPU remain per-service outcomes and insights — see the practical-split table below. `mentor_charts.py` still plots Locust only; wiring mesh into charts is a follow-up, not a claim that mesh is not an outcome.
```

Leave the “So you want both” / practical-split table; it is still correct (Locust = users, Envoy inbound = which service).

- [ ] **Step 2: `METRICS-GATHERED.md`**

Change the sentence under Layer 1 columns:

```
Rejection rate is **not a stored column**. Analysis derives it as `Fail / RPS` (0 when `RPS == 0`). RetryGuard uses the same formula.
```

to:

```
Rejection rate is **not a stored column**. Analysis derives storefront rejection as `Fail / RPS` (0 when `RPS == 0`). RetryGuard does **not** use this; it uses inbound `Δ5xx / Δtotal` from `service_inbound.csv` (see Layer 3).
```

Replace the Layer 3 body (keep the log-keyword table) with:

```
RetryGuard reads `{record_path}/service_inbound.csv` every 1 s. For each of the 9 `CONTROLLED_SERVICES` it computes inbound `Δ5xx / Δtotal` against the last consumed poll (SKIP if no newer timestamp). That rate is Algorithm 1 `measure_value()`. Locust CSVs are not opened.

It controls nine HTTP backends (including `paymentservice`). It does not patch `frontend` or `redis-cart`.

Default: disable after 30 consecutive 1 s samples ≥ 20% inbound 5xx; re-enable after 30 consecutive samples below 20% (Scenario 5 sweeps `interval_samples` 10/20/30/60).
```

- [ ] **Step 3: `METRICS-COLLECTION-GUIDE.md` RetryGuard log section**

Change the `OBSERVE` / `SKIP` table wording from “30s window” / “No CSV data … this window” to “each 1 s sample” / “no new inbound row this tick”.

Replace the example `START` services list with the 9-name `CONTROLLED_SERVICES` list (or a shortened `services=[adservice, …, shippingservice]`).

Replace the “Reading an ON→OFF” bullets that say “2 consecutive windows (≥60s)” with “`interval_samples` consecutive 1 s inbound samples (default 30)”.

- [ ] **Step 4: Commit**

```powershell
git add "Guides and Info/PER-SERVICE-METRICS.md" "Guides and Info/METRICS-GATHERED.md" "Guides and Info/METRICS-COLLECTION-GUIDE.md"
git commit -m "docs: RetryGuard decisions come from mesh inbound, not Locust"
```

---

### Task 6: `AGENTS.md` status + leftover-string sweep

**Files:**
- Modify: `AGENTS.md`

**Interfaces:** none.

- [ ] **Step 1: Add a dated §4 Done bullet** (after the existing 2026-09-10 paper-exact Interval bullet). Do **not** remove the mentor_charts follow-up already in §4 / remaining work.

```
- **RetryGuard `measure_value()` is mesh inbound (2026-09-10)** — `experiments/retryguard.py` now reads `service_inbound.csv` (`Δ5xx / Δtotal`, no 4xx, no double-count) for the 9 HTTP backends in `CONTROLLED_SERVICES` (includes `paymentservice`; excludes `frontend` / `redis-cart`). Locust CSVs are storefront outcomes only. Spec: `docs/superpowers/specs/2026-09-10-retryguard-mesh-measure-value-design.md`. `campaign_48/` predates this (Locust-driven) and stays historical. `mentor_charts.py` still only knows Locust; wiring mesh into plots remains a follow-up — mesh is still an intended per-service outcome.
```

In remaining work, remove or shorten the “specified and planned; not implemented yet” paragraph (it will be implemented). **Keep** the “Chart follow-up (do eventually)” paragraph verbatim.

- [ ] **Step 2: Sweep live code/docs for leftover Locust-as-controller text**

```powershell
Select-String -Path experiments\retryguard.py,experiments\test_retryguard.py,AGENTS.md,"Guides and Info\RETRYGUARD-IMPLEMENTATION.md","Guides and Info\PER-SERVICE-METRICS.md","Guides and Info\METRICS-GATHERED.md","Guides and Info\METRICS-COLLECTION-GUIDE.md" -Pattern "ENDPOINT_SERVICE_MAP|read_rejection_rate|service_rejection_rate"
```

Expected: no hits in those live files. Historical docs (`EXPERIMENT-READINESS-WORKPLAN.md`, campaign READMEs) may still mention the old map — leave them.

```powershell
python -m unittest experiments.test_retryguard experiments.test_run_scenario -v
```

Expected: both suites PASS (`test_run_scenario` must still pass — this plan does not change the runner).

- [ ] **Step 3: Commit**

```powershell
git add AGENTS.md
git commit -m "docs: record mesh inbound measure_value in AGENTS.md"
```

---

## Self-review (spec coverage)

| Spec requirement | Task |
|---|---|
| `Δ5xx / Δtotal`, no averaging, no 4xx | 1–2 |
| No double-count / first-row SKIP / missing → None | 1–2 |
| `CONTROLLED_SERVICES` = 9 backends; no frontend / redis-cart; includes payment | 1–3 |
| `run()` reads only `service_inbound.csv`; startup wait | 3 |
| Delete Locust map/readers | 3 |
| `apply_algorithm1` / YAML params / mentor_charts unchanged | global + Task 6 runner test |
| RETRYGUARD-IMPLEMENTATION, PER-SERVICE-METRICS, METRICS-GATHERED, AGENTS | 4–6 |
| METRICS-COLLECTION-GUIDE decision-metric wording | 5 |
| No campaign backfill | global |
| Locust remains storefront outcome; mesh remains per-service outcome | 4–6 + existing AGENTS chart follow-up |
