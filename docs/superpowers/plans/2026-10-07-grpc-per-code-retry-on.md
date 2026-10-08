# gRPC Per-Code Columns and Per-Callee retryOn Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store completed gRPC failures per status code, retry on `unavailable` and `deadline-exceeded` for the four read-only callees, and make those callees' rejection rate count the same two codes.

**Architecture:** The collector writes one column per gRPC status (2, 4, 13, 14) in place of the lumped `grpc_5xx`. `retryguard.py` owns the retry string and the list of callees that get the extra tokens; the rejection rate adds `grpc_4 + grpc_14` for exactly those callees. `run_scenario.py` patches VirtualServices at run start, so it gets the same per-callee string. Every callee keeps a single route rule.

**Tech Stack:** Python 3, `unittest`, Istio VirtualService, Envoy 1.25 sidecars.

## Global Constraints

- Retry-token callees: `adservice`, `currencyservice`, `productcatalogservice`, `recommendationservice`. All other callees keep `5xx,reset,connect-failure`.
- New tokens: `unavailable,deadline-exceeded`. Not `internal`. `UNKNOWN` (2) and `INTERNAL` (13) are recorded but counted nowhere.
- `cartservice` and `shippingservice` stay on `5xx,reset,connect-failure`, same as checkout, payment, and email. No method-matched routes. Their rejection rate stays `(Δ5xx + Δresets) / Δtotal`, so the rate and the retry string still count the same failures.
- `retryguard.py` and `envoy_retry_collector.py` are deployed to the master as single files. Do not add a shared module they would both need.
- `rejection = (Δ5xx + Δresets [+ Δgrpc_4 + Δgrpc_14]) / Δtotal`. The bracket applies only to the four callees.
- Do not touch `experiments/results/`. Old result folders keep their lumped `grpc_5xx` column.

---

### Task 1: Collector writes gRPC failures per status code

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (lines ~116-123, ~162-164, `parse_inbound`, `count_destination_grpc_5xx`, `write_inbound_csv`)
- Test: `experiments/test_envoy_retry_collector.py` (lines ~96, ~113, ~129-157, ~348-349)

**Interfaces:**
- Produces: `GRPC_COLUMNS = ("grpc_2", "grpc_4", "grpc_13", "grpc_14")`; `count_destination_grpc_status(stats_text: str) -> Dict[str, int]` keyed by those column names; `parse_inbound` returns all four keys; `service_inbound.csv` ends with those four columns and no `grpc_5xx`.

- [ ] **Step 1: Update the tests first**

In `test_envoy_retry_collector.py`:

Replace `self.assertEqual(inbound["grpc_5xx"], 0)` (line ~96) with:

```python
        for col in ("grpc_2", "grpc_4", "grpc_13", "grpc_14"):
            self.assertEqual(inbound[col], 0)
```

In `test_no_inbound_lines_returns_zeros`, replace `"grpc_5xx": 0,` in the expected dict with `"grpc_2": 0, "grpc_4": 0, "grpc_13": 0, "grpc_14": 0,`.

Rename `class TestDestinationGrpc5xx` to `class TestDestinationGrpcStatus`. In `test_sums_completed_grpc_failures_only` replace the assertion `self.assertEqual(inbound["grpc_5xx"], 50)` with:

```python
        self.assertEqual(
            (inbound["grpc_2"], inbound["grpc_4"], inbound["grpc_13"], inbound["grpc_14"]),
            (5, 40, 3, 2),
        )
```

In `test_sums_across_pods`, replace each `"grpc_5xx": 4` / `"grpc_5xx": 6` with `"grpc_4": 4, "grpc_2": 0, "grpc_13": 0, "grpc_14": 0` / `"grpc_4": 6, "grpc_2": 0, "grpc_13": 0, "grpc_14": 0`, and the assertion with `self.assertEqual(summed["grpc_4"], 10)`.

In the `write_inbound_csv` test (lines ~348-349) replace the last two assertions with:

