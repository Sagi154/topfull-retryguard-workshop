# Reset-driven mu_sat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `mu_sat` fire on reset-driven overload the same way RetryGuard already measures rejection — `(Δ5xx + Δresets) / Δtotal` — so `capacity_frozen.py freeze` can lock real `mu_per_millicore` values from the existing local calibration folders.

**Architecture:** One generalization in `estimate_service_mu.py` (read the existing `resets` column, new `failure_fraction` trigger, same `Δ2xx/dt` numerator). `capacity_frozen.py` and `rho_estimate_report.py` follow that field. No collector, no CLI flags, no VM runs.

**Tech Stack:** Python 3 stdlib (`unittest`), existing `service_inbound.csv` on already-pulled local folders.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-19-reset-driven-mu-sat-design.md`
- Denominator stays `Δtotal` (completed requests). Do **not** rewrite as `Δ(5xx+resets)/Δ(total+resets)`. Fraction > 1.0 is expected.
- Keep `SAT_5XX_FRACTION = 0.05`. Do not retune it if a service still has `mu_sat=None`.
- Keep `Tick.five_xx_fraction`. Stop using it to gate `sat_samples`.
- Missing `resets` column → 0 (`_int` already does this).
- Do not touch `retryguard.py`.
- Do not add a 5xx-only vs reset-only `mu_sat` split.
- Do not start VMs. Verify against local folders only.
- Freeze μ only from the three full-CPU calibration folders. S3 RG run8 is estimate-only (checkout is 100m there, not paper 1000m).
- Do not regenerate every campaign `rho_estimate_report.*`. Only the four verification folders if you choose to, and never the historical August-38 tree.

## File map

| File | Role |
|---|---|
| `experiments/estimate_service_mu.py` | Diff `resets`, `failure_fraction`, `inbound_failure_fraction`, gate `mu_sat` on it |
| `experiments/test_estimate_service_mu.py` | Reset-only sat tick + keep existing 5xx sat test |
| `experiments/capacity_frozen.py` | `count_sat_ticks` + freeze error string |
| `experiments/test_capacity_frozen.py` | Freeze succeeds on reset-only CSV |
| `experiments/rho_estimate_report.py` | Methodology sentence + toggle-summary token |
| `experiments/capacity/capacity_frozen.json` | Written by freeze CLI in Task 3, not by hand |
| `experiments/capacity/README.md`, `AGENTS.md` | After a successful freeze |

---

### Task 1: Estimator — reset-aware `mu_sat`

**Files:**
- Modify: `experiments/estimate_service_mu.py`
- Test: `experiments/test_estimate_service_mu.py`

**Interfaces:**
- Consumes: `service_inbound.csv` `resets` column (already collected).
- Produces: `Tick.delta_resets: int = 0`, `Tick.failure_fraction -> float`, `ServiceEstimate.inbound_failure_fraction: float = 0.0`, `mu_sat` gated on `failure_fraction >= SAT_5XX_FRACTION`.

- [ ] **Step 1: Write the failing tests**

In `experiments/test_estimate_service_mu.py`, extend `_tick` so reset-only ticks can be built without touching every existing call:

```python
def _tick(lambda_s, w_seconds, dtotal=100, d2xx=100, d5xx=0, dt=1.0,
          ts="2026-09-13T13:52:11Z", has_latency_cols=True, dresets=0):
    return mu.Tick(
        timestamp=ts,
        dt_seconds=dt,
        lambda_s=lambda_s,
        delta_total=dtotal,
        delta_2xx=d2xx,
        delta_5xx=d5xx,
        has_latency_cols=has_latency_cols,
        w_seconds=w_seconds,
        delta_resets=dresets,
    )
```

Add these tests next to `TestTickFiveXxFraction` / `TestSummarizeService`:

```python
class TestTickFailureFraction(unittest.TestCase):
    def test_resets_only_can_exceed_one(self):
        t = _tick(80.0, 0.02, dtotal=100, d5xx=0, dresets=260)
        self.assertAlmostEqual(t.five_xx_fraction, 0.0)
        self.assertAlmostEqual(t.failure_fraction, 2.6)

    def test_zero_when_no_total(self):
        t = _tick(0.0, None, dtotal=0, dresets=10)
        self.assertEqual(t.failure_fraction, 0.0)


