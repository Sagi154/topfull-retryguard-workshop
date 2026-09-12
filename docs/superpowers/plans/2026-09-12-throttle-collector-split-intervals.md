# Throttle Collector Split Intervals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> This plan was written with the superpowers **writing-plans** skill. Spec source of truth: [2026-09-12-throttle-collector-split-intervals-design.md](../specs/2026-09-12-throttle-collector-split-intervals-design.md). Do not re-litigate the design.

**Goal:** Decouple Layer A (`/thresholds`+`/stats`) *attempt* cadence from Layer B / CSV-row cadence so live goproxy admin fetches default to every 5 s while `topfull_throttle.csv` and `topfull_detect.csv` keep writing one row per tick on the existing 1 s wall-clock grid.

**Architecture:** Extract a pure wall-clock predicate `is_layer_a_attempt_tick(aligned_epoch_seconds, layer_a_interval)`. `run_collector()` reads `layer_a_poll_interval_seconds` (default 5) and, each tick, computes `attempt_layer_a` from the same aligned epoch `tick_timestamp()` already floors to. `poll_once(..., attempt_layer_a)` skips `fetch_proxy_admin` when False and calls `resolve_thresholds(None)` / `resolve_admitted(None)` — the existing last-good / `*_fresh=0` path. Layer B still scrapes every tick. No new persistent loop state.

**Tech Stack:** Python 3 stdlib (`unittest`, no pytest). Run tests as `python experiments/test_topfull_throttle_collector.py` and `python experiments/test_run_scenario.py` from `c:\Users\sagi1\Projects\Workshop`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-throttle-collector-split-intervals-design.md`. Follow it literally.
- New param name is `layer_a_poll_interval_seconds`. Default **5** when absent from params / YAML. It does **not** default to matching `poll_interval_seconds`.
- `poll_interval_seconds` keeps its existing meaning and default (`1`): Layer B cAdvisor scrape, `topfull_detect.csv` row cadence, **and** `topfull_throttle.csv` row cadence.
- Attempt-cadence mechanism is **wall-clock-aligned modulo**, not a tick-counter: attempt Layer A iff `int(aligned_epoch) % layer_a_poll_interval_seconds == 0`. No new persistent state across `run_collector()` iterations.
- Extract `is_layer_a_attempt_tick(aligned_epoch_seconds: int, layer_a_interval: int) -> bool`.
- `poll_once()` gains `attempt_layer_a: bool`. When `False`, skip `fetch_proxy_admin` entirely (no thread-pool submission, no network call) and call `resolve_thresholds(None, ...)` / `resolve_admitted(None, ...)`.
- Freshness stays binary `0`/`1`. Do **not** add a third state for "not attempted."
- Do **not** change `PROXY_FETCH_TIMEOUT_SECONDS` (0.8 s).
- Do **not** split `/thresholds` vs `/stats` into independently configurable cadences. One Layer A interval covers both URLs together.
- Do **not** change Layer B (`scrape_cadvisor_cpu`, `detect_metrics`, `topfull_detect.csv` schema or cadence).
- Do **not** change signatures of `fetch_proxy_admin`, `resolve_thresholds`, `resolve_admitted`, `LastGoodThrottle`, or `write_throttle_csv`.
- Scenario YAMLs need **no** edits. The default of 5 applies when the key is absent.
- Do **not** patch goproxy. Do **not** backfill `experiments/results/campaign_48/` or `experiments/results/august_38/`.
- No new pip dependencies. Injected `run_cmd` / `fetch_url` only — no real sleeps or network in tests.
- Commit steps below are **only if the user has asked to commit**. Do not commit otherwise.

## File map

| File | Responsibility |
|---|---|
| Modify: `experiments/topfull_throttle_collector.py` | `DEFAULT_LAYER_A_POLL_INTERVAL_SECONDS`, `is_layer_a_attempt_tick`, `poll_once(attempt_layer_a=...)`, `run_collector` reads the new param and logs it |
| Modify: `experiments/test_topfull_throttle_collector.py` | All spec §5 tests |
| Modify: `experiments/run_scenario.py` | `start_topfull_throttle_collector()` writes `layer_a_poll_interval_seconds` into `/tmp/topfull_throttle_params.json` (default 5) |
| Modify: `experiments/test_run_scenario.py` | Wiring assertion for the new params key |
| Modify: `Guides and Info/TOPFULL-THROTTLE-METRICS.md` | Split cadence + new `*_fresh=0` meaning |
| Modify: `Guides and Info/METRICS-GATHERED.md` | Same |

Do **not** edit any file under `experiments/configs/`.

## Locked interfaces (every later task uses these names)

```python
DEFAULT_LAYER_A_POLL_INTERVAL_SECONDS = 5

def is_layer_a_attempt_tick(
    aligned_epoch_seconds: int, layer_a_interval: int
) -> bool:
    """True iff this aligned epoch is a Layer A attempt tick."""

def poll_once(
    ...,
    attempt_layer_a: bool = True,
) -> None:
    """When False, skip fetch_proxy_admin; resolve_*(None). Layer B still runs."""

