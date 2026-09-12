# Throttle collector — split Layer A / Layer B poll intervals — design

TopFull + RetryGuard Workshop — TAU Deepness Lab

> `experiments/topfull_throttle_collector.py` polls Layer A (goproxy `:8090` `/thresholds`+`/stats`) and Layer B (cAdvisor CPU + paper-quota `overloaded` reconstruction) on the exact same 1 s grid today, driven by one `poll_interval_seconds`. Layer A's admin-hook GETs are `OnRequest` hooks on the **same** `:8090` process that all Locust traffic flows through, and under S2-style sustained overload they mostly fail to complete inside the 0.8 s budget (measured ~24.6% fresh in one run) — and every attempt is itself one more proxied HTTP round-trip competing for accept-queue slots and `StatsModule` mutex time on the already-saturated listener. This spec decouples Layer A's *attempt* cadence from Layer B's, on a slower, configurable interval (default 5 s), while Layer B and the CSV row cadence stay unchanged. This is **option 1 ("split intervals")** from a prior discussion with the user — the choice itself is not re-litigated here, only specified. Design-only; no code, YAML, or doc changes are made as part of this task.

Related: [TOPFULL-THROTTLE-METRICS.md](../../../Guides%20and%20Info/TOPFULL-THROTTLE-METRICS.md), [THROTTLE-METRICS-COLLECTOR-AND-QUOTA-SYNC-2026-09.md](../../../Guides%20and%20Info/THROTTLE-METRICS-COLLECTOR-AND-QUOTA-SYNC-2026-09.md) §2 "Layers A–D", [2026-09-09-topfull-throttle-collector-design.md](2026-09-09-topfull-throttle-collector-design.md) (original collector + wall-clock alignment mechanism), [2026-09-11-slo-fail-and-mu-estimator-design.md](2026-09-11-slo-fail-and-mu-estimator-design.md) §3/§8 (why `/stats`/`/thresholds` contend with data-plane traffic; measured freshness and collector-overhead data), [METRICS-GATHERED.md](../../../Guides%20and%20Info/METRICS-GATHERED.md).

---

## 1. Purpose and scope

**In scope**

- A new, independently configurable attempt cadence for Layer A (`/thresholds`+`/stats`), decoupled from Layer B's cAdvisor-scrape / CSV-row cadence.
- The exact mechanism for deciding "is this tick a Layer-A-attempt tick," including what (if any) state must persist across `run_collector()` loop iterations.
- The new/changed collector params (name, default, how `run_scenario.py` would build and pass them) — described, not implemented.
- A decision on freshness-flag semantics: whether "we didn't attempt this tick" needs a different `*_fresh` value than "we attempted and timed out."
- A backward-compatibility decision for the ~16 existing scenario YAMLs that only set `poll_interval_seconds`.
- The unit-test additions this change would need, matching `experiments/test_topfull_throttle_collector.py`'s existing style.
- Named follow-up doc updates (`TOPFULL-THROTTLE-METRICS.md`, `METRICS-GATHERED.md`) as remaining work, not performed here.

**Out of scope (explicit)**

- Any actual code change to `topfull_throttle_collector.py`, `run_scenario.py`, or any scenario YAML. This is a spec-only task.
- Changing `PROXY_FETCH_TIMEOUT_SECONDS` (0.8 s) — that budget applies unchanged to whichever tick does attempt Layer A.
- Splitting `/thresholds` and `/stats` into two *independently* configurable cadences. `/thresholds` (`ReqThreshold()`, reads `limiterTable[api].Limit()`, no mutex) is cheap; `/stats` (`ReqStat()`, calls `mapStats[api].currentRPS()` under the same per-API `sync.Mutex` every admitted Locust request also takes in `StatsModule.logRequest()`) is the contended one. This spec keeps **one** Layer A interval covering both URLs together (matching how the user narrowed the prior discussion to "option 1" specifically) and states the finer per-endpoint split as an explicitly out-of-scope future refinement (§3.5).
- Any change to Layer B (`scrape_cadvisor_cpu`, `detect_metrics`, `topfull_detect.csv`) — it keeps its existing 1 s grid, columns, and semantics untouched.
- Any change to goproxy itself (an out-of-band admin port on a separate listener, or a longer-wait background `/stats` thread inside goproxy) — a bigger TopFull patch already noted as separate/out-of-scope in earlier discussion ([TOPFULL-THROTTLE-METRICS.md](../../../Guides%20and%20Info/TOPFULL-THROTTLE-METRICS.md) "Follow-up not implemented").
- Backfilling `campaign_48/` or `august_38/` — future runs only, same as every prior collector change in this project.