```python
            self.assertEqual(rows[0]["grpc_4"], "0")
            self.assertEqual(
                list(rows[0].keys())[-4:], ["grpc_2", "grpc_4", "grpc_13", "grpc_14"]
            )
            self.assertNotIn("grpc_5xx", rows[0])
```

- [ ] **Step 2: Run to confirm they fail**

Run: `python -m unittest experiments.test_envoy_retry_collector -v`
Expected: FAIL (KeyError `grpc_4` and similar).

- [ ] **Step 3: Implement**

In `envoy_retry_collector.py`, replace the `grpc_5xx` pieces:

```python
# Completed gRPC failures that Envoy still counts as HTTP 200, one column per
# status. Codes are UNKNOWN (2), DEADLINE_EXCEEDED (4), INTERNAL (13),
# UNAVAILABLE (14). retryguard.py reads grpc_4 and grpc_14 for some callees.
GRPC_FAILURE_CODES = ("2", "4", "13", "14")
GRPC_COLUMNS = tuple(f"grpc_{c}" for c in GRPC_FAILURE_CODES)

INBOUND_METRICS = (
    "total", "2xx", "4xx", "5xx", "resets", "rq_time_sum_ms", "rq_time_count",
) + GRPC_COLUMNS
```

Delete `GRPC_5XX_STATUSES`. Change `INBOUND_CSV_COLUMNS`:

```python
INBOUND_CSV_COLUMNS = [
    "timestamp", "service", "total", "2xx", "4xx", "5xx", "resets",
    "rq_time_sum_ms", "rq_time_count", "rq_time_buckets",
] + list(GRPC_COLUMNS)
```

Replace `count_destination_grpc_5xx` with:

```python
def count_destination_grpc_status(stats_text: str) -> Dict[str, int]:
    """Completed gRPC failures that arrived as HTTP 200, per status code.

    Restricted to reporter=destination so a caller's outbound row is not
    added to the callee. response_code other than 200 is excluded: code 0
    is the reset the `resets` column already counts.
    """
    counts = {col: 0 for col in GRPC_COLUMNS}
    for line in stats_text.splitlines():
        m = PROM_LINE_RE.match(line.strip())
        if not m or m.group("name") != "istio_requests_total":
            continue
        labels = parse_prom_labels(m.group("labels") or "")
        if labels.get("reporter") != "destination":
            continue
        if labels.get("response_code") != "200":
            continue
        status = labels.get("grpc_response_status")
        if status not in GRPC_FAILURE_CODES:
            continue
        counts[f"grpc_{status}"] += int(float(m.group("value")))
    return counts
```

In `parse_inbound`: replace `grpc_5xx = count_destination_grpc_5xx(stats_text)` with `grpc = count_destination_grpc_status(stats_text)`; in the empty-case replace `empty["grpc_5xx"] = grpc_5xx` with `empty.update(grpc)`; at the end replace `out["grpc_5xx"] = grpc_5xx` with `out.update(grpc)`. In its docstring, replace the `grpc_5xx` paragraph with: "`grpc_2`, `grpc_4`, `grpc_13`, `grpc_14` are `istio_requests_total` rows on this scrape with reporter=destination and response_code=200, one per grpc_response_status. response_code 0 is left out because that series is the reset count."

In `write_inbound_csv`, replace `"grpc_5xx": inbound.get("grpc_5xx", 0),` with `**{col: inbound.get(col, 0) for col in GRPC_COLUMNS},`.

`sum_inbound_maps` already sums every `INBOUND_METRICS` key, so it needs no change.

- [ ] **Step 4: Run to confirm they pass**

Run: `python -m unittest experiments.test_envoy_retry_collector -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "feat: record completed gRPC failures per status code"
```

---

### Task 2: Per-callee retryOn and rejection rate in retryguard.py

**Files:**
- Modify: `experiments/retryguard.py` (constants near line 85; `InboundSnapshot` ~146; `read_latest_inbound_row` ~197; `InboundCsvTailer._apply_line` ~263; `measure_inbound_rejection` ~208; `http_retry_fields`, `build_vs_patch_body`, `build_edge_vs_patch_body`, `patch_virtualservice` ~370-490; the two callers at ~842 and ~930)
- Test: `experiments/test_retryguard.py`

