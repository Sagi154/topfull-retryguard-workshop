# Scorer Matches Controller Rejection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the scorer's per-service inbound rejection equal the number RetryGuard acts on, and keep the old HTTP-only number visible for the four read callees.

**Architecture:** `analysis_score.rejection_streaks` gets a `count_grpc` flag that mirrors `retryguard.measure_inbound_rejection`. `score_run` calls it with `count_grpc=True` for the four read callees and also stores an HTTP-only copy for them. The renderer prints the matched tables for every service and one extra HTTP-only table for the four callees. A parity test pins the two formulas together. Old guides are re-scored into new `-rescored.md` files; the originals are not edited.

**Tech Stack:** Python 3, `unittest`, `experiments/analysis_score.py`, `experiments/retryguard.py`, Markdown guides.

**Runs before:** the metrics-docs refresh plan (`C:\Users\sagi1\.cursor\plans\metrics_docs_refresh_4a81fc8c.plan.md`). That plan was edited to assume this one is done.

## Global Constraints

- The controller is the reference. Do not change `measure_inbound_rejection` or any RetryGuard behavior. `retryguard.py` is copied alone to master by `run_scenario.py`, so it must not import a new module. No shared module is created for that reason; a parity test keeps the copies equal.
- Controller formula, from `experiments/retryguard.py` lines 247-257: `(Δ5xx + Δresets [+ Δgrpc_4 + Δgrpc_14 when count_grpc]) / Δtotal`; `Δtotal <= 0` is a non-positive-total tick.
- The four read callees: `adservice`, `currencyservice`, `productcatalogservice`, `recommendationservice`. `retryguard.GRPC_RETRY_CALLEES` and `analysis_score.GRPC_CALLEES` must be equal as sets.
- Every other service keeps `5xx + resets` only. Edge rpr is untouched.
- A missing `grpc_4` / `grpc_14` column counts as 0 (`_num` already does this), so folders from before those columns still score.
- Never edit an existing guide in `Guides and Info/` to change its numbers. New files get the suffix `-rescored.md` and link back to the original.
- Run tests with `python -m pytest experiments/test_analysis_score.py experiments/test_retryguard.py`.

## File Structure

- Modify `experiments/analysis_score.py`: `rejection_streaks`, `score_run` (around line 598), the renderer (around lines 898-933), module docstring (lines 26-28).
- Modify `experiments/test_analysis_score.py`: scorer behavior tests.
- Modify `experiments/test_retryguard.py`: parity tests (this file already stubs `kubernetes` so `retryguard` imports).
- Modify `Guides and Info/ANALYSIS-TEMPLATE.md`: items 5, 7, 8 and a history note.
- Modify `Guides and Info/2026-10-13-controller-vs-scorer-rejection.md`: status resolved.
- Create `Guides and Info/<name>-rescored.md` for each affected 2026-10-12 guide.
- Modify `STATUS.md`: one Done bullet.

---

### Task 1: Scorer counts gRPC on the four read callees

**Files:**
- Modify: `experiments/analysis_score.py:338-380` (`rejection_streaks`), `:595-606` (`score_run` loop), `:26-28` (docstring)
- Test: `experiments/test_analysis_score.py` (class `TestRejectionAndInbound`, after line 150)

**Interfaces:**
- Consumes: `_num(row, key) -> float`, `GRPC_CALLEES` (analysis_score.py line 65).
- Produces: `rejection_streaks(rows, high_bar, low_bar, count_grpc=False) -> dict` with the same four keys as before. `score_run` result gains `"rejection_http": dict[str, dict]`, keyed by service, present only for services in `GRPC_CALLEES`. `result["rejection"][service]` for those four is the matched (gRPC-counted) value.

- [ ] **Step 1: Write the failing tests**

Add inside `TestRejectionAndInbound`:

```python
    def test_count_grpc_adds_grpc_failures(self):
        rows = [
            {"timestamp": "2026-10-13T00:00:00Z", "total": 0, "5xx": 0, "resets": 0, "grpc_4": 0, "grpc_14": 0},
            {"timestamp": "2026-10-13T00:00:01Z", "total": 100, "5xx": 0, "resets": 0, "grpc_4": 30, "grpc_14": 10},  # 0.40 with grpc
        ]
        http = score.rejection_streaks(rows, 0.20, 0.10)
        matched = score.rejection_streaks(rows, 0.20, 0.10, count_grpc=True)
        self.assertEqual(http["high_count"], 0)
        self.assertEqual(http["low_count"], 1)
        self.assertEqual(matched["high_count"], 1)
        self.assertEqual(matched["high_streak"], 1)
        self.assertEqual(matched["low_count"], 0)

    def test_count_grpc_without_grpc_columns_equals_http(self):
        rows = [
            {"timestamp": "2026-10-13T00:00:00Z", "total": 0, "5xx": 0, "resets": 0},
            {"timestamp": "2026-10-13T00:00:01Z", "total": 10, "5xx": 0, "resets": 3},
        ]
        self.assertEqual(
            score.rejection_streaks(rows, 0.20, 0.10, count_grpc=True),
            score.rejection_streaks(rows, 0.20, 0.10),
        )

    def test_score_run_matches_only_on_read_callees(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "run1"
            fields = ["timestamp", "service", "total", "5xx", "resets", "grpc_4", "grpc_14"]
            rows = []
            for service in ("productcatalogservice", "checkoutservice"):
                rows.append(["2026-10-13T00:00:00Z", service, 0, 0, 0, 0, 0])
                rows.append(["2026-10-13T00:00:01Z", service, 100, 0, 0, 30, 10])
            _write(folder / "service_inbound.csv", fields, rows)
            result = score.score_run(folder)
            self.assertEqual(result["rejection"]["productcatalogservice"]["high_count"], 1)
            self.assertEqual(result["rejection_http"]["productcatalogservice"]["high_count"], 0)
            self.assertEqual(result["rejection"]["checkoutservice"]["high_count"], 0)
            self.assertNotIn("checkoutservice", result["rejection_http"])
```

- [ ] **Step 2: Check the folder fixture**

`_write(path, header, rows)` takes list rows (`test_analysis_score.py` line 14) and `score.score_run(Path)` is the scorer entry point (`analysis_score.py` line 521). Run only the third test once; if `score_run` raises because another CSV is missing, add that file with `_write` (header only) in the test. Do not change the assertions.

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest experiments/test_analysis_score.py -k "count_grpc or matches_only" -v`
Expected: FAIL (`TypeError: rejection_streaks() got an unexpected keyword argument 'count_grpc'`, then `KeyError: 'rejection_http'`).

- [ ] **Step 4: Implement**

In `rejection_streaks`, change the signature and the `failed` line:

```python
def rejection_streaks(
    rows: list[dict], high_bar: float, low_bar: float, count_grpc: bool = False
) -> dict:
```

```python
        failed = _num(row, "5xx") + _num(row, "resets")
        if count_grpc:
            failed += _num(row, "grpc_4") + _num(row, "grpc_14")
```

Extend the docstring: `count_grpc` adds `grpc_4 + grpc_14` and is the controller's formula on the four read callees (`retryguard.measure_inbound_rejection(..., count_grpc=True)`).

In `score_run`, replace the `rejection[service] = ...` line and add the HTTP-only dict (declare `rejection_http = {}` next to `rejection = {}`):

```python
        matched = service in GRPC_CALLEES
        rejection[service] = rejection_streaks(rows, high_bar, low_bar, count_grpc=matched)
        if matched:
            rejection_http[service] = rejection_streaks(rows, high_bar, low_bar)