---

## 2. Current behavior (baseline)

`experiments/topfull_throttle_collector.py` today:

- `run_collector()` reads a single `poll_interval_seconds` (default `DEFAULT_POLL_INTERVAL_SECONDS = 1`) from params, and drives everything off it: `sleep_until_next_tick(interval)` → `tick_timestamp(interval)` → `poll_once(...)`, once per tick, no other state carried across iterations except the single `LastGoodThrottle` instance.
- `poll_once()` runs Layer A and Layer B **concurrently** inside one `ThreadPoolExecutor(max_workers=3)`: `fetch_proxy_admin()` (which itself fans `/thresholds` and `/stats` out to a nested `ThreadPoolExecutor(max_workers=2)`) and `scrape_cadvisor_cpu()`. Layer B does not wait on Layer A's pool slot (`TestLayerBNotBlocked` already asserts this).
- Every tick, regardless of whether the Layer A fetch succeeded, `resolve_thresholds()` / `resolve_admitted()` write exactly one row per Locust API to `topfull_throttle.csv`, using the freshly-fetched value when available (`threshold_fresh=1`/`admitted_fresh=1`) or the `LastGoodThrottle`-carried value (`*_fresh=0`) when the fetch failed or timed out inside `PROXY_FETCH_TIMEOUT_SECONDS` (0.8 s).
- `topfull_detect.csv` gets one row per `DETECT_SERVICES` entry every tick, unconditionally (Layer B has no failure-carry logic needed at this cadence — it doesn't compete for `:8090`).

**The problem, restated precisely:** because both layers share `poll_interval_seconds=1`, Layer A *attempts* a live `/thresholds`+`/stats` fetch every single second even when the process is in a state (sustained overload) where that attempt is unlikely to complete in time and is itself extra load on the exact resource (`:8090`'s accept queue + `StatsModule` mutex) whose contention is the object of study. [2026-09-11-slo-fail-and-mu-estimator-design.md](2026-09-11-slo-fail-and-mu-estimator-design.md) §3/§8 measured only ~24.6% of Layer A ticks getting a fresh scrape in one S2 run, and a ~186 ms Locust `getcart` P95 delta (2648 ms with mesh+throttle collectors on vs 2462 ms off) attributable in part to this and the mesh collector — secondary to the ~1.4–1.8 s direct-path cost that exists with no collectors running at all, but not zero. Reducing *how often* Layer A is attempted (not how long each attempt waits) is the lever this spec pulls.

---

## 3. Proposed design

### 3.1 New param: `layer_a_poll_interval_seconds`

- `poll_interval_seconds` keeps its existing meaning and default (`1`): the wall-clock grid for Layer B's cAdvisor scrape, `topfull_detect.csv` row cadence, **and** `topfull_throttle.csv` row cadence (one row per API, every tick, unchanged — the CSV keeps its full 1 s resolution and is still joinable with `service_edges.csv` / `service_inbound.csv` / `resource_usage.csv` on `timestamp`).
- A new param, `layer_a_poll_interval_seconds` (default **5**), governs only how often a *live* `/thresholds`+`/stats` fetch is attempted. It must be a whole multiple of `poll_interval_seconds` — practically always true since `poll_interval_seconds` stays `1` in every scenario YAML.
- On ticks where this is not a Layer-A-attempt tick, the row written to `topfull_throttle.csv` this tick is the `LastGoodThrottle`-carried value with `threshold_fresh=0` / `admitted_fresh=0` — reusing the existing carry-forward machinery unchanged. On ticks where it *is* an attempt tick, behavior is identical to today: fetch (bounded by the unchanged 0.8 s `PROXY_FETCH_TIMEOUT_SECONDS`), and set `*_fresh=1` on success or `0` on timeout/failure, exactly as now.

### 3.2 Attempt-cadence mechanism

Two mechanisms were considered:

1. **Tick counter modulo.** `run_collector()` keeps an integer `polls` counter (it already has one) and computes `layer_a_ratio = layer_a_poll_interval_seconds // poll_interval_seconds` once at startup; a tick is a Layer A attempt tick iff `polls % layer_a_ratio == 0`. Simple, but it is state that must be threaded through `run_collector()` → `poll_once()` (a new parameter or closure), and — because it counts *loop iterations*, not wall-clock time — it silently drifts from "every 5th wall-clock second" if any single `poll_once()` call ever runs long enough to skip a `sleep_until_next_tick` cycle (unlikely given `sleep_until_next_tick` re-anchors to `time.time()` every call, but not impossible under load).
2. **Wall-clock-aligned modulo (recommended).** Reuse the tick's already-aligned epoch second — the same floor-to-`poll_interval_seconds` value `tick_timestamp()` derives internally — and attempt Layer A iff `int(aligned_epoch) % layer_a_poll_interval_seconds == 0`. This needs **no new persistent state** across loop iterations: it is a pure function of the current tick's wall-clock time, computed fresh every call, exactly like `tick_timestamp()`/`sleep_until_next_tick()` already are. It self-heals after any delay or process restart (the next 5 s-aligned boundary is always well-defined) and keeps the same "derive everything from wall-clock, not from a step count" philosophy the collector already uses for tick alignment (§2 of [2026-09-09-topfull-throttle-collector-design.md](2026-09-09-topfull-throttle-collector-design.md)).

**Recommendation: mechanism 2.** It is simpler (no new field on `run_collector`'s local state, no new constructor parameter to thread through `poll_once`), matches the existing wall-clock-alignment convention, and is robust to a collector restart mid-run (a resumed collector picks back up on the natural 5 s boundaries rather than needing to know how many polls happened before it restarted). Concretely, `poll_once()` gains a boolean `attempt_layer_a: bool` parameter (computed by the caller from the tick's aligned epoch and `layer_a_poll_interval_seconds`, the same way `tick_timestamp()` computes its floor); when `False`, `poll_once()` skips `fetch_proxy_admin()` entirely (no thread pool submission, no network call) and calls `resolve_thresholds(None, ...)` / `resolve_admitted(None, ...)` directly — the same code path `poll_once()` already takes today when a real fetch times out, so `LastGoodThrottle` and the freshness-flag logic need **zero** changes. Layer B's `scrape_cadvisor_cpu()` submission to the thread pool is unconditional, every tick, unchanged.

`run_collector()`'s only change is computing `attempt_layer_a` from the tick's aligned epoch and `layer_a_poll_interval_seconds` before calling `poll_once()`, and reading the new param (with its default) alongside the existing `poll_interval_seconds` read.

### 3.3 Freshness-flag semantics decision

**Decision: keep the existing binary `0`/`1` semantics unchanged — do not add a third state.** "This tick was not attempted" and "this tick was attempted and timed out" both mean the same thing to a downstream analyst: *the value in this row is carried from an earlier successful fetch, not measured this second.* Any consumer that already does the documented thing — filter `admitted_fresh==1` before treating `admitted_rps` as a true per-second measurement (per `TOPFULL-THROTTLE-METRICS.md`'s existing guidance) — behaves correctly with no changes, whether the `0` came from a skipped attempt or a failed one. Adding a distinguishing value (e.g. `2` for "not attempted" vs `0` for "attempted, failed") would be schema-breaking for that filter convention and buys no new analysis capability this project currently needs (nothing today asks "how many ticks did we even try," only "is this row's value fresh").

This does slightly reduce the *diagnostic* granularity: previously, a run of `threshold_fresh=0` rows meant "Layer A kept timing out" (contention evidence); after this change, most `*_fresh=0` rows under the default `layer_a_poll_interval_seconds=5` will mean "we didn't try this tick" (by design), with genuine timeouts now a rarer subset of those `0`s. That distinction is recoverable if ever needed — the collector's own log already lines up `WARNING  …fetch failed` only on genuine failures, never on skipped ticks, so `topfull_throttle_collector.log` (not the CSV) remains the place to distinguish "skipped by design" from "attempted and failed" post hoc, if that question ever comes up. The CSV schema itself does not need a new column for it.

### 3.4 Backward compatibility decision

**Decision: `layer_a_poll_interval_seconds` defaults to `5` when absent from a scenario YAML's `topfull_throttle_collector` block — it does *not* default to matching `poll_interval_seconds`.** Rationale:

- The whole point of this change is to reduce `:8090` contention *without* requiring every one of the ~16 scenario YAMLs to be hand-edited (the task's own framing: "without requiring every YAML to be edited"). A default that silently preserves the old 1:1 behavior would mean nobody gets the improvement unless they remember to opt in — defeating the purpose for exactly the runs (S2/S3/S4 sustained-overload scenarios) that motivated it.
- The change is safe to apply by default: it can only ever *reduce* attempted Layer A fetches, never increase them, and every consumer of `topfull_throttle.csv` is already expected to check `*_fresh` before trusting a row (per existing guidance) — so no existing analysis code silently regresses in correctness, only in how often it sees a `_fresh=1` row under light load (S1 normal-op, where Layer A was mostly succeeding anyway, and where a 5 s cadence still gives 1-in-5 fresh coverage — plenty for a scenario with no throttling pressure in the first place).
- `run_scenario.py`'s `start_topfull_throttle_collector()` (§4) would read `ttc_cfg.get("layer_a_poll_interval_seconds", 5)` the same way it already reads `ttc_cfg.get("poll_interval_seconds", 1)` — an existing YAML with only `poll_interval_seconds: 1` set continues to run unmodified (Layer B/CSV cadence identical) but automatically gets the Layer A cadence improvement with no edit required. A YAML that explicitly wants the old 1:1 behavior can still set `layer_a_poll_interval_seconds: 1`.

### 3.5 Explicitly out of scope: per-endpoint (`/thresholds` vs `/stats`) split

Noted in §1 and repeated here because the background material raises it: `/thresholds` (`ReqThreshold()`) is lock-free against `StatsModule` and cheap; `/stats` (`ReqStat()`) is the one contending on the per-API mutex that every admitted Locust request also takes. A theoretically tighter design could poll `/thresholds` at (or near) the original 1 s cadence — since it doesn't contend — while polling only `/stats` at the slower cadence. This spec's recommended default is **one Layer A interval covering both URLs together**, per the user's prior narrowing to "option 1." If this finer split is wanted later, it would need: two independent freshness flags already exist per-column (`threshold_fresh`, `admitted_fresh` are already separate), so the CSV schema would not need to change — only `fetch_proxy_admin()` would need to become two independently-scheduled fetches instead of one paired parallel fetch, and `poll_once()` would need two `attempt_*` booleans instead of one. Left as a named future refinement, not designed further here.

---

## 4. Wiring (described, not implemented)

For a future implementer, the shape of the change in each touched location:

- **`experiments/topfull_throttle_collector.py`**
  - `run_collector()`: read `layer_a_poll_interval_seconds` from `params` (default `5`) alongside the existing `interval` read; each loop iteration, compute `attempt_layer_a` from the tick's aligned epoch (§3.2) and pass it to `poll_once()`.
  - `poll_once()`: accept the new `attempt_layer_a: bool` parameter; when `False`, skip the `fetch_proxy_admin` submission and call `resolve_thresholds(None, ...)` / `resolve_admitted(None, ...)` directly (same path as a real timeout today). No signature change needed for `fetch_proxy_admin`, `resolve_thresholds`, `resolve_admitted`, `LastGoodThrottle`, `write_throttle_csv`, or anything in Layer B.
  - Add a startup log line analogous to the existing `START  poll_interval=%ss` that also reports `layer_a_poll_interval=%ss`, so `topfull_throttle_collector.log` documents which cadence a given run used (useful once campaign runs mix defaults across dates).

- **`experiments/run_scenario.py`** (`start_topfull_throttle_collector()`): add `"layer_a_poll_interval_seconds": int(ttc_cfg.get("layer_a_poll_interval_seconds", 5))` to the `params` dict written to `/tmp/topfull_throttle_params.json`, alongside the existing `poll_interval_seconds` and `cpu_quotas` keys. `run_manifest.json`'s existing `"topfull_throttle_collector": cfg.get("topfull_throttle_collector", {})` capture needs no change — it already snapshots the whole YAML block, so the new key shows up automatically once a YAML sets it.

- **Scenario YAMLs**: no edits required by default (§3.4). A scenario that wants a non-default Layer A cadence (e.g. an even slower attempt rate for S2/S3/S4 sustained-overload runs, or `layer_a_poll_interval_seconds: 1` to reproduce today's behavior for an A/B comparison run) adds one line to its existing `topfull_throttle_collector:` block:

    ```yaml
    topfull_throttle_collector:
      enabled: true
      poll_interval_seconds: 1
      layer_a_poll_interval_seconds: 5   # new, optional; defaults to 5 if omitted
    ```

- **Docs (follow-up, not done in this task):** `Guides and Info/TOPFULL-THROTTLE-METRICS.md`'s collector section and `Guides and Info/METRICS-GATHERED.md`'s `topfull_throttle.csv` description both currently describe Layer A and Layer B as sharing one 1 s cadence and describe `*_fresh` purely in terms of timeout-carry. Both need a paragraph documenting: (a) the split cadence and its default, (b) that `*_fresh=0` now also covers "not attempted this tick by design," not only "attempted and timed out" (§3.3), and (c) that `topfull_throttle.csv`'s row cadence is unchanged (still 1 s, still joinable) even though the *live* fraction of rows is now lower by design under the default.

---

## 5. Testing strategy

New/changed tests in `experiments/test_topfull_throttle_collector.py`, following its existing patterns (injected `run_cmd`/`fetch_url`, `SimpleNamespace` results, tiny fixture data, no real sleeps):

- **Attempt-cadence unit test (pure function, no I/O):** a small helper — call it `is_layer_a_attempt_tick(aligned_epoch_seconds: int, layer_a_interval: int) -> bool` (or equivalent, whatever the implementer names the extracted predicate) — tested directly: given `poll_interval_seconds=1`, `layer_a_poll_interval_seconds=5`, and epochs `0, 1, 2, 3, 4, 5, 6, …, 9`, assert it returns `True` only for epochs `0` and `5`. Mirrors `TestTickTimestamp`'s style of asserting on fixed `EPOCH`-relative offsets.
- **`poll_once` call-count test (mirrors `TestParallelAdminFetch` / `TestLastGoodThrottle`):** drive `run_collector()` (or call `poll_once()` directly in a loop over 10 fixed timestamps spanning two 5-tick windows) with a `fetch_url` that records every URL it's called with. Assert the admin fetch (`/thresholds`+`/stats`) is invoked exactly **2 times** total (ticks 0 and 5 of the 10 simulated ticks) while `topfull_throttle.csv` still accumulates **10** rows per API (one per tick, same as today) — the 8 non-attempt ticks carry `LastGoodThrottle` values with `*_fresh=0`.
- **Layer B unaffected test:** in the same 10-tick simulation, assert `topfull_detect.csv` accumulates exactly 10 × `len(DETECT_SERVICES)` rows regardless of the Layer A cadence, and that `scrape_cadvisor_cpu`/cAdvisor-fetching `fetch_url` calls happen on every one of the 10 ticks — confirming Layer B's cadence and call count are untouched by this change.
- **Freshness-flag test on a skipped (not failed) tick:** a fixture where the admin fetch would *succeed* if called (fetch_url returns valid `SAMPLE_STATS`/`SAMPLE_THRESHOLDS`), but the tick is a non-attempt tick per the cadence — assert `topfull_throttle.csv` for that tick has `threshold_fresh="0"` / `admitted_fresh="0"` and carries the previous attempt tick's values (extends `TestLastGoodThrottle`'s existing carry-forward assertions to the "skipped by design" case, not just the "attempted and timed out" case already covered).
- **Backward-compat / default test:** a fixture with only `{"poll_interval_seconds": 1}` in `params` (no `layer_a_poll_interval_seconds` key at all) run through `run_collector(..., max_polls=10)` — assert the admin fetch is invoked exactly 2 times over 10 polls (i.e. the implicit default of `5` took effect), confirming an untouched existing scenario YAML gets the new behavior without an explicit key.
- **Opt-out / explicit-1 test:** a fixture with `{"poll_interval_seconds": 1, "layer_a_poll_interval_seconds": 1}` — assert the admin fetch is invoked on every one of the 10 polls (i.e. explicit `1` reproduces today's exact behavior), for anyone who wants an A/B run against the old cadence.

No test needs to touch real sleeping, real network I/O, or real subprocess calls — same style as the existing suite.

---

## 6. Non-goals (recap)

- `PROXY_FETCH_TIMEOUT_SECONDS` (0.8 s) — unchanged.
- `/thresholds` vs `/stats` independent cadences — explicitly deferred (§3.5).
- Layer B (`scrape_cadvisor_cpu`, `detect_metrics`, `topfull_detect.csv` schema/cadence) — untouched.
- goproxy itself (out-of-band admin port, internal background `/stats` thread) — untouched; that remains a separate, larger, out-of-scope TopFull patch idea noted previously.
- Backfilling any existing campaign folder.

---

## 7. Success criteria

- A future implementation of this spec reduces the number of `/thresholds`+`/stats` fetch *attempts* against `:8090` to roughly `1/layer_a_poll_interval_seconds` of today's rate under the default (`5`), while `topfull_throttle.csv` keeps writing one row per API every `poll_interval_seconds` (unchanged 1 s cadence) and `topfull_detect.csv` is byte-for-byte unaffected in cadence and columns.
- Every existing scenario YAML that sets only `poll_interval_seconds` continues to run with no edits and automatically gets the reduced Layer A attempt rate.
- `threshold_fresh`/`admitted_fresh` remain binary `0`/`1` columns; no schema change to either CSV.
- A follow-up run (S2 or similar sustained-overload scenario) with this implemented should show a materially higher fraction of *attempted* Layer A ticks landing inside the 0.8 s budget than the ~24.6% baseline measured pre-change — because attempts are now spaced out instead of firing every second into a saturated `:8090`. (Confirming this empirically is future work, not part of this spec.)

---

## Status

Design spec only (this document). No implementation, YAML, or other doc has been changed as part of producing this spec.