**Interfaces:**
- Produces: `GRPC_RETRY_CALLEES`, `RETRY_ON_GRPC`, `retry_on_for(service: str) -> str`; `InboundSnapshot.grpc_4`, `.grpc_14` (default 0.0); `measure_inbound_rejection(previous, current, count_grpc: bool = False)`; the three body builders take a trailing `retry_on: str = RETRY_ON`. Every body stays a single route rule.

- [ ] **Step 1: Write the failing tests**

Add to `test_retryguard.py`:

```python
class TestGrpcRetryCallees(unittest.TestCase):
    def test_retry_on_for(self):
        self.assertEqual(
            retryguard.retry_on_for("recommendationservice"),
            "5xx,reset,connect-failure,unavailable,deadline-exceeded",
        )
        for svc in ("checkoutservice", "paymentservice", "emailservice",
                    "cartservice", "shippingservice", "frontend"):
            self.assertEqual(retryguard.retry_on_for(svc), "5xx,reset,connect-failure")

    def test_patch_body_uses_given_retry_on(self):
        route = [{"destination": {"host": "recommendationservice"}}]
        body = retryguard.build_vs_patch_body(
            route, 3, 500, retry_on=retryguard.retry_on_for("recommendationservice")
        )
        self.assertEqual(len(body["spec"]["http"]), 1)
        self.assertIn("deadline-exceeded", body["spec"]["http"][0]["retries"]["retryOn"])

    def test_rejection_counts_grpc_only_when_asked(self):
        prev = retryguard.InboundSnapshot("2026-10-07T10:00:01Z", 100.0, 0.0)
        curr = retryguard.InboundSnapshot(
            "2026-10-07T10:00:02Z", 200.0, 0.0, resets=0.0, grpc_4=30.0, grpc_14=10.0
        )
        off, _ = retryguard.measure_inbound_rejection(prev, curr)
        on, _ = retryguard.measure_inbound_rejection(prev, curr, count_grpc=True)
        self.assertAlmostEqual(off, 0.0)
        self.assertAlmostEqual(on, 0.40)
```

- [ ] **Step 2: Run to confirm they fail**

Run: `python -m unittest experiments.test_retryguard.TestGrpcRetryCallees -v`
Expected: FAIL (`retry_on_for` and the new fields do not exist).

- [ ] **Step 3: Implement**

Constants, below `RETRY_ON`:

```python
RETRY_ON = "5xx,reset,connect-failure"
# Callees whose methods are all reads, so a repeated call only costs load.
# cartservice (AddItem) and shippingservice (ShipOrder) stay on RETRY_ON:
# one route rule cannot split a read from a write, and the rejection rate
# has no per-method split either.
GRPC_RETRY_CALLEES = (
    "adservice",
    "currencyservice",
    "productcatalogservice",
    "recommendationservice",
)
RETRY_ON_GRPC = RETRY_ON + ",unavailable,deadline-exceeded"


def retry_on_for(service: str) -> str:
    return RETRY_ON_GRPC if service in GRPC_RETRY_CALLEES else RETRY_ON
```

`InboundSnapshot`: add `grpc_4: float = 0.0` and `grpc_14: float = 0.0` after `resets`. In both `read_latest_inbound_row` and `InboundCsvTailer._apply_line`, add to the constructor call:

```python
                grpc_4=float(row.get("grpc_4", 0) or 0),
                grpc_14=float(row.get("grpc_14", 0) or 0),
```

`measure_inbound_rejection`: add parameter `count_grpc: bool = False` and, after `delta_failures` is computed:

```python
    if count_grpc:
        delta_failures += (current.grpc_4 - previous.grpc_4) + (
            current.grpc_14 - previous.grpc_14
        )
```

Callers: at the edge-mode loop (~842) and the rejection-mode loop (~930), pass `service in GRPC_RETRY_CALLEES` as the third argument.

