# RetryGuard `service_inbound.csv` incremental tailer

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Replace `retryguard.py`'s per-tick, per-service full re-parse of `service_inbound.csv` with a single incremental tailer that reads only newly-appended bytes. Fixes a real, measured inefficiency identified while investigating the 2026-09-15 `S2_sustained_overload` RetryGuard run (`run_topfull_retryguard_sustained_overload_run10`), which showed a ~4-minute simultaneous restart of RetryGuard + all 3 master-side collectors partway through the run, plus a run-wide ~2x P95 degradation vs the baseline arm (`baseline_topfull_no_retryguard_sustained_overload_run21`). This spec **does not** claim to fully explain that incident (see [2026-09-15-TOPFULL-E2-16-RETRY-SUMMARY.md](../../../Guides%20and%20Info/2026-09-15-TOPFULL-E2-16-RETRY-SUMMARY.md) for the observed symptoms) — it removes one concrete, avoidable source of extra CPU/disk load that RetryGuard adds to the shared master node, as a prerequisite to re-testing cleanly.

Related: [RETRYGUARD-IMPLEMENTATION.md](../../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md), [2026-09-10-retryguard-mesh-measure-value-design.md](2026-09-10-retryguard-mesh-measure-value-design.md) (defines `service_inbound.csv`'s schema and the Δ5xx/Δtotal formula this spec must preserve exactly).

---

## 1. Purpose and scope

**Problem, with evidence:** In `run_topfull_retryguard_sustained_overload_run10`, `retryguard.py`'s log went silent from `2026-09-15T10:00:15Z` to `10:04:36Z` (261s), then printed a fresh `WAITING`/`READY`/`START` sequence — a genuine process restart, not just a slow tick. The same ~200-260s window shows `envoy_retry_collector.py`, `resource_usage_collector.py`, and `topfull_throttle_collector.py` all restarting too (fresh `START` log lines at 10:03:08Z / 10:03:35Z / 10:04:08Z respectively), while the baseline arm (no RetryGuard) ran the identical scenario with zero such gaps. Whatever caused the restart is most likely an external/operational event (out of scope here — see §6), but RetryGuard's own hot loop has a genuine, fixable inefficiency that adds unnecessary CPU/disk I/O to the same master node the whole time it runs, regardless of whether that specific incident recurs.

**In scope**

- Replace the full-file re-parse in `retryguard.py`'s `run()` loop (currently 9 calls/sec to `read_latest_inbound_row()`, each a full `list(csv.DictReader(...))` over the whole file) with a single incremental read per tick that only processes bytes appended since the last poll.
- Preserve `measure_inbound_rejection()`'s exact semantics: one raw sample per second, SKIP on no-newer-timestamp, `Δtotal == 0 → 0.0`, `Δ(5xx + resets) / Δtotal` (per [2026-09-10-retryguard-mesh-measure-value-design.md](2026-09-10-retryguard-mesh-measure-value-design.md)).
- Handle the file being written concurrently by `envoy_retry_collector.py` (partial trailing line at read time) and being freshly created at RetryGuard startup (`wait_for_inbound_csv()` already handles "doesn't exist yet").
- Unit tests for the new tailer, using the same `service_inbound.csv` fixture style already in `experiments/test_retryguard.py`.

**Out of scope**

- Diagnosing or fixing *why* the mid-run restart happened (that needs a live repro with master-node CPU/mem sampling — see plan Task 3 for the collector extension, and Task 2 for the re-run).
- Changing `read_latest_inbound_row()` — it stays as-is; it's covered by existing unit tests (`TestReadLatestInboundRow`) and is fine as a one-off "read the whole file" utility. This spec only stops the hot loop from calling it 9×/second.
- Changing Algorithm 1, `apply_algorithm1()`, thresholds, or `interval_samples`.
- Changing `service_inbound.csv`'s schema or `envoy_retry_collector.py`'s write side.
- Batching/parallelizing the 9 per-service lookups differently than "one shared cache, 9 dict reads."

---

## 2. Current behavior (baseline to preserve)

```150:172:experiments/retryguard.py
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
        ...
```

```370:380:experiments/retryguard.py
    while not _shutdown:
        time.sleep(sample_interval)
        if _shutdown:
            break

        for service in CONTROLLED_SERVICES:
            current = read_latest_inbound_row(inbound_path, service)
            rejection, previous[service] = measure_inbound_rejection(
                previous[service], current
            )
```

9 `CONTROLLED_SERVICES` × 1 full-file parse/service/second. `service_inbound.csv` grows by ~11 rows/second (11 Boutique services × 1 poll/sec from `envoy_retry_collector.py`), so by minute 9 of a 10-minute run the file has ~6000 rows and RetryGuard is fully re-reading and re-parsing ~6000 lines, 9 times, every single second — ~54,000 row-parses/sec by the end of a long run, all thrown away except 9 rows.

---

## 3. New design

### 3.1 `InboundCsvTailer`

A new class in `retryguard.py`, instantiated once in `run()`:

```python
class InboundCsvTailer:
    """
    Incrementally tails service_inbound.csv. Call poll() once per tick;
    read self.latest[service] afterward. Never re-parses bytes already
    consumed. Safe to call poll() even if the file doesn't exist yet or
    was truncated/recreated (e.g. a stale leftover from a prior run).
    """

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.latest: Dict[str, InboundSnapshot] = {}
        self._offset = 0
        self._fieldnames: Optional[list[str]] = None
        self._pending = ""  # buffered partial trailing line from last poll

    def poll(self) -> None:
        """Read and apply any new complete lines. No-op on any I/O error
        or missing file (mirrors read_latest_inbound_row's OSError handling)."""
```

**Behavior:**

- **First successful poll:** open the file, read from byte 0, treat the first line as the CSV header (capture `_fieldnames` via `csv.reader`), then process remaining complete lines as data rows.
- **Subsequent polls:** `os.stat()` the file size first.
  - If `size < self._offset` (file shrank — truncated or recreated by a fresh collector launch): reset `_offset = 0`, `_fieldnames = None`, `_pending = ""`, `self.latest = {}`, and re-run the "first successful poll" path this call. (Mirrors what would happen if `retryguard.py` itself restarted and reopened the file fresh — makes the tailer robust to the exact kind of collector restart seen in `run10`.)
  - Otherwise: open the file, `seek(self._offset)`, read to EOF, prepend `self._pending`, split on `"\n"`. All complete lines (i.e. all but a possible trailing fragment with no newline) get parsed; the trailing fragment becomes the new `self._pending`. Update `self._offset` to the file size (or byte position actually consumed — see plan Task 1 Step 3 for the exact accounting).
- **Row parsing:** each complete line → `next(csv.reader([line]))` → zip with `self._fieldnames` → build a plain dict → same field extraction / `try/except (KeyError, TypeError, ValueError): continue` guard as `read_latest_inbound_row()` today → construct `InboundSnapshot` → `self.latest[row["service"]] = snapshot` (last one wins per service per poll, matching the old "keep overwriting `latest` while scanning" behavior).
- **Any `OSError`** (file disappears mid-read, permission blip, etc.): log nothing extra, leave `self.latest` and `_offset` unchanged, try again next tick — mirrors `read_latest_inbound_row()`'s existing `except OSError: return None`.

### 3.2 `run()` loop change

```370:380:experiments/retryguard.py
    tailer = InboundCsvTailer(inbound_path)
    while not _shutdown:
        time.sleep(sample_interval)
        if _shutdown:
            break

        tailer.poll()
        for service in CONTROLLED_SERVICES:
            current = tailer.latest.get(service)
            rejection, previous[service] = measure_inbound_rejection(
                previous[service], current
            )
```

One `poll()` call/tick (amortized O(new bytes since last tick), not O(total file size)), 9 dict lookups instead of 9 file re-parses. Everything downstream (`measure_inbound_rejection`, `apply_algorithm1`, logging, patching) is untouched.

### 3.3 Why this is safe

- `measure_inbound_rejection()` already guards `current.timestamp <= previous.timestamp` → SKIP, so if `tailer.latest[service]` hasn't changed since last tick (no new row for that service this second), behavior is identical to today (SKIP, counters unchanged).
- A service with **zero** rows so far → `tailer.latest.get(service)` returns `None`, same as `read_latest_inbound_row()` returning `None` today → SKIP.
- Truncation/reset handling means a stale `record_path` (leftover files, or a genuine mid-run collector restart that recreates `service_inbound.csv` from scratch) doesn't wedge the tailer into reading garbage or crashing — it just re-syncs.

---

## 4. Testing

Add to `experiments/test_retryguard.py` (new `TestInboundCsvTailer` class), using the existing `_write_inbound()` / `_row()` helpers:

- Tailing picks up rows written after construction (simulate: write 1 row, `poll()`, assert `latest`; append 1 more row, `poll()` again, assert `latest` updated, and assert **no full re-read** happened — e.g. by asserting `_offset` advanced rather than reset to 0).
- A poll with no new bytes since the last one leaves `latest` and `_offset` unchanged.
- File doesn't exist yet → `poll()` is a no-op, `latest == {}`.
- File shrinks (simulate truncation) → next `poll()` re-reads from scratch and rebuilds `latest` correctly rather than crashing or silently keeping stale offsets.
- A partial trailing line (file written mid-row, no trailing `\n` yet) is buffered and completed correctly once the rest of the line is appended on a later poll.
- End-to-end: after several `poll()` calls interleaved with appends across multiple services, `latest[service]` matches what `read_latest_inbound_row(path, service)` would return for each service — i.e. the incremental tailer and the full-reparse function agree on the same file contents (regression guard against subtly wrong incremental logic).

---

## 5. Non-goals / explicitly not doing

- Not switching to `csv.DictReader` on a streaming file object (would require careful `newline=""`/universal-newline handling across seek boundaries that's easy to get subtly wrong; plain manual line-splitting on bytes already read is simpler to reason about and test).
- Not adding file locking around `service_inbound.csv` — `envoy_retry_collector.py`'s append pattern (open, write, close each poll) already makes concurrent reads safe enough in practice (this file's read pattern hasn't changed, only the range of bytes read).
- Not changing `wait_for_inbound_csv()` (startup wait) — it still does one `list(csv.DictReader(...))` at startup only, which is fine (single call, not hot-loop).

---

## 6. Follow-up (separate from this spec)

Confirming whether this fix actually prevents the `run10`-style mid-run restart, and whether it's really RetryGuard (vs. an unrelated master-node event) behind the ~2x P95 gap, requires re-running the scenario and directly sampling master's own CPU/memory during the run. That's covered by Tasks 2 and 3 of the accompanying implementation plan, not by this spec.