class TestSummarizeService(unittest.TestCase):
    # keep test_high_five_xx_uses_sat_mu_independent_of_latency unchanged

    def test_zero_five_xx_means_no_sat_mu(self):
        ticks = [_tick(80.0, 0.02), _tick(90.0, 0.02)]
        est = mu.summarize_service("frontend", ticks)
        self.assertIsNone(est.mu_sat)

    def test_high_resets_zero_5xx_uses_sat_mu(self):
        # failure_fraction = 20/100 = 0.20 >= 0.05; mu_sat = 80
        est = mu.summarize_service(
            "checkoutservice",
            [_tick(100.0, 0.01, dtotal=100, d2xx=80, d5xx=0, dresets=20)],
        )
        self.assertEqual(est.mu_sat, 80.0)
        self.assertEqual(est.inbound_5xx_fraction, 0.0)
        self.assertAlmostEqual(est.inbound_failure_fraction, 0.20)
```

Also add a CSV-level check that a missing `resets` column still diffs (treated as 0) — reuse `test_folder_without_latency_columns_reports_gap` as the pattern; no extra file needed if `_int` already returns 0.

- [ ] **Step 2: Run tests, expect FAIL**

```powershell
python -m unittest experiments.test_estimate_service_mu -v
```

Expected: `Tick.__init__() got an unexpected keyword argument 'delta_resets'` and/or `Tick has no attribute failure_fraction`.

- [ ] **Step 3: Minimal implementation**

In `experiments/estimate_service_mu.py`:

1. After `delta_5xx = ...` in `difference_inbound`, add:

```python
delta_resets = _int(cur, "resets") - _int(prev, "resets")
```

and include `"delta_resets": delta_resets` in the appended dict.

2. Add `delta_resets: int = 0` as the **last** field on `Tick` (keeps existing positional `Tick(...)` calls valid). Add:

```python
@property
def failure_fraction(self) -> float:
    if self.delta_total <= 0:
        return 0.0
    return (self.delta_5xx + self.delta_resets) / self.delta_total
```

Leave `five_xx_fraction` as-is.

3. In `ticks_from_rows`, pass `delta_resets=d.get("delta_resets", 0)`.

4. On `ServiceEstimate`, add `inbound_failure_fraction: float = 0.0` **after** `inbound_5xx_fraction` (default so existing positional constructors keep working).

5. In `summarize_service`:

```python
d5 = sum(t.delta_5xx for t in ticks)
dreset = sum(t.delta_resets for t in ticks)
dtot = sum(t.delta_total for t in ticks)
inbound_5xx_fraction = (d5 / dtot) if dtot else 0.0
inbound_failure_fraction = ((d5 + dreset) / dtot) if dtot else 0.0