VirtualService builders: add a trailing `retry_on: str = RETRY_ON` parameter to `http_retry_fields`, `build_vs_patch_body`, and `build_edge_vs_patch_body`. In `http_retry_fields` use `"retryOn": retry_on`. `build_vs_patch_body` passes it to `http_retry_fields`. `build_edge_vs_patch_body` passes it to both its `build_vs_patch_body` call and its per-caller `http_retry_fields` call. In `patch_virtualservice`, compute `retry_on = retry_on_for(service_name)` once and pass `retry_on=retry_on` to whichever builder is called. Do not add a second http rule for any callee.

- [ ] **Step 4: Run the whole retryguard test file**

Run: `python -m unittest experiments.test_retryguard -v`
Expected: PASS, including the existing patch-body tests (the default keeps the old string).

- [ ] **Step 5: Commit**

```bash
git add experiments/retryguard.py experiments/test_retryguard.py
git commit -m "feat: retry on unavailable/deadline-exceeded for read-only callees"
```

---

### Task 3: Run-start patching and the checked-in manifest

**Files:**
- Modify: `experiments/run_scenario.py` (`restore_virtualservice_retries` ~1124, `apply_per_try_timeout` ~1167)
- Modify: `experiments/virtual-services.yaml` (the four callees)
- Test: `experiments/test_retryguard.py`

**Interfaces:**
- Consumes: `retryguard.retry_on_for`, `retryguard.GRPC_RETRY_CALLEES` from Task 2.
- Produces: `run_scenario.retry_on_for(service)` with the same result as `retryguard.retry_on_for`.

`run_scenario.py` does not import `retryguard` (retryguard is deployed to the master as one file), so the small helper is repeated here and a test keeps the two in step.

- [ ] **Step 1: Write the failing test**

Add to `test_retryguard.py`:

```python
class TestRunScenarioRetryOnMatches(unittest.TestCase):
    def test_same_string_as_controller(self):
        import run_scenario
        for svc in (
            "adservice", "cartservice", "checkoutservice", "currencyservice",
            "emailservice", "frontend", "paymentservice", "productcatalogservice",
            "recommendationservice", "shippingservice",
        ):
            self.assertEqual(run_scenario.retry_on_for(svc), retryguard.retry_on_for(svc))
```

- [ ] **Step 2: Run to confirm it fails**

Run: `python -m unittest experiments.test_retryguard.TestRunScenarioRetryOnMatches -v`
Expected: FAIL (`run_scenario` has no `retry_on_for`).

- [ ] **Step 3: Implement**

In `run_scenario.py`, above `restore_virtualservice_retries`, add:

```python
# Keep in step with retryguard.py (deployed standalone, so not imported).
RETRY_ON = "5xx,reset,connect-failure"
GRPC_RETRY_CALLEES = (
    "adservice", "currencyservice", "productcatalogservice", "recommendationservice",
)


def retry_on_for(service: str) -> str:
    if service in GRPC_RETRY_CALLEES:
        return RETRY_ON + ",unavailable,deadline-exceeded"
    return RETRY_ON
```

In both functions replace `"retryOn": "5xx,reset,connect-failure",` with `"retryOn": retry_on_for(svc),`. Keep one http rule per VirtualService.

In `virtual-services.yaml`, for the `adservice`, `currencyservice`, `productcatalogservice`, and `recommendationservice` VirtualServices change the line to `retryOn: "5xx,reset,connect-failure,unavailable,deadline-exceeded"`. Leave the other six, including `cartservice` and `shippingservice`, on the current string.

- [ ] **Step 4: Run both test files**

Run: `python -m unittest experiments.test_retryguard experiments.test_run_scenario -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/run_scenario.py experiments/virtual-services.yaml experiments/test_retryguard.py
git commit -m "feat: apply per-callee retryOn at run start and in the manifest"
```

---

### Task 4: Two live holds on the run157 mix

Run live; the earlier tasks only change code. Both holds use the mix of both-off run157 (340/115/150/5/5, Paper-C1, frontend pinned at 4) so each compares directly with an existing hold: the both-off hold against run157, the RetryGuard hold against RetryGuard-only run18. Leave a 360 s cool-off between them.

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (confirm `log_folder` is `…_run158` and counts are 340/115/150/5/5; fix them if not)
- Modify: `experiments/configs/scenario_2_retryguard_no_topfull.yaml` (confirm `log_folder` is `…_run19`, counts are 340/115/150/5/5, and `retry_metric: edge_rpr`; fix them if not)