```

Add `"rejection_http": rejection_http,` to the returned dict next to `"rejection": rejection,` (line ~668).

Replace module docstring lines 26-28 with:

```
Rejection streaks use (delta 5xx + delta resets) / delta total, plus
delta grpc_4 + delta grpc_14 on the four read callees. That is the
controller's own formula (retryguard.measure_inbound_rejection). The
HTTP-only value for those four is kept in "rejection_http". A
non-positive total delta breaks a streak.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest experiments/test_analysis_score.py -v`
Expected: all PASS, including the older `test_non_positive_total_breaks_both_streaks`.

- [ ] **Step 6: Commit**

```bash
git add experiments/analysis_score.py experiments/test_analysis_score.py
git commit -m "feat(scorer): count grpc_4 and grpc_14 in rejection on the four read callees"
```

---

### Task 2: Render matched tables plus an HTTP-only table

**Files:**
- Modify: `experiments/analysis_score.py:898-933` (renderer)
- Test: `experiments/test_analysis_score.py` (class `TestScoreAndRender`)

**Interfaces:**
- Consumes: `item["rejection"]`, `item["rejection_http"]` from Task 1; `_table(title, header, labels, rows, sep)`; `GRPC_CALLEES`.
- Produces: render output with these table titles, exactly:
  - `(a) context: rejection streak above 0.20 / count. Not the shed signal` (matched; title unchanged so templates still match it)
  - `(a) context: rejection streak under the re-enable bar / count` (matched; unchanged)
  - `(a) context: HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees` (new)
  - `(a) context: HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees` (new)

- [ ] **Step 1: Read the existing render test**

Run: `rg -n "score.render|score.score_run" experiments/test_analysis_score.py`
Expected: `test_folder_and_group_bar` (about line 225-240) builds folders and calls `score.render(scored, ["1", "2"], sep=1)`. Copy its fixture style for any extra CSVs `render` needs.

- [ ] **Step 2: Write the failing test**

Add to `TestScoreAndRender`:

```python
    def test_http_only_table_lists_only_read_callees(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "run1"
            fields = ["timestamp", "service", "total", "5xx", "resets", "grpc_4", "grpc_14"]
            rows = []
            for service in ("productcatalogservice", "checkoutservice"):
                rows.append(["2026-10-13T00:00:00Z", service, 0, 0, 0, 0, 0])
                rows.append(["2026-10-13T00:00:01Z", service, 100, 0, 0, 30, 10])
            _write(folder / "service_inbound.csv", fields, rows)
            text = score.render([score.score_run(folder)], ["1"])
        marker = "HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees"
        self.assertIn(marker, text)
        section = text.split(marker, 1)[1].split("\n\n", 2)[1]
        self.assertIn("productcatalogservice", section)
        self.assertNotIn("checkoutservice", section)
```

- [ ] **Step 3: Run it to verify it fails**

Run: `python -m pytest experiments/test_analysis_score.py -k http_only_table -v`
Expected: FAIL on `assertIn(marker, text)`.

- [ ] **Step 4: Implement**

Change `rejection_rows` to take the source key and a service list:

```python
    def rejection_rows(key_streak, key_count, bold_at, source="rejection", services=SERVICES):
        rows = []
        for service in services:
            cells = []
            for item in scored:
                stats = item[source].get(service)
```

Everything else in the function stays. Then after the two existing `lines.append(_table(...))` blocks, add:

```python
    lines.append(_table(
        "(a) context: HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees",
        "Service", labels,
        rejection_rows("high_streak", "high_count", None, "rejection_http", GRPC_CALLEES), sep,
    ))
    lines.append(_table(
        "(a) context: HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees",
        "Service", labels,
        rejection_rows("low_streak", "low_count", None, "rejection_http", GRPC_CALLEES), sep,
    ))
```

Do not bold the HTTP-only tables. Change the line before the `grpc_4 / grpc_14` table to: `"gRPC counted in the rejection rate on the four read callees (main rejection tables above) and in the retry policy. Cell is grpc_4 / grpc_14."`

- [ ] **Step 5: Run the full scorer tests**

Run: `python -m pytest experiments/test_analysis_score.py -v`
Expected: all PASS.

- [ ] **Step 6: Smoke on a real folder**

Run: `python experiments/analysis_score.py "experiments/results/final results/S2_sustained_overload_burst/both/s2_burst20_rgtf1" | rg -n "HTTP-only|rejection streak"`
Expected: four `(a) context` titles. If that folder name does not exist, `Get-ChildItem "experiments/results/final results/S2_sustained_overload_burst/both"` and use any folder listed.

- [ ] **Step 7: Commit**

```bash
git add experiments/analysis_score.py experiments/test_analysis_score.py
git commit -m "feat(scorer): print HTTP-only rejection beside the matched tables"
```

---

### Task 3: Parity test between controller and scorer

**Files:**
- Test: `experiments/test_retryguard.py` (new class after `TestGrpcRetryCallees`, around line 993)

**Interfaces:**
- Consumes: `retryguard.InboundSnapshot`, `retryguard.measure_inbound_rejection`, `retryguard.GRPC_RETRY_CALLEES`, `analysis_score.rejection_streaks`, `analysis_score.GRPC_CALLEES`.
- Produces: none. This test fails whenever the two formulas drift.

- [ ] **Step 1: Write the test**

```python
class TestScorerControllerRejectionParity(unittest.TestCase):
    ROWS = [
        # timestamp, total, 5xx, resets, grpc_4, grpc_14
        ("2026-10-13T00:00:00Z", 0, 0, 0, 0, 0),
        ("2026-10-13T00:00:01Z", 100, 5, 5, 0, 0),    # 0.10 either way
        ("2026-10-13T00:00:02Z", 200, 5, 5, 30, 10),  # 0.40 with grpc, 0.00 http
        ("2026-10-13T00:00:03Z", 200, 5, 5, 30, 10),  # no arrivals
        ("2026-10-13T00:00:04Z", 300, 25, 5, 30, 10), # 0.20 http, not above 0.20
    ]

    def _csv_rows(self):
        return [
            {"timestamp": t, "total": tot, "5xx": f, "resets": r, "grpc_4": g4, "grpc_14": g14}
            for t, tot, f, r, g4, g14 in self.ROWS
        ]

    def _controller_rates(self, count_grpc):
        snaps = [
            retryguard.InboundSnapshot(t, float(tot), float(f), resets=float(r),
                                       grpc_4=float(g4), grpc_14=float(g14))
            for t, tot, f, r, g4, g14 in self.ROWS
        ]
        rates, prev = [], None
        for snap in snaps:
            rate, prev = retryguard.measure_inbound_rejection(prev, snap, count_grpc)
            rates.append(rate)
        return rates

    def test_counts_agree_for_both_modes(self):
        import analysis_score as score
        for count_grpc in (False, True):
            rates = [r for r in self._controller_rates(count_grpc) if r is not None]
            stats = score.rejection_streaks(self._csv_rows(), 0.20, 0.10, count_grpc=count_grpc)
            self.assertEqual(stats["high_count"], sum(1 for r in rates if r > 0.20))
            self.assertEqual(stats["low_count"], sum(1 for r in rates if r < 0.10))

    def test_read_callee_lists_match(self):
        import analysis_score as score
        self.assertEqual(set(score.GRPC_CALLEES), set(retryguard.GRPC_RETRY_CALLEES))
```

Note: the controller returns `0.0` for a non-positive total delta and the scorer skips that tick, so the no-arrivals row would count as under 0.10 for the controller. Fix the comparison in `test_counts_agree_for_both_modes` by dropping the controller rate for that tick: build `rates` from `snaps` only where `snap.total > previous.total`. Implement that by returning `None` from `_controller_rates` when `current.total <= previous.total` (check `snap.total` against the prior snapshot's total inside the loop before appending).

- [ ] **Step 2: Run it**

Run: `python -m pytest experiments/test_retryguard.py -k Parity -v`
Expected: PASS once Tasks 1 and 2 are in. To confirm the test has teeth, temporarily remove the `if count_grpc:` addition in `analysis_score.rejection_streaks`, rerun, expect FAIL, then restore it.

- [ ] **Step 3: Run both test files**

Run: `python -m pytest experiments/test_analysis_score.py experiments/test_retryguard.py -q`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add experiments/test_retryguard.py
git commit -m "test: pin scorer rejection to the controller formula"
```

---

### Task 4: Template and issue note

**Files:**
- Modify: `Guides and Info/ANALYSIS-TEMPLATE.md` items 5, 7, 8
- Modify: `Guides and Info/2026-10-13-controller-vs-scorer-rejection.md`

- [ ] **Step 1: ANALYSIS-TEMPLATE item 5**

Replace the item 5 text with:

```
5. **Rejection, beside (a).** Not the shed signal. Longest streak / count above 0.20, then longest streak / count under the re-enable bar. These are the controller's own numbers: `(Δ5xx + Δresets) / Δtotal`, plus `Δgrpc_4 + Δgrpc_14` on the four read callees (`adservice`, `currencyservice`, `productcatalogservice`, `recommendationservice`). **Bold** is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain. Two more tables (`HTTP-only rejection ... four read callees`) give the same two readings from `5xx + resets` alone, so guides written before 2026-10-13 can be compared on those four callees. Guides before 2026-10-13 show the HTTP-only number in the main table; their rescored copies end in `-rescored.md`.
```

- [ ] **Step 2: Item 7**

In item 7, replace `The same grpc_4 / grpc_14 pair is what the retry policy counts on the four read callees.` with `The same grpc_4 / grpc_14 pair is what the retry policy retries on, and what item 5 counts, on the four read callees.`

- [ ] **Step 3: Item 8**

Add at the end of item 8 Part 2: `The OFF rejection rows and item 5 now use the same definition, so a callee's number in both sections agrees.`

- [ ] **Step 4: Done-when line**

In "Done when", change `Bold marks match the rules in (a), the 0.20 rejection table, and (b).` to `Bold marks match the rules in (a), the 0.20 rejection table, and (b). The four read callees have an HTTP-only rejection table beside the main one.`

- [ ] **Step 5: Issue note**

In `2026-10-13-controller-vs-scorer-rejection.md` set the status line to `Status: resolved 2026-10-13. The scorer now uses the controller formula; HTTP-only values are kept for the four read callees. See docs/superpowers/plans/2026-10-13-scorer-matches-controller-rejection.md.` Under "Options", add `**Chosen: 2, plus the HTTP-only column from 3.**` and leave the rest of the file as the record.

- [ ] **Step 6: Commit**

```bash
git add "Guides and Info/ANALYSIS-TEMPLATE.md" "Guides and Info/2026-10-13-controller-vs-scorer-rejection.md"
git commit -m "docs: template and issue note for matched rejection"
```

---

### Task 5: Rescored copies of the 2026-10-12 guides

**Files:**
- Create: one `Guides and Info/<original-stem>-rescored.md` per affected guide
- Do not modify the originals

**Interfaces:**
- Consumes: the scorer from Tasks 1-2 and each guide's folder list.

- [ ] **Step 1: Find the affected guides**

Run: `rg -l "rejection streak above 0.20" "Guides and Info" | rg "2026-10-1[23]"`
Expected: the six 2026-10-12 guides (`s1-mode-matrix-abc`, `s2-burst-matrix-abc`, `s3-checkout-200-100-abc`, `s2-mode-matrix-abc`, `s2-normal-rgtf1-x3-abc`, `s1-s2-mode-matrix-abc`). Also run `rg -il "rejection" "Guides and Info/2026-10-12-s2-burst15-abc.md"` and include that guide if it has an item 5 style rejection table. Skip 2026-09 guides: they used older parameters and are out of the comparison.

- [ ] **Step 2: For each guide, get its run folders**

Open the guide's Setup / Index section and list the `experiments/results/final results/...` folders in index order, with the same `--sep` grouping the guide used (look at where its bold bar falls).

- [ ] **Step 3: Re-score**

Run, for each guide: `python experiments/analysis_score.py [--sep N] <run_dirs in index order> > $env:TEMP\<stem>.txt`
Expected: the output includes the four `(a) context` rejection tables.

- [ ] **Step 4: Write the rescored file**

Copy the original guide to `<stem>-rescored.md`. At the top, add:

```
> Re-scored 2026-10-13 with the scorer that matches the controller's rejection (`grpc_4 + grpc_14` counted on adservice, currencyservice, productcatalogservice, recommendationservice). Only item 5 changed. Original: [<stem>.md](<stem>.md).
```

Replace the item 5 tables (the two `(a) context: rejection streak ...` tables) with the scorer's new matched tables, and add the two HTTP-only tables after them. Replace any prose in that guide that quotes a rejection streak or count for one of the four callees with the new figure. Leave every other section byte-identical.

- [ ] **Step 5: Verify nothing else moved**

Run: `git diff --no-index --stat "Guides and Info/<stem>.md" "Guides and Info/<stem>-rescored.md"`
Expected: changes only in the header note and the item 5 region. Inspect `git diff --no-index` for any other hunk and revert it.

- [ ] **Step 6: Commit**

```bash
git add "Guides and Info/*-rescored.md"
git commit -m "docs: rescored copies of 2026-10-12 guides with matched rejection"
```

---

### Task 6: Hand-off to the metrics-docs plan and STATUS

**Files:**
- Modify: `STATUS.md`
- Verify: `C:\Users\sagi1\.cursor\plans\metrics_docs_refresh_4a81fc8c.plan.md` (already edited when this plan was written)

- [ ] **Step 1: STATUS**

Add one bullet under Done in `STATUS.md`: `2026-10-13: scorer rejection now uses the controller formula (grpc_4 + grpc_14 on the four read callees); HTTP-only tables kept beside it; 2026-10-12 guides re-scored into *-rescored.md. Plan: docs/superpowers/plans/2026-10-13-scorer-matches-controller-rejection.md.`

- [ ] **Step 2: Check the other plan**

Run: `rg -n "grpc_4|controller-vs-scorer|scorer inbound rejection|scorer's rejection" "C:\Users\sagi1\.cursor\plans\metrics_docs_refresh_4a81fc8c.plan.md"`
Expected: only lines that describe the matched definition. No line says the scorer excludes `grpc_4` / `grpc_14`.

- [ ] **Step 3: Full test run and commit**

Run: `python -m pytest experiments/test_analysis_score.py experiments/test_retryguard.py -q`
Expected: all PASS.

```bash
git add STATUS.md
git commit -m "docs(status): scorer matches controller rejection"
```

## Self-Review

- Spec coverage: scorer matches controller (Task 1), HTTP-only column on four callees (Task 2), parity test (Task 3), template and issue note (Task 4), re-scored copies in new files (Task 5), metrics-docs plan hand-off and STATUS (Task 6). Shared helper from the design was dropped on purpose (Global Constraints) because `retryguard.py` is deployed as a single file; the parity test replaces it.
- Names verified against the code: `score.score_run(Path)`, `score.render(scored, labels, sep=None)`, `_write(path, header, rows)` with list rows. The fixtures may need extra empty CSVs for `score_run`; Task 1 Step 2 covers that.