# run_collector reads:
#   interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
#   layer_a_interval = int(params.get(
#       "layer_a_poll_interval_seconds", DEFAULT_LAYER_A_POLL_INTERVAL_SECONDS
#   ))
# each loop:
#   t = time.time()
#   aligned = int(t // interval) * interval
#   ts = tick_timestamp(interval, now=t)
#   attempt_layer_a = is_layer_a_attempt_tick(aligned, layer_a_interval)
```

`attempt_layer_a` defaults to `True` so every existing `poll_once(...)` call in `test_topfull_throttle_collector.py` stays valid without edits.

---

### Task 1: `is_layer_a_attempt_tick` predicate

**Files:**
- Modify: `experiments/topfull_throttle_collector.py` (add constant + function next to `tick_timestamp`)
- Test: `experiments/test_topfull_throttle_collector.py`

**Interfaces:**
- Consumes: nothing new. Same floor math as `tick_timestamp()` (`aligned = int(t // interval) * interval`).
- Produces:
  - `DEFAULT_LAYER_A_POLL_INTERVAL_SECONDS = 5`
  - `is_layer_a_attempt_tick(aligned_epoch_seconds: int, layer_a_interval: int) -> bool`

- [ ] **Step 1: Write the failing tests**

Append this class to `experiments/test_topfull_throttle_collector.py` immediately after `TestSleepUntilNextTick` (before `SAMPLE_STATS`):

```python
class TestIsLayerAAttemptTick(unittest.TestCase):
    def test_true_only_on_multiples_of_five(self):
        # Spec §5: poll_interval=1, layer_a=5, epochs 0..9 → True only at 0 and 5.
        got = [
            ttc.is_layer_a_attempt_tick(epoch, 5) for epoch in range(10)
        ]
        self.assertEqual(
            got,
            [True, False, False, False, False, True, False, False, False, False],
        )

    def test_interval_one_is_every_tick(self):
        self.assertTrue(
            all(ttc.is_layer_a_attempt_tick(epoch, 1) for epoch in range(10))
        )

    def test_constant_default_is_five(self):
        self.assertEqual(ttc.DEFAULT_LAYER_A_POLL_INTERVAL_SECONDS, 5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_topfull_throttle_collector.py TestIsLayerAAttemptTick`

Expected: FAIL with `AttributeError: module 'topfull_throttle_collector' has no attribute 'is_layer_a_attempt_tick'`.

- [ ] **Step 3: Add the constant and predicate**

In `experiments/topfull_throttle_collector.py`, immediately after `DEFAULT_POLL_INTERVAL_SECONDS = 1` (line 43), add:

```python
DEFAULT_LAYER_A_POLL_INTERVAL_SECONDS = 5
```

Do **not** touch `PROXY_FETCH_TIMEOUT_SECONDS = 0.8` on the following lines.

Immediately after `sleep_until_next_tick` (after its `sleeper or time.sleep` call, before `setup_logging`), add:

```python
def is_layer_a_attempt_tick(
    aligned_epoch_seconds: int, layer_a_interval: int
) -> bool:
    """Wall-clock predicate: attempt Layer A iff aligned epoch % interval == 0."""
    return int(aligned_epoch_seconds) % int(layer_a_interval) == 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: `OK` (existing classes plus `TestIsLayerAAttemptTick`).

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/topfull_throttle_collector.py experiments/test_topfull_throttle_collector.py
git commit -m "Add wall-clock predicate for Layer A attempt ticks"
```

---

### Task 2: `poll_once(attempt_layer_a)` skip path

**Files:**
- Modify: `experiments/topfull_throttle_collector.py` (`poll_once` only)
- Test: `experiments/test_topfull_throttle_collector.py`

**Interfaces:**
- Consumes: `is_layer_a_attempt_tick` from Task 1; existing `fetch_proxy_admin`, `resolve_thresholds`, `resolve_admitted`, `LastGoodThrottle`, `scrape_cadvisor_cpu`.
- Produces: `poll_once(..., attempt_layer_a: bool = True)`. When `False`: no `fetch_proxy_admin` submit; `resolve_thresholds(None, proxy_dir, store)` and `resolve_admitted(None, store)`. Layer B `scrape_cadvisor_cpu` still submitted every call. Default `True` preserves every existing test.

- [ ] **Step 1: Write the failing tests**

Append these helpers and classes to the end of `experiments/test_topfull_throttle_collector.py`, **before** `if __name__ == "__main__":`:

```python
SPLIT_EPOCHS = [int(EPOCH) + i for i in range(10)]


def _split_run_cmd(cmd):
    joined = " ".join(cmd)
    if "cadvisor" in joined and "podIP" in joined:
        return SimpleNamespace(returncode=0, stdout="10.0.0.9\n", stderr="")
    if "get" in cmd and ("po" in cmd or "pods" in joined):
        return SimpleNamespace(
            returncode=0, stdout=json.dumps(SAMPLE_POD_LIST), stderr=""
        )
    return SimpleNamespace(returncode=1, stdout="", stderr="no")


def _split_fetch_factory(fetched):
    lock = threading.Lock()

    def fetch_url(url: str) -> str:
        with lock:
            fetched.append(url)
        if url.endswith("/thresholds"):
            return SAMPLE_THRESHOLDS
        if url.endswith("/stats"):
            return SAMPLE_STATS
        if "deadbeefcheckout" in url:
            return SAMPLE_CADVISOR_SUMMARY
        raise OSError("no such container")

    return fetch_url


class TestPollOnceLayerASkip(unittest.TestCase):
    def _drive_ten_ticks(self, fetched, last_good=None):
        store = last_good if last_good is not None else ttc.LastGoodThrottle()
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            fetch_url = _split_fetch_factory(fetched)
            for epoch in SPLIT_EPOCHS:
                ts = ttc.tick_timestamp(1, now=float(epoch))
                ttc.poll_once(
                    record_path,
                    proxy_dir,
                    "http://10.128.0.3:8090/stats",
                    timestamp=ts,
                    run_cmd=_split_run_cmd,
                    fetch_url=fetch_url,
                    thresholds_url="http://10.128.0.3:8090/thresholds",
                    last_good=store,
                    attempt_layer_a=ttc.is_layer_a_attempt_tick(epoch, 5),
                )
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                throttle = list(csv.DictReader(f))
            with (record_path / "topfull_detect.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                detect = list(csv.DictReader(f))
            return throttle, detect

    def test_admin_fetch_twice_over_ten_ticks_csv_still_ten_rows(self):
        # Spec §5: /thresholds+/stats invoked on ticks 0 and 5 only;
        # topfull_throttle.csv still has 10 rows per API; skipped ticks *_fresh=0.
        fetched = []
        throttle, detect = self._drive_ten_ticks(fetched)
        stats_calls = sum(1 for url in fetched if url.endswith("/stats"))
        thresh_calls = sum(1 for url in fetched if url.endswith("/thresholds"))
        self.assertEqual(stats_calls, 2)
        self.assertEqual(thresh_calls, 2)
        by_ts = {}
        for row in throttle:
            by_ts.setdefault(row["timestamp"], []).append(row)
        self.assertEqual(len(by_ts), 10)
        for rows in by_ts.values():
            self.assertEqual(len(rows), len(ttc.LOCUST_APIS))
        attempt_ts = {
            ttc.tick_timestamp(1, now=float(SPLIT_EPOCHS[0])),
            ttc.tick_timestamp(1, now=float(SPLIT_EPOCHS[5])),
        }
        for ts, rows in by_ts.items():
            if ts in attempt_ts:
                self.assertTrue(all(r["threshold_fresh"] == "1" for r in rows))
                self.assertTrue(all(r["admitted_fresh"] == "1" for r in rows))
            else:
                self.assertTrue(all(r["threshold_fresh"] == "0" for r in rows))
                self.assertTrue(all(r["admitted_fresh"] == "0" for r in rows))
            by_api = {r["api"]: r for r in rows}
            self.assertEqual(by_api["getproduct"]["threshold"], "10000.0")
            self.assertEqual(by_api["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(by_api["getcart"]["threshold"], "80.0")

    def test_layer_b_unaffected_ten_detect_ticks(self):
        # Spec §5: topfull_detect.csv is 10 × DETECT_SERVICES; scrape_cadvisor_cpu
        # (and its cAdvisor fetch_url calls) happen every tick. SAMPLE_POD_LIST
        # has two app containers, so fetch_url cAdvisor hits are >10; count the
        # scrape function itself.
        fetched = []
        scrape_calls = {"n": 0}
        orig_scrape = ttc.scrape_cadvisor_cpu

        def counting_scrape(*args, **kwargs):
            scrape_calls["n"] += 1
            return orig_scrape(*args, **kwargs)

        with mock.patch.object(
            ttc, "scrape_cadvisor_cpu", side_effect=counting_scrape
        ):
            _throttle, detect = self._drive_ten_ticks(fetched)
        self.assertEqual(len(detect), 10 * len(ttc.DETECT_SERVICES))
        self.assertEqual(scrape_calls["n"], 10)
        cadvisor_urls = [
            url for url in fetched if "/api/v2.0/summary/" in url
        ]
        self.assertTrue(cadvisor_urls)
        by_ts = {r["timestamp"] for r in detect}
        self.assertEqual(len(by_ts), 10)
        checkout = [
            r for r in detect if r["service"] == "checkoutservice"
        ]
        self.assertEqual(len(checkout), 10)
        self.assertTrue(all(r["cadvisor_cpu"] == "910.0" for r in checkout))


class TestFreshnessSkippedByDesign(unittest.TestCase):
    def test_skipped_tick_carries_last_good_even_if_fetch_would_succeed(self):
        # Spec §5: admin fetch *would* succeed, but non-attempt tick still
        # writes *_fresh=0 and carries the previous attempt's values.
        fetched = []
        last_good = ttc.LastGoodThrottle()
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            fetch_url = _split_fetch_factory(fetched)
            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://10.128.0.3:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=_split_run_cmd,
                fetch_url=fetch_url,
                thresholds_url="http://10.128.0.3:8090/thresholds",
                last_good=last_good,
                attempt_layer_a=True,
            )
            fetched_after_attempt = list(fetched)
            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://10.128.0.3:8090/stats",
                timestamp="2023-11-14T22:13:21Z",
                run_cmd=_split_run_cmd,
                fetch_url=fetch_url,
                thresholds_url="http://10.128.0.3:8090/thresholds",
                last_good=last_good,
                attempt_layer_a=False,
            )
            admin_after_skip = [
                url
                for url in fetched[len(fetched_after_attempt) :]
                if url.endswith("/thresholds") or url.endswith("/stats")
            ]
            self.assertEqual(admin_after_skip, [])
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                rows = list(csv.DictReader(f))
            tick1 = {
                r["api"]: r
                for r in rows
                if r["timestamp"] == "2023-11-14T22:13:20Z"
            }
            tick2 = {
                r["api"]: r
                for r in rows
                if r["timestamp"] == "2023-11-14T22:13:21Z"
            }
            self.assertEqual(tick1["getproduct"]["threshold"], "10000.0")
            self.assertEqual(tick1["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(tick1["getproduct"]["threshold_fresh"], "1")
            self.assertEqual(tick1["getproduct"]["admitted_fresh"], "1")
            self.assertEqual(tick2["getproduct"]["threshold"], "10000.0")
            self.assertEqual(tick2["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(tick2["getproduct"]["threshold_fresh"], "0")
            self.assertEqual(tick2["getproduct"]["admitted_fresh"], "0")
            self.assertEqual(tick2["getcart"]["threshold"], "80.0")
            self.assertNotIn("2", {r["threshold_fresh"] for r in rows})
            self.assertNotIn("2", {r["admitted_fresh"] for r in rows})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_topfull_throttle_collector.py TestPollOnceLayerASkip TestFreshnessSkippedByDesign`

Expected: FAIL — `poll_once() got an unexpected keyword argument 'attempt_layer_a'`. (If the 10-tick test is reached with today's `poll_once`, admin URLs are fetched on every tick, so `stats_calls` is 10 not 2.)

- [ ] **Step 3: Add `attempt_layer_a` to `poll_once`**

In `experiments/topfull_throttle_collector.py`, replace the entire `poll_once` function with:

```python
def poll_once(
    record_path: Path,
    proxy_dir: Path,
    stats_url: str,
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[UrlFetcher] = None,
    cpu_quotas: Optional[Dict[str, int]] = None,
    thresholds_url: Optional[str] = None,
    http_proxy: Optional[str] = None,
    last_good: Optional[LastGoodThrottle] = None,
    attempt_layer_a: bool = True,
) -> None:
    ts = timestamp or utc_now()
    thresh_url = thresholds_url or (stats_url.rsplit("/", 1)[0] + "/thresholds")
    store = last_good if last_good is not None else LastGoodThrottle()
    try:
        runner = run_cmd or default_run_cmd
        fetcher = fetch_url or _admin_aware_fetch(http_proxy)
        thresh_map: Optional[Dict[str, float]] = None
        admitted_map: Optional[Dict[str, float]] = None
        cpu_by_svc: Dict[str, float] = {}

        with ThreadPoolExecutor(max_workers=3) as pool:
            fut_admin = None
            if attempt_layer_a:
                fut_admin = pool.submit(
                    fetch_proxy_admin, fetcher, stats_url, thresh_url, ts
                )
            fut_cpu = pool.submit(scrape_cadvisor_cpu, runner, fetcher)
            if fut_admin is not None:
                try:
                    thresh_map, admitted_map, _te, _se = fut_admin.result()
                except Exception as exc:
                    log.warning("%s  WARNING  admin fetch failed: %s", ts, exc)
            try:
                cpu_by_svc = fut_cpu.result()
            except Exception as exc:
                log.warning("%s  WARNING  cadvisor scrape failed: %s", ts, exc)

        if not attempt_layer_a:
            thresh_map = None
            admitted_map = None
        thresholds, t_fresh = resolve_thresholds(thresh_map, proxy_dir, store)
        admitted, a_fresh = resolve_admitted(admitted_map, store)
        write_throttle_csv(
            record_path / "topfull_throttle.csv",
            ts,
            thresholds,
            admitted,
            threshold_fresh=t_fresh,
            admitted_fresh=a_fresh,
        )
        rows = {
            svc: detect_metrics(
                svc, cpu_by_svc.get(svc, 0.0), quotas=cpu_quotas
            )
            for svc in DETECT_SERVICES
        }
        write_detect_csv(record_path / "topfull_detect.csv", ts, rows)
    except Exception as exc:
        log.warning("%s  WARNING  poll_once failed: %s", ts, exc)
```

Do **not** change `fetch_proxy_admin`, `resolve_thresholds`, `resolve_admitted`, `LastGoodThrottle`, `PROXY_FETCH_TIMEOUT_SECONDS`, or any Layer B function.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: `OK`. Existing `TestPollOnce` / `TestParallelAdminFetch` / `TestLastGoodThrottle` / `TestLayerBNotBlocked` keep working because `attempt_layer_a` defaults to `True`.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/topfull_throttle_collector.py experiments/test_topfull_throttle_collector.py
git commit -m "Skip Layer A admin fetch on non-attempt throttle ticks"
```

---

### Task 3: `run_collector` reads the new param and computes `attempt_layer_a`

**Files:**
- Modify: `experiments/topfull_throttle_collector.py` (`run_collector` only)
- Test: `experiments/test_topfull_throttle_collector.py`

**Interfaces:**
- Consumes: `DEFAULT_LAYER_A_POLL_INTERVAL_SECONDS`, `is_layer_a_attempt_tick`, `poll_once(..., attempt_layer_a=...)`.
- Produces: `run_collector` reads `layer_a_poll_interval_seconds` from `params` (default 5); each iteration uses one `time.time()` reading for both `tick_timestamp(interval, now=t)` and `aligned = int(t // interval) * interval`; passes `is_layer_a_attempt_tick(aligned, layer_a_interval)` into `poll_once`. START log also reports `layer_a_poll_interval=%ss`.

- [ ] **Step 1: Write the failing tests**

Append this class before `if __name__ == "__main__":` in `experiments/test_topfull_throttle_collector.py`:

```python
class TestRunCollectorLayerAInterval(unittest.TestCase):
    def _run_with_clock(self, params, fetched):
        times = iter(float(EPOCH) + i for i in range(20))
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            with mock.patch.object(ttc.time, "time", side_effect=lambda: next(times)):
                ttc.run_collector(
                    params,
                    record_path,
                    proxy_dir,
                    "http://10.128.0.3:8090/stats",
                    run_cmd=_split_run_cmd,
                    fetch_url=_split_fetch_factory(fetched),
                    thresholds_url="http://10.128.0.3:8090/thresholds",
                    max_polls=10,
                )
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                throttle = list(csv.DictReader(f))
            with (record_path / "topfull_detect.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                detect = list(csv.DictReader(f))
            return throttle, detect

    def test_absent_key_defaults_to_five(self):
        # Spec §5: params has only poll_interval_seconds; implicit default 5
        # → admin fetch exactly 2 times over 10 polls.
        fetched = []
        throttle, detect = self._run_with_clock(
            {"poll_interval_seconds": 1}, fetched
        )
        self.assertEqual(
            sum(1 for url in fetched if url.endswith("/stats")), 2
        )
        self.assertEqual(
            sum(1 for url in fetched if url.endswith("/thresholds")), 2
        )
        self.assertEqual(
            len({r["timestamp"] for r in throttle}), 10
        )
        self.assertEqual(len(detect), 10 * len(ttc.DETECT_SERVICES))

    def test_explicit_one_reproduces_every_tick(self):
        # Spec §5: layer_a_poll_interval_seconds=1 → admin fetch on all 10 polls.
        fetched = []
        throttle, _detect = self._run_with_clock(
            {
                "poll_interval_seconds": 1,
                "layer_a_poll_interval_seconds": 1,
            },
            fetched,
        )
        self.assertEqual(
            sum(1 for url in fetched if url.endswith("/stats")), 10
        )
        self.assertEqual(
            sum(1 for url in fetched if url.endswith("/thresholds")), 10
        )
        self.assertEqual(len({r["timestamp"] for r in throttle}), 10)

    def test_start_log_mentions_layer_a_interval(self):
        fetched = []
        with self.assertLogs(ttc.log, level="INFO") as cm:
            self._run_with_clock({"poll_interval_seconds": 1}, fetched)
        start_lines = [line for line in cm.output if "START" in line]
        self.assertTrue(start_lines)
        self.assertIn("layer_a_poll_interval=5s", start_lines[0])
        self.assertIn("poll_interval=1s", start_lines[0])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_topfull_throttle_collector.py TestRunCollectorLayerAInterval`

Expected: FAIL — `test_absent_key_defaults_to_five` sees 10 `/stats` fetches (today's 1:1 cadence), and/or `test_start_log_mentions_layer_a_interval` does not find `layer_a_poll_interval=5s`.

- [ ] **Step 3: Wire `run_collector`**

In `experiments/topfull_throttle_collector.py`, replace the entire `run_collector` function with:

```python
def run_collector(
    params: dict,
    record_path: Path,
    proxy_dir: Path,
    stats_url: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[UrlFetcher] = None,
    max_polls: Optional[int] = None,
    thresholds_url: Optional[str] = None,
    http_proxy: Optional[str] = None,
) -> None:
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    layer_a_interval = int(
        params.get(
            "layer_a_poll_interval_seconds",
            DEFAULT_LAYER_A_POLL_INTERVAL_SECONDS,
        )
    )
    cpu_quotas = params.get("cpu_quotas")
    if cpu_quotas is not None:
        cpu_quotas = {str(k): int(v) for k, v in cpu_quotas.items()}
    thresh_url = thresholds_url or (stats_url.rsplit("/", 1)[0] + "/thresholds")
    last_good = LastGoodThrottle()
    log.info(
        "%s  START  poll_interval=%ss layer_a_poll_interval=%ss",
        utc_now(),
        interval,
        layer_a_interval,
    )
    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        if max_polls is None:
            sleep_until_next_tick(interval)
            if _shutdown:
                break
        t = time.time()
        aligned = int(t // interval) * interval
        ts = tick_timestamp(interval, now=t)
        poll_once(
            record_path,
            proxy_dir,
            stats_url,
            timestamp=ts,
            run_cmd=run_cmd,
            fetch_url=fetch_url,
            cpu_quotas=cpu_quotas,
            thresholds_url=thresh_url,
            http_proxy=http_proxy,
            last_good=last_good,
            attempt_layer_a=is_layer_a_attempt_tick(aligned, layer_a_interval),
        )
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
    log.info("%s  EXIT", utc_now())
```

`time.time()` is called **once** per loop iteration and that reading is passed to `tick_timestamp(..., now=t)` so the timestamp and the modulo predicate share the same aligned epoch. Do not introduce a `polls % ratio` counter.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: `OK`. `TestRunCollector.test_max_polls_writes_and_exits` still passes (`max_polls=1` still writes both CSVs regardless of whether that wall-clock second is an attempt tick).

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/topfull_throttle_collector.py experiments/test_topfull_throttle_collector.py
git commit -m "Drive Layer A attempts from layer_a_poll_interval_seconds"
```

---

### Task 4: Wire `run_scenario.py` `start_topfull_throttle_collector()`

**Files:**
- Modify: `experiments/run_scenario.py` (`start_topfull_throttle_collector`, the `params` dict around the existing `poll_interval_seconds` key)
- Test: `experiments/test_run_scenario.py` (`TestTopfullThrottleCollectorWiring`)

**Interfaces:**
- Consumes: YAML `topfull_throttle_collector.layer_a_poll_interval_seconds` (optional).
- Produces: `/tmp/topfull_throttle_params.json` gains `"layer_a_poll_interval_seconds": int(ttc_cfg.get("layer_a_poll_interval_seconds", 5))` next to the existing `poll_interval_seconds` and `cpu_quotas` keys. `run_manifest.json` already snapshots the whole YAML block — no manifest edit. Scenario YAMLs are **not** edited.

- [ ] **Step 1: Write the failing assertions**

In `experiments/test_run_scenario.py`, inside `TestTopfullThrottleCollectorWiring.test_start_uploads_params_and_launches_tmux`, immediately after `self.assertEqual(params["poll_interval_seconds"], 1)`, add:

```python
        self.assertEqual(params["layer_a_poll_interval_seconds"], 5)
        self.assertNotIn(
            "layer_a_poll_interval_seconds",
            cfg["topfull_throttle_collector"],
        )
```

Then append this new method to the same class:

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_passes_explicit_layer_a_interval(
        self, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        cfg["topfull_throttle_collector"]["layer_a_poll_interval_seconds"] = 1
        run_scenario.start_topfull_throttle_collector(cfg)
        params = mock_write_json.call_args[0][2]
        self.assertEqual(params["poll_interval_seconds"], 1)
        self.assertEqual(params["layer_a_poll_interval_seconds"], 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_run_scenario.py TestTopfullThrottleCollectorWiring`

Expected: FAIL — `KeyError: 'layer_a_poll_interval_seconds'` (or assertion that the key is missing from `params`).

- [ ] **Step 3: Pass the new key from YAML**

In `experiments/run_scenario.py`, inside `start_topfull_throttle_collector`, replace the `params = { ... }` block with:

```python
    params = {
        "poll_interval_seconds": int(ttc_cfg.get("poll_interval_seconds", 1)),
        "layer_a_poll_interval_seconds": int(
            ttc_cfg.get("layer_a_poll_interval_seconds", 5)
        ),
        "cpu_quotas": topfull_cpu_quotas.effective_cpu_quotas(
            cfg.get("scale_constraints") or []
        ),
    }
```

Replace the `step("Uploaded TopFull throttle collector params: ...")` call with:

```python
    step(
        "Uploaded TopFull throttle collector params: "
        f"poll_interval={params['poll_interval_seconds']}s "
        f"layer_a_poll_interval={params['layer_a_poll_interval_seconds']}s"
    )
```

Do **not** edit any file under `experiments/configs/`. Do **not** change the `run_manifest.json` writer — it already stores `cfg.get("topfull_throttle_collector", {})`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_run_scenario.py`

Expected: `OK`.

Also re-run: `python experiments/test_topfull_throttle_collector.py`

Expected: `OK`.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "Pass layer_a_poll_interval_seconds into throttle collector params"
```

---

### Task 5: Document the split cadence and new freshness meaning

**Files:**
- Modify: `Guides and Info/TOPFULL-THROTTLE-METRICS.md` (collector status paragraph ~line 81; Layer A table rows ~lines 95–96; "How to keep this" Layer A subsection ~lines 245–264)
- Modify: `Guides and Info/METRICS-GATHERED.md` (Layer 3 supplement writer + `topfull_throttle.csv` freshness paragraph ~lines 202–213; clocks bullet ~line 295)

**Interfaces:** none. Docs only. Do not claim `campaign_48/` has these files. Do not edit scenario YAMLs.

- [ ] **Step 1: Update `TOPFULL-THROTTLE-METRICS.md`**

Replace the collector paragraph that currently begins `The collector is **implemented**` with:

```markdown
The collector is **implemented** (`experiments/topfull_throttle_collector.py`): Layer B (cAdvisor) and both CSV **row** cadences stay on the wall-clock **1 s** grid (`poll_interval_seconds`, default 1) so `topfull_throttle.csv` remains joinable with `service_edges.csv` / `service_inbound.csv` / `resource_usage.csv` on `timestamp`. Live Layer A `GET /thresholds` + `GET /stats` attempts use a slower cadence (`layer_a_poll_interval_seconds`, default **5**, applied even when a scenario YAML omits the key): a tick is an attempt iff `int(aligned_epoch) % layer_a_poll_interval_seconds == 0`. On a skipped tick, or on goproxy timeout, it **carries the last successful values** and sets the matching `*_fresh` flag to `0`. `*_fresh` stays binary `0`/`1` — `0` means the value in this row is carried, whether because this tick was not attempted by design or because the attempt timed out. Distinguish those two cases from `topfull_throttle_collector.log` (`WARNING  …fetch failed` only on genuine failures). Campaign folders still lack these files until the next run — this does not backfill `campaign_48/` or `august_38/`. Details are in [How to keep this for analysis](#how-to-keep-this-for-analysis-future-runs-only).
```

In the Layer A table, replace the two "How to get it" cells that say `every 1 s` with:

```markdown
| **Threshold** | It cut `postcheckout` to 40 req/s. | Live `GET :8090/thresholds` every `layer_a_poll_interval_seconds` (default 5 s). CSV still writes the carried cap every 1 s. |
| **Admitted RPS** | The proxy let 37 through (clamp binding, or Locust offered less). | Live `GET :8090/stats` on the same Layer A attempt cadence (default 5 s). CSV still writes the carried admitted value every 1 s. |
```

In **How to keep this for analysis**, replace the opening "Implemented (2026-09-09; …)" sentence so it also names the split-interval design, then replace Layer A numbered steps 1–4 and the freshness paragraph with:

```markdown
**Implemented (2026-09-09; Layer A scrape hardened 2026-09-11; Layer A attempt cadence split 2026-09-12).** Campaign folders still lack the files until the next run. Design: [2026-09-09-topfull-throttle-collector-design.md](../docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md) + [2026-09-12-throttle-collector-split-intervals-design.md](../docs/superpowers/specs/2026-09-12-throttle-collector-split-intervals-design.md) — `topfull_throttle_collector.py` writes Layer A and Layer B on the **same wall-clock 1s grid** as the per-service mesh collector (one CSV row per API / service per second). Live proxied `:8090/thresholds` + `:8090/stats` fetches are attempted only when `int(aligned_epoch) % layer_a_poll_interval_seconds == 0` (default 5). Layers C/D remain out of scope.

**Layer A — proxy / cap (required):**

1. Same script on master. CSV row cadence stays 1 s (`poll_interval_seconds`). Live `/thresholds`+`/stats` attempts use `layer_a_poll_interval_seconds` (default 5; set `1` to reproduce the old 1:1 cadence).
2. On an attempt tick, fetch `/thresholds` and `/stats` **in parallel** through goproxy (`ProxyHandler` → `127.0.0.1:8090`, request `proxy_url + "/…"`), each with a **0.8 s** timeout, and run Layer B cAdvisor in the same pool so a proxy timeout cannot stall the detector scrape. On a non-attempt tick, skip the admin pair entirely; Layer B still runs.
3. On success, store the values as last-good. On skip, timeout, or empty body, **carry last-good** (do not write measured zeros from an empty `rate_config/` dir). `rate_config/<api>` is used only when at least one API file still exists.
4. Write `topfull_throttle.csv` with columns: timestamp, api, threshold, admitted_rps, threshold_fresh, admitted_fresh.

`threshold_fresh` / `admitted_fresh` are `1` if that column was measured this tick, `0` if carried forward (or still unknown). After the split cadence, most `0`s under the default are "not attempted this tick by design," not "attempted and timed out." Analysts who need a true per-second admitted rate should still filter `admitted_fresh==1`. Threshold last-good is the sticky cap. Do not introduce a third freshness value.
```

Leave the **Follow-up not implemented** background-`/stats`-thread paragraph in place (still out of scope). Do not change Layer B text.

- [ ] **Step 2: Update `METRICS-GATHERED.md`**

Replace the Layer 3 supplement writer + `topfull_throttle.csv` block (the paragraph beginning `**Writer:**` through the `admitted_fresh==1` sentence) with:

```markdown
**Writer:** `experiments/topfull_throttle_collector.py` on master. CSV rows stay on
1s wall-clock ticks shared with the mesh collector (`poll_interval_seconds`,
default 1). Live Layer A `GET /thresholds` + `GET /stats` attempts use
`layer_a_poll_interval_seconds` (default **5**, even when the scenario YAML
omits the key). `topfull_detect.csv` cadence is unchanged (still 1 s).

**Present only in runs launched after this collector landed** — not in
`campaign_48/` or `august_38/`.

### `topfull_throttle.csv`
timestamp, api, threshold, admitted_rps, threshold_fresh, admitted_fresh

`threshold_fresh` / `admitted_fresh` are `1` when measured that tick, `0` when
the value is carried from an earlier successful scrape. After the split
cadence, `0` covers both "not attempted this tick by design" and "attempted
and timed out" — there is no third state. Filter `admitted_fresh==1` for a
true per-second admitted rate. Row cadence is still 1 s and still joinable
on `timestamp`; the live fraction of rows is lower by design under the
default. Genuine timeouts vs skips are in `topfull_throttle_collector.log`
(`WARNING  …fetch failed` only on failures).
```

In the clocks subsection, replace the bullet that currently begins `Envoy mesh + throttle collectors now stamp` with:

```markdown
- Envoy mesh + throttle collectors now stamp `floor(unix_time / interval) * interval` UTC seconds (aligned). `resource_usage.csv` uses interval=5 on the same grid. Throttle **rows** stay 1 s; Layer A live `/thresholds`+`/stats` attempts use `layer_a_poll_interval_seconds` (default 5) on that same aligned grid. Skipped ticks still write a `topfull_throttle.csv` row with `*_fresh=0`.
```

- [ ] **Step 3: Confirm no YAML edits slipped in**

Run: `git diff --stat -- experiments/configs`

Expected: empty (no scenario YAML changes).

- [ ] **Step 4: Commit (only if the user has asked to commit)**

```
git add "Guides and Info/TOPFULL-THROTTLE-METRICS.md" "Guides and Info/METRICS-GATHERED.md"
git commit -m "Document throttle collector Layer A split cadence"
```

---

## Self-review (spec coverage)

| Spec item | Task |
|---|---|
| §3.1 `layer_a_poll_interval_seconds` default **5**; `poll_interval_seconds` stays Layer B + CSV cadence | Task 1 constant + Task 3 `run_collector` read |
| §3.2 wall-clock-aligned modulo; extract `is_layer_a_attempt_tick` | Task 1 |
| §3.2 `poll_once(attempt_layer_a)`; skip `fetch_proxy_admin`; `resolve_*(None)` | Task 2 |
| §3.2 `run_collector` computes `attempt_layer_a` from aligned epoch; START log includes both intervals | Task 3 |
| §3.3 freshness stays binary `0`/`1`; skip and timeout both write `0` | Task 2 `TestFreshnessSkippedByDesign` |
| §3.4 absent YAML/params key → default 5, not "match poll_interval" | Task 3 `test_absent_key_defaults_to_five` + Task 4 wiring default |
| §3.4 explicit `1` reproduces today's 1:1 cadence | Task 3 `test_explicit_one_reproduces_every_tick` + Task 4 explicit-1 wiring test |
| §3.5 / §6 no `/thresholds` vs `/stats` split | Global Constraints — not planned |
| §4 `run_scenario.py` `ttc_cfg.get("layer_a_poll_interval_seconds", 5)` | Task 4 |
| §4 scenario YAMLs need no edits | Global Constraints + Task 5 Step 3 |
| §4 docs: split cadence, `*_fresh=0` also means "not attempted", row cadence still 1 s | Task 5 |
| §5 attempt-cadence unit test (epochs 0..9 → True at 0 and 5) | Task 1 |
| §5 `poll_once` 10-tick / 2 admin fetches / 10 CSV rows | Task 2 |
| §5 Layer B unaffected (10 × `DETECT_SERVICES`, cAdvisor every tick) | Task 2 |
| §5 freshness on a skipped (not failed) tick | Task 2 |
| §5 default via `run_collector(..., max_polls=10)` | Task 3 |
| §5 opt-out `layer_a_poll_interval_seconds: 1` | Task 3 |
| §6 `PROXY_FETCH_TIMEOUT_SECONDS` unchanged; Layer B untouched; no goproxy patch; no campaign backfill | Global Constraints |

Out of scope left unplanned on purpose: per-endpoint `/thresholds` vs `/stats` cadences, changing the 0.8 s timeout, Layer B schema/cadence, goproxy admin port, `mentor_charts.py`, scenario YAML edits, campaign backfill, a live S2 confirmation run (spec §7 empirical follow-up).