- [ ] **Step 1: Run hold A (both off, run158)**

Follow AGENTS.md §6 (clear stale `/tmp` scripts, then):

```powershell
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

- [ ] **Step 2: Check hold A**

In `baseline_no_topfull_sustained_overload_run158`:

1. `service_inbound.csv` ends with `grpc_2,grpc_4,grpc_13,grpc_14`, and `grpc_4` is non-zero for `recommendationservice`.
2. Live `kubectl get virtualservice recommendationservice -o yaml` (mid-hold) shows the extended `retryOn`. `checkoutservice`, `cartservice`, and `shippingservice` each show one rule on `5xx,reset,connect-failure`.
3. `service_edges.csv`: compare Δretry on `frontend→recommendationservice` with run157 (284,199) and `frontend→checkoutservice` with run157 (1,517).

Pass: recommendations' retries rise clearly above run157 for the same mix and checkout's edge does not. If they do not rise, the statuses are arriving in trailers and Envoy is ignoring the new tokens; record that and stop before hold B (the rejection-rate half still stands).

- [ ] **Step 3: Cool off 360 s, then run hold B (RetryGuard on, TopFull off, run19)**

```powershell
python experiments/run_scenario.py experiments/configs/scenario_2_retryguard_no_topfull.yaml
python experiments/pull_results.py experiments/configs/scenario_2_retryguard_no_topfull.yaml
```

- [ ] **Step 4: Check hold B**

In `run_retryguard_no_topfull_sustained_overload_run19`, against RetryGuard-only run18 (same mix, old controller: 1× ON→OFF on `frontend→recommendationservice` at rpr 1.47, no OFF→ON, retries 23,402, goodput ~261, fail ~0.50):

1. `START` line in `retryguard.log` shows `metric=edge_rpr`; no traceback or `PATCH_FAIL`.
2. Count `ON→OFF` / `OFF→ON` per edge, and the rejection values logged at each re-enable for `recommendationservice` (they now include `grpc_4 + grpc_14`). State whether the re-enable bar of 0.10 was met in the OFF window, which run18 never did.
3. Report goodput, fail fraction, P95, and frontend→recommendations retries next to run18 and run158. Replicas are not guaranteed to match run18; state frontend replica count per sample and any `replica_count` zeros.

Pass: no `PATCH_FAIL`, the CSV columns and VS shapes are as above, and the numbers are reported side by side. No numeric improvement is required; do not tune thresholds in this plan.

- [ ] **Step 5: Record and commit**

Add one bullet each for run158 and run19 to `AGENTS.md` §4, and update the "Decision" section of `Guides and Info/2026-10-07-grpc-retry-and-rejection.md` to say the retry string and the rate now differ per callee, and that cart and shipping stay on the current string. Bump both YAMLs to the next free slot (`run159`, `run20`).

```bash
git add AGENTS.md "Guides and Info/2026-10-07-grpc-retry-and-rejection.md" experiments/configs/scenario_2_baseline_no_topfull.yaml experiments/configs/scenario_2_retryguard_no_topfull.yaml "experiments/results"
git commit -m "docs: per-callee gRPC retry results from run158 and run19"
```

---

## Self-review

- Spec coverage: per-code storage (Task 1); tokens for the four read-only callees, every other callee including cart and shipping unchanged and still one rule (Tasks 2-3); same codes in the rate for those four callees (Task 2); live check that retries rise with RetryGuard off (Task 4 hold A) and a RetryGuard-on hold of the same mix (Task 4 hold B).
- No placeholders: every code step shows the code. Task 4's checks depend on live output and carry stated criteria.
- Names are consistent across tasks: `GRPC_COLUMNS`, `count_destination_grpc_status`, `retry_on_for`, `GRPC_RETRY_CALLEES`, `grpc_4`, `grpc_14`, `count_grpc`.