sat_samples = [
    t.delta_2xx / t.dt_seconds
    for t in ticks
    if t.delta_total > 0 and t.failure_fraction >= SAT_5XX_FRACTION
]
```

Pass `inbound_failure_fraction=inbound_failure_fraction` on every `ServiceEstimate(...)` return in this function.

6. Add `"inbound_failure_fraction"` to `format_table` headers/rows, next to `inbound_5xx_fraction`.

7. Module docstring: change `mu_sat = Δ2xx/Δt on ticks with a high 5xx fraction` to `high (5xx+resets) fraction`.

- [ ] **Step 4: Run tests, expect PASS**

```powershell
python -m unittest experiments.test_estimate_service_mu -v
```

Expected: OK. Existing `test_high_five_xx_uses_sat_mu_independent_of_latency` still passes (10/100 5xx still saturates). `test_zero_five_xx_means_no_sat_mu` still has `mu_sat is None`.

- [ ] **Step 5: Commit**

```powershell
git add experiments/estimate_service_mu.py experiments/test_estimate_service_mu.py
git commit -m "Gate mu_sat on (5xx+resets)/total so reset-driven overload can freeze μ."
```

---

### Task 2: Freeze + report follow the new trigger

**Files:**
- Modify: `experiments/capacity_frozen.py`
- Modify: `experiments/rho_estimate_report.py`
- Test: `experiments/test_capacity_frozen.py`

**Interfaces:**
- Consumes: `Tick.failure_fraction` from Task 1.
- Produces: `count_sat_ticks` counts `failure_fraction >= SAT_5XX_FRACTION`; freeze error text `no saturating 5xx/reset ticks`; report prints `inbound_failure_fraction`.

- [ ] **Step 1: Write the failing freeze test**

In `experiments/test_capacity_frozen.py`, extend `_write_inbound` to include `resets` (default `"0"` so existing tests stay valid):

```python
def _write_inbound(d: Path, rows: list[dict]) -> None:
    fields = ["timestamp", "service", "total", "2xx", "4xx", "5xx",
              "resets", "rq_time_sum_ms", "rq_time_count"]
    with open(d / "service_inbound.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            row.setdefault("resets", "0")
            w.writerow(row)
```

Add:

```python
def test_freeze_succeeds_on_reset_only_saturation(self):
    with TemporaryDirectory() as raw:
        d = Path(raw)
        _write_capacity(d, "checkoutservice", 100)
        _write_inbound(d, [
            {"timestamp": "2026-09-17T00:00:00Z", "service": "checkoutservice",
             "total": "0", "2xx": "0", "4xx": "0", "5xx": "0", "resets": "0",
             "rq_time_sum_ms": "0", "rq_time_count": "0"},
            {"timestamp": "2026-09-17T00:00:01Z", "service": "checkoutservice",
             "total": "100", "2xx": "50", "4xx": "0", "5xx": "0", "resets": "50",
             "rq_time_sum_ms": "0", "rq_time_count": "0"},
        ])
        out = d / "capacity_frozen.json"
        cf.save_table(cf.empty_table(), out)
        entry = cf.freeze_service(
            d, "checkoutservice", table_path=out, force=True
        )
        self.assertAlmostEqual(entry.throughput_at_calibration, 50.0)
        self.assertAlmostEqual(entry.mu_per_millicore, 0.5)
        self.assertGreaterEqual(entry.n_sat_ticks, 1)
```

Keep `test_refuses_when_mu_sat_missing` (5xx=0 and resets=0 / omitted).

- [ ] **Step 2: Run test, expect FAIL**

```powershell
python -m unittest experiments.test_capacity_frozen.TestFreezeService.test_freeze_succeeds_on_reset_only_saturation -v
```

Expected: FAIL with `mu_sat unavailable for checkoutservice (no saturating 5xx ticks)` until Task 1 is in and `count_sat_ticks` still filters on `five_xx_fraction` — after Task 1, `freeze_service` may already succeed because it uses `estimate_run().mu_sat`. If it already PASSES, still switch `count_sat_ticks` so `n_sat_ticks` is not stuck at 0.

- [ ] **Step 3: Wire freeze + report**

`experiments/capacity_frozen.py` `count_sat_ticks`:

```python
return sum(
    1 for t in ticks
    if t.delta_total > 0 and t.failure_fraction >= mu.SAT_5XX_FRACTION
)
```

Change the freeze error string to:

```python
f"mu_sat unavailable for {service} (no saturating 5xx/reset ticks)"
```

`experiments/rho_estimate_report.py`:

- In `CONTEXT_NOTE`, replace `on ticks with a high 5xx fraction` with `on ticks with a high (5xx+resets) fraction`.
- On the toggle-summary line (~line 247), append ` inbound_failure_fraction={mu._fmt(est.inbound_failure_fraction)}`.

Do **not** change `test_rho_estimate_report.py` unless a constructor breaks (it currently does not construct `ServiceEstimate` by field list).

- [ ] **Step 4: Run tests, expect PASS**

```powershell
python -m unittest experiments.test_capacity_frozen experiments.test_estimate_service_mu experiments.test_rho_estimate_report -v
```

Expected: OK.

- [ ] **Step 5: Commit**

```powershell
git add experiments/capacity_frozen.py experiments/test_capacity_frozen.py experiments/rho_estimate_report.py
git commit -m "Count reset-saturated ticks when freezing mu_per_millicore."
```

---

### Task 3: Local verify, then freeze for real

**Files:**
- Modify (via freeze CLI, not by hand): `experiments/capacity/capacity_frozen.json`
- Modify: `experiments/capacity/README.md`, `AGENTS.md` — only after freeze actually writes numbers
- Do not overwrite S3 / campaign-48 historical result CSVs

**Interfaces:**
- Consumes: Task 1+2 code; local folders listed below.
- Produces: real `mu_per_millicore` for whichever of the four minimum-set services now have `mu_sat`, or an explicit still-`not_yet_calibrated` note if `mu_sat` is still null.

- [ ] **Step 1: Print estimates for the four folders**

```powershell
python experiments/estimate_service_mu.py experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run2
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_checkout_payment_full_cpu_run1
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_productcatalog_full_cpu_run1
python experiments/estimate_service_mu.py experiments/results/campaign_48/S3_targeted_bottleneck/run_topfull_retryguard_targeted_bottleneck_run8
```

Record `mu_sat` / `inbound_5xx_fraction` / `inbound_failure_fraction` for `frontend`, `checkoutservice`, `paymentservice`, `productcatalogservice`. S3 run8 is a cross-check that checkout now has a number; do not freeze from it.

- [ ] **Step 2: Freeze from the three full-CPU folders (skip any service whose `mu_sat` is still n/a)**

```powershell
python experiments/capacity_frozen.py freeze "experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run2" --service frontend --force
python experiments/capacity_frozen.py freeze "experiments/results/campaign_48/calibration_checkout_payment_full_cpu_run1" --service checkoutservice --force
python experiments/capacity_frozen.py freeze "experiments/results/campaign_48/calibration_checkout_payment_full_cpu_run1" --service paymentservice --force
python experiments/capacity_frozen.py freeze "experiments/results/campaign_48/calibration_productcatalog_full_cpu_run1" --service productcatalogservice --force
```

Expected stdout per success: `froze <service> mu_per_millicore=<number> -> experiments\capacity\capacity_frozen.json`. Expected on still-null: `mu_sat unavailable for <service> (no saturating 5xx/reset ticks)` — leave that entry `not_yet_calibrated`, do **not** lower the threshold.

- [ ] **Step 3: Sanity `rho_hat` on S1/S2 baselines (only for services that actually froze)**

```powershell
python experiments/rho_frozen_report.py "experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24"
python experiments/rho_frozen_report.py "experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23"
```

Read frontend `rho_hat` (and any other frozen service). Informal band from earlier discussion: S1 entry ~0.5–0.8, S2 entry >1 — a sanity check, not a pass/fail gate. If `rho_hat` is still `n/a`, the freeze in Step 2 did not stick.

- [ ] **Step 4: Update README + AGENTS.md to match reality**

If freeze succeeded: `experiments/capacity/README.md` lists which services have `method: mu_sat`, source run, and millicores. `AGENTS.md` §4 gets one dated bullet (2026-09-19): reset-driven trigger, which services froze, sample `rho_hat` numbers.

If freeze failed for a service: keep `not_yet_calibrated` and say so — still a completed plan, not a reason to invent a new saturation definition.

- [ ] **Step 5: Commit**

```powershell
git add experiments/capacity/capacity_frozen.json experiments/capacity/README.md AGENTS.md
git commit -m "Freeze mu_per_millicore from reset-aware mu_sat on full-CPU calibration runs."
```

If nothing froze, skip adding `capacity_frozen.json` numbers and commit only the docs that record the still-null outcome.

---

## Self-review

1. **Spec coverage:** trigger (`failure_fraction`) = Task 1; numerator unchanged = Task 1; `inbound_failure_fraction` + `format_table` = Task 1; `count_sat_ticks` + error string + report sentence = Task 2; four-folder verify + freeze + no threshold loosening = Task 3; `retryguard.py` untouched; no VM runs; no dual mu_sat variants.
2. **Placeholders:** none. S3 freeze-exclusion is explicit (wrong millicores), not a TBD.
3. **Names:** `failure_fraction`, `inbound_failure_fraction`, `delta_resets` used consistently across tasks.
