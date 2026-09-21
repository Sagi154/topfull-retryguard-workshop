# Mesh Collector Per-Tick IP Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gap the 2026-09-20 Ron-Nezer migration review flagged as a merge-blocker: `envoy_retry_collector.py`'s pod-IP cache only refreshes when an HTTP fetch to a cached IP *fails*, so a healthy HPA-driven replica addition (e.g. `frontend` scaling 1→2 with the original pod still answering) is never noticed and that replica's mesh stats are silently missing from `service_edges.csv`/`service_inbound.csv` forever. This plan replaces the failure-triggered, per-service reseed with an unconditional, whole-namespace pod-list refresh on every poll tick after the first.

**Architecture:** Add three small pure functions (`fetch_pod_list`, `pod_service_name`, `pod_ips_from_pod_list`) that mirror the exact `kubectl get pods -n default -o json` + group-by-service-prefix pattern already proven safe at 1-second cadence in `topfull_throttle_collector.py`'s `_pod_list`/`container_ids_from_pod_list` and `resource_usage_collector.py`'s per-poll `fetch_deployments_json`. Compose them into `refresh_ip_cache()`, which replaces `envoy_retry_collector.py`'s `ip_cache` dict **in place** with a fresh snapshot every poll tick except the very first (tick 0 keeps using `run_scenario.py`'s one-time seed, unchanged, with zero kubectl calls — that part is explicitly out of scope and stays as-is). Wire this into `poll_once()`, and delete the old failure-triggered, per-service, rate-limited reseed logic from `_apply_scrape_results()` since it is now fully superseded.

**Tech Stack:** Python 3, stdlib `unittest` (no pytest — this repo has none), mocked `run_cmd`/`fetch_url` callables (no live kubectl/network access needed for any step in this plan).

## Global Constraints

- **Test framework is stdlib `unittest`.** Run with `python experiments/test_envoy_retry_collector.py -v` from the repo root. Do not introduce `pytest`.
- **Do not modify `run_scenario.py` or any `experiments/configs/*.yaml`.** The team decided to keep `run_scenario.py`'s one-time `discover_service_pod_ips()` seed exactly as-is; only the *collector's own* per-tick behavior changes. `run_scenario.py`'s `discover_service_pod_ips()` and `test_run_scenario.py`'s `TestDiscoverServicePodIps`/`test_start_uploads_pod_ips_on_master` tests are unaffected and must still pass unchanged.
- **Only two files change:** `experiments/envoy_retry_collector.py` and `experiments/test_envoy_retry_collector.py`. No other collector, no `TopFull/` submodule, no `experiments/results/`.
- **No live-cluster access required for any task in this plan.** Every test mocks `run_cmd` (kubectl) and `fetch_url` (HTTP), matching this test file's existing style (see `TestPollOnceNetwork`, `TestTier2Reseed` in the current file).
- **Cost model, already accepted:** this plan deliberately adds one extra `kubectl get pods -n default -o json` call per poll tick, from `poll_index >= 1` onward. This is the same call shape and cadence `topfull_throttle_collector.py`'s `_pod_list()` already issues every second in production today — this plan does not need a new performance-validation task on top of that existing evidence.
- **Leave `discover_pod_ip()` and `discover_pod_ips()` (the old per-service, `-l app=X` functions) and their existing tests (`TestDiscoverPodIps`, and any `discover_pod_ip` tests) untouched.** After Task 2, nothing in production code calls `discover_pod_ips()` any more (it becomes dead code, same as `discover_pod_ip()` already was per the 2026-09-20 review). Do not delete them — this mirrors the review's own conclusion that leftover dead code here is "not a defect," and removing it is unrelated scope.
- **`ip_cache` is always mutated in place, never reassigned.** `run_collector()` passes the same dict object into `poll_once()` on every tick and relies on this; every new/changed function in this plan (`refresh_ip_cache`) must mutate the dict it's given (`.clear()` + assignment), not return a new one.

---

### Task 1: Add whole-namespace pod-list discovery and in-place cache refresh (pure functions)

**Files:**
- Modify: `experiments/envoy_retry_collector.py` — insert new functions immediately after `join_ip_list()` (currently ends around line 572) and before `def discover_pod_ip(` (currently starts around line 575).
- Test: `experiments/test_envoy_retry_collector.py` — insert new test classes immediately after `class TestDiscoverPodIps(unittest.TestCase):` (currently ends around line 423, right before `class TestFetchStatsTextHttp`).

**Interfaces:**
- Consumes: nothing from later tasks.
- Produces (all new, consumed by Task 2):
  - `fetch_pod_list(run_cmd: Optional[CommandRunner] = None, namespace: str = NAMESPACE) -> Optional[dict]`
  - `pod_service_name(pod_name: str, services: List[str]) -> Optional[str]`
  - `pod_ips_from_pod_list(pod_list: dict, services: List[str]) -> Dict[str, List[str]]`
  - `refresh_ip_cache(ip_cache: Dict[str, str], services: List[str], run_cmd: Optional[CommandRunner] = None, namespace: str = NAMESPACE) -> None` (mutates `ip_cache` in place; returns `None`)

- [ ] **Step 1: Write the failing tests for `fetch_pod_list`**

In `experiments/test_envoy_retry_collector.py`, insert this new class right after the end of `class TestDiscoverPodIps(unittest.TestCase):` (i.e. right before `class TestFetchStatsTextHttp(unittest.TestCase):`):

```python
class TestFetchPodList(unittest.TestCase):
    def test_returns_parsed_json_on_success(self):
        def runner(cmd):
            return SimpleNamespace(
                returncode=0,
                stdout='{"items": [{"metadata": {"name": "frontend-abc"}}]}',
                stderr="",
            )

        result = erc.fetch_pod_list(run_cmd=runner)
        self.assertEqual(result, {"items": [{"metadata": {"name": "frontend-abc"}}]})

    def test_builds_whole_namespace_kubectl_command(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="{}", stderr="")

        erc.fetch_pod_list(run_cmd=runner)
        self.assertEqual(
            calls[0],
            ["kubectl", "get", "pods", "-n", "default", "-o", "json"],
        )

    def test_returns_none_on_nonzero_exit(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        self.assertIsNone(erc.fetch_pod_list(run_cmd=runner))

    def test_returns_none_on_exception(self):
        def runner(cmd):
            raise TimeoutError("timed out")

        self.assertIsNone(erc.fetch_pod_list(run_cmd=runner))

    def test_returns_none_on_invalid_json(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="not-json", stderr="")

        self.assertIsNone(erc.fetch_pod_list(run_cmd=runner))
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestFetchPodList -v`
Expected: `AttributeError: module 'envoy_retry_collector' has no attribute 'fetch_pod_list'` (5 errors).

- [ ] **Step 3: Implement `fetch_pod_list`**

In `experiments/envoy_retry_collector.py`, insert immediately after the end of `join_ip_list()`:

```python
def fetch_pod_list(
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> Optional[dict]:
    """
    One kubectl call for every pod in the namespace (all 11 Boutique
    services, every replica) — mirrors resource_usage_collector.py's
    fetch_deployments_json() and topfull_throttle_collector.py's
    _pod_list(), both of which already issue this exact call shape every
    poll tick in production. Returns None on any kubectl failure or
    malformed JSON so callers (refresh_ip_cache) can keep their
    last-known-good IP cache instead of going blind for one tick.
    """
    runner = run_cmd or default_run_cmd
    cmd = ["kubectl", "get", "pods", "-n", namespace, "-o", "json"]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  fetch pod list failed: %s", utc_now(), exc)
        return None
    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  fetch pod list exit=%s stderr=%s",
            utc_now(),
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None
    try:
        return json.loads(getattr(result, "stdout", "") or "{}")
    except json.JSONDecodeError:
        log.warning("%s  WARNING  fetch pod list returned invalid JSON", utc_now())
        return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python experiments/test_envoy_retry_collector.py TestFetchPodList -v`
Expected: `OK` (5 tests).

- [ ] **Step 5: Write the failing tests for `pod_service_name`**

Insert right after `class TestFetchPodList(unittest.TestCase):`:

```python
class TestPodServiceName(unittest.TestCase):
    def test_matches_exact_and_prefix(self):
        services = ["frontend", "checkoutservice"]
        self.assertEqual(
            erc.pod_service_name("frontend-abc123-11111", services), "frontend"
        )
        self.assertEqual(
            erc.pod_service_name("checkoutservice-def456-22222", services),
            "checkoutservice",
        )

    def test_no_match_returns_none(self):
        self.assertIsNone(erc.pod_service_name("istiod-abc123", ["frontend"]))

    def test_prefers_longest_matching_service_name(self):
        # Same tie-break rule as topfull_throttle_collector.py's
        # _pod_service_name, in case two service names ever overlap.
        services = ["cart", "cartservice"]
        self.assertEqual(
            erc.pod_service_name("cartservice-xyz-1", services), "cartservice"
        )
```

- [ ] **Step 6: Run the tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestPodServiceName -v`
Expected: `AttributeError: module 'envoy_retry_collector' has no attribute 'pod_service_name'` (3 errors).

- [ ] **Step 7: Implement `pod_service_name`**

In `experiments/envoy_retry_collector.py`, insert immediately after `fetch_pod_list()`:

```python
def pod_service_name(pod_name: str, services: List[str]) -> Optional[str]:
    """
    Match a pod name to one of `services` by Deployment-name prefix —
    identical rule to topfull_throttle_collector.py's _pod_service_name:
    longest service name checked first, so e.g. "cartservice-..." can't
    accidentally match a shorter, unrelated service name that happens to
    be a string prefix of it.
    """
    for svc in sorted(services, key=len, reverse=True):
        if pod_name == svc or pod_name.startswith(svc + "-"):
            return svc
    return None
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `python experiments/test_envoy_retry_collector.py TestPodServiceName -v`
Expected: `OK` (3 tests).

- [ ] **Step 9: Write the failing tests for `pod_ips_from_pod_list`**

Insert right after `class TestPodServiceName(unittest.TestCase):`:

```python
SAMPLE_POD_LIST_TWO_FRONTEND_REPLICAS = {
    "items": [
        {
            "metadata": {"name": "frontend-abc123-11111"},
            "status": {"phase": "Running", "podIP": "10.0.0.5"},
        },
        {
            "metadata": {"name": "frontend-abc123-22222"},
            "status": {"phase": "Running", "podIP": "10.0.0.9"},
        },
        {
            "metadata": {"name": "checkoutservice-def456-1"},
            "status": {"phase": "Running", "podIP": "10.0.0.20"},
        },
        {
            "metadata": {"name": "frontend-abc123-33333"},
            "status": {"phase": "Pending"},
        },
        {
            "metadata": {"name": "frontend-abc123-44444"},
            "status": {"phase": "Terminating", "podIP": "10.0.0.99"},
        },
    ],
}


class TestPodIpsFromPodList(unittest.TestCase):
    def test_groups_running_pods_by_service(self):
        ips = erc.pod_ips_from_pod_list(
            SAMPLE_POD_LIST_TWO_FRONTEND_REPLICAS, ["frontend", "checkoutservice"]
        )
        self.assertEqual(ips["frontend"], ["10.0.0.5", "10.0.0.9"])
        self.assertEqual(ips["checkoutservice"], ["10.0.0.20"])

    def test_excludes_pending_and_terminating_pods(self):
        ips = erc.pod_ips_from_pod_list(
            SAMPLE_POD_LIST_TWO_FRONTEND_REPLICAS, ["frontend"]
        )
        self.assertNotIn("10.0.0.99", ips["frontend"])
        self.assertEqual(len(ips["frontend"]), 2)

    def test_service_with_no_running_pods_is_empty_list_not_missing_key(self):
        ips = erc.pod_ips_from_pod_list({"items": []}, ["adservice"])
        self.assertEqual(ips["adservice"], [])
```

- [ ] **Step 10: Run the tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestPodIpsFromPodList -v`
Expected: `AttributeError: module 'envoy_retry_collector' has no attribute 'pod_ips_from_pod_list'` (3 errors).

- [ ] **Step 11: Implement `pod_ips_from_pod_list`**

In `experiments/envoy_retry_collector.py`, insert immediately after `pod_service_name()`:

```python
def pod_ips_from_pod_list(
    pod_list: dict, services: List[str]
) -> Dict[str, List[str]]:
    """
    Group every Running pod's IP by service, from one whole-namespace
    `kubectl get pods -o json` snapshot. Pending pods (no podIP yet) and
    Terminating pods (sidecar may already be shutting down, refusing new
    connections) are excluded. Unlike the retired per-service jsonpath
    discovery, this single call sees every replica of every service in
    one shot, so noticing a scaled-up replica never depends on a fetch
    to it failing first.
    """
    out: Dict[str, List[str]] = {s: [] for s in services}
    for item in pod_list.get("items") or []:
        name = (item.get("metadata") or {}).get("name") or ""
        svc = pod_service_name(name, services)
        if svc is None:
            continue
        status = item.get("status") or {}
        if status.get("phase") != "Running":
            continue
        pod_ip = status.get("podIP")
        if pod_ip:
            out[svc].append(pod_ip)
    return out
```

- [ ] **Step 12: Run the tests to verify they pass**

Run: `python experiments/test_envoy_retry_collector.py TestPodIpsFromPodList -v`
Expected: `OK` (3 tests).

- [ ] **Step 13: Write the failing tests for `refresh_ip_cache`**

Insert right after `class TestPodIpsFromPodList(unittest.TestCase):`:

```python
class TestRefreshIpCache(unittest.TestCase):
    def test_replaces_cache_with_fresh_snapshot(self):
        import json

        def runner(cmd):
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(SAMPLE_POD_LIST_TWO_FRONTEND_REPLICAS),
                stderr="",
            )

        cache = {"frontend": "10.0.0.1"}  # stale single IP
        erc.refresh_ip_cache(cache, ["frontend", "checkoutservice"], run_cmd=runner)
        self.assertEqual(cache["frontend"], "10.0.0.5,10.0.0.9")
        self.assertEqual(cache["checkoutservice"], "10.0.0.20")

    def test_kubectl_failure_leaves_cache_untouched(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="refused")

        cache = {"frontend": "10.0.0.1"}
        erc.refresh_ip_cache(cache, ["frontend"], run_cmd=runner)
        self.assertEqual(cache, {"frontend": "10.0.0.1"})

    def test_service_with_no_pods_is_dropped_from_cache(self):
        import json

        def runner(cmd):
            return SimpleNamespace(
                returncode=0, stdout=json.dumps({"items": []}), stderr=""
            )

        cache = {"frontend": "10.0.0.1"}
        erc.refresh_ip_cache(cache, ["frontend"], run_cmd=runner)
        self.assertEqual(cache, {})

    def test_mutates_in_place_same_object(self):
        cache = {"frontend": "10.0.0.1"}
        original_id = id(cache)

        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="refused")

        erc.refresh_ip_cache(cache, ["frontend"], run_cmd=runner)
        self.assertEqual(id(cache), original_id)
```

- [ ] **Step 14: Run the tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestRefreshIpCache -v`
Expected: `AttributeError: module 'envoy_retry_collector' has no attribute 'refresh_ip_cache'` (4 errors).

- [ ] **Step 15: Implement `refresh_ip_cache`**

In `experiments/envoy_retry_collector.py`, insert immediately after `pod_ips_from_pod_list()`:

```python
def refresh_ip_cache(
    ip_cache: Dict[str, str],
    services: List[str],
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> None:
    """
    Replace ip_cache **in place** with a fresh whole-namespace snapshot,
    so a healthy HPA-driven pod addition is scraped on the very next poll
    tick without needing a prior fetch failure (the bug the 2026-09-20
    Ron-Nezer migration review flagged: the old per-service, failure-
    triggered reseed never noticed a *successful* extra replica). On a
    kubectl failure this tick, ip_cache is left untouched — one bad tick
    keeps scraping last-known-good IPs rather than going blind.
    """
    pod_list = fetch_pod_list(run_cmd=run_cmd, namespace=namespace)
    if pod_list is None:
        return
    ips_by_service = pod_ips_from_pod_list(pod_list, services)
    ip_cache.clear()
    for service, ips in ips_by_service.items():
        if ips:
            ip_cache[service] = join_ip_list(ips)
```

- [ ] **Step 16: Run the tests to verify they pass**

Run: `python experiments/test_envoy_retry_collector.py TestRefreshIpCache -v`
Expected: `OK` (4 tests).

- [ ] **Step 17: Run the whole test file to confirm no regressions so far**

Run: `python experiments/test_envoy_retry_collector.py -v`
Expected: all pre-existing tests still `OK` (Task 1 only adds new functions; nothing existing calls them yet).

- [ ] **Step 18: Commit**

```bash
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "feat: add whole-namespace pod-list discovery and in-place IP cache refresh"
```

---

### Task 2: Wire per-tick refresh into `poll_once`, retire the failure-triggered reseed

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (`poll_once()`, `_apply_scrape_results()`)
- Test: `experiments/test_envoy_retry_collector.py` (replace `class TestTier2Reseed(unittest.TestCase):` with a new class)

**Interfaces:**
- Consumes: `refresh_ip_cache()` from Task 1.
- Produces: `poll_once()` keeps its exact existing signature (no new parameters) — later callers (`run_collector()`, `run_scenario.py`'s `start_envoy_retry_collector`) are unaffected. `_apply_scrape_results()`'s signature drops its now-unused trailing `run_cmd` parameter (private function, not called anywhere else in this codebase — confirmed no direct test references it).

- [ ] **Step 1: Write the failing tests for the new per-tick refresh behavior in `poll_once`**

In `experiments/test_envoy_retry_collector.py`, find this entire block and delete it:

```python
class TestTier2Reseed(unittest.TestCase):
    def test_fetch_failure_reseeds_new_ip_next_poll(self):
        import tempfile

        state = {"fetches": []}

        def fetch(url):
            state["fetches"].append(url)
            if "10.0.0.1" in url:
                return SimpleNamespace(returncode=1, stdout="", stderr="refused")
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        def runner(cmd):
            joined = " ".join(cmd)
            if "app=frontend" in joined:
                return SimpleNamespace(returncode=0, stdout="10.0.0.2\n", stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        cache = {"frontend": "10.0.0.1"}
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-13T12:00:00Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=0,
                tier2_warn_state={},
            )
            self.assertEqual(cache.get("frontend"), "10.0.0.2")
            self.assertFalse((record_path / "service_inbound.csv").exists())
            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-13T12:00:01Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=1,
                tier2_warn_state={},
            )
            inbound = list(csv.DictReader((record_path / "service_inbound.csv").open(newline="")))
        self.assertEqual(len(inbound), 1)
        self.assertTrue(any("10.0.0.2" in u for u in state["fetches"]))

    def test_reseed_is_rate_limited(self):
        import tempfile

        kubectl_calls = []

        def fetch(url):
            return SimpleNamespace(returncode=1, stdout="", stderr="refused")

        def runner(cmd):
            kubectl_calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="10.0.0.9\n", stderr="")

        cache = {"frontend": "10.0.0.1"}
        warn_state = {}
        with tempfile.TemporaryDirectory() as td:
            for i in range(5):
                erc.poll_once(
                    Path(td),
                    ["frontend"],
                    timestamp="2026-09-13T12:00:00Z",
                    run_cmd=runner,
                    fetch_url=fetch,
                    ip_cache=cache,
                    poll_index=i,
                    tier2_warn_state=warn_state,
                )
        self.assertEqual(len(kubectl_calls), 1)

    def test_partial_failure_reseed_replaces_full_ip_list(self):
        import tempfile

        def fetch(url):
            if "10.0.0.1" in url:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="refused")

        def runner(cmd):
            joined = " ".join(cmd)
            if "app=frontend" in joined:
                # Cluster now reports 2 healthy replica IPs.
                return SimpleNamespace(returncode=0, stdout="10.0.0.1\n10.0.0.3\n", stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        cache = {"frontend": "10.0.0.1,10.0.0.2"}
        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["frontend"],
                timestamp="2026-09-20T12:00:00Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=0,
                tier2_warn_state={},
            )
        self.assertEqual(cache.get("frontend"), "10.0.0.1,10.0.0.3")
```

Replace it with:

```python
class TestPollOnceIpCacheRefresh(unittest.TestCase):
    def test_first_tick_uses_seeded_cache_without_any_kubectl_call(self):
        import tempfile

        kubectl_calls = []

        def runner(cmd):
            kubectl_calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="{}", stderr="")

        def fetch(url):
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        cache = {"frontend": "192.168.1.10"}
        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["frontend"],
                timestamp="2026-09-21T12:00:00Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=0,
                tier2_warn_state={},
            )
        self.assertEqual(kubectl_calls, [])
        self.assertEqual(cache, {"frontend": "192.168.1.10"})

    def test_healthy_scale_up_is_scraped_next_tick_with_zero_fetch_failures(self):
        import json
        import tempfile

        pod_list = {
            "items": [
                {
                    "metadata": {"name": "frontend-abc-11111"},
                    "status": {"phase": "Running", "podIP": "192.168.1.10"},
                },
                {
                    "metadata": {"name": "frontend-abc-22222"},
                    "status": {"phase": "Running", "podIP": "192.168.1.11"},
                },
            ],
        }

        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout=json.dumps(pod_list), stderr="")

        fetch_log = []

        def fetch(url):
            fetch_log.append(url)
            # Both replicas answer successfully — no fetch failure at all,
            # unlike the retired reseed mechanism this test replaces.
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        cache = {"frontend": "192.168.1.10"}  # seeded with only the original replica
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-21T12:00:01Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=1,
                tier2_warn_state={},
            )
            inbound = list(
                csv.DictReader((record_path / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual(cache["frontend"], "192.168.1.10,192.168.1.11")
        self.assertEqual(len(fetch_log), 2)
        self.assertEqual(len(inbound), 1)
        self.assertEqual(inbound[0]["total"], "400")  # 200 + 200, both replicas summed

    def test_refresh_runs_every_tick_from_poll_index_one_onward(self):
        import json
        import tempfile

        kubectl_calls = []

        def runner(cmd):
            kubectl_calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout=json.dumps({"items": []}), stderr="")

        def fetch(url):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        cache = {}
        with tempfile.TemporaryDirectory() as td:
            for i in range(5):
                erc.poll_once(
                    Path(td),
                    ["frontend"],
                    timestamp="2026-09-21T12:00:00Z",
                    run_cmd=runner,
                    fetch_url=fetch,
                    ip_cache=cache,
                    poll_index=i,
                    tier2_warn_state={},
                )
        # poll_index 0 skips the refresh (seeded tick); 1,2,3,4 each refresh
        # once — the accepted cost model (one whole-namespace kubectl call
        # per tick), not rate-limited like the retired per-service reseed.
        self.assertEqual(len(kubectl_calls), 4)

    def test_kubectl_failure_this_tick_keeps_previous_cache_and_keeps_scraping(self):
        import tempfile

        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="refused")

        def fetch(url):
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        cache = {"frontend": "192.168.1.10"}
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-21T12:00:01Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=1,
                tier2_warn_state={},
            )
            inbound = list(
                csv.DictReader((record_path / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual(cache, {"frontend": "192.168.1.10"})  # untouched, not wiped
        self.assertEqual(len(inbound), 1)  # scrape still happened, using the old IP

    def test_departed_service_is_dropped_from_cache_next_tick(self):
        import json
        import tempfile

        pod_list = {"items": []}  # checkoutservice's pod is gone this tick

        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout=json.dumps(pod_list), stderr="")

        def fetch(url):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        cache = {"checkoutservice": "10.0.0.50"}
        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["checkoutservice"],
                timestamp="2026-09-21T12:00:01Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=1,
                tier2_warn_state={},
            )
        self.assertEqual(cache, {})
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestPollOnceIpCacheRefresh -v`
Expected: failures — e.g. `test_first_tick_uses_seeded_cache_without_any_kubectl_call` fails because `poll_once` doesn't call `refresh_ip_cache` yet, but also because the *old* code path (still calling `discover_pod_ips` on tier2 failures) may cause unrelated kubectl calls in some of the other new tests. All 5 should currently fail or error — this is expected; do not try to make them pass without Step 3's implementation change.

- [ ] **Step 3: Wire `refresh_ip_cache` into `poll_once`, and simplify `_apply_scrape_results`**

In `experiments/envoy_retry_collector.py`, find this exact function:

```python
def poll_once(
    record_path: Path,
    services: List[str],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[HttpFetcher] = None,
    ip_cache: Optional[Dict[str, str]] = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    poll_index: int = 0,
    tier2_warn_state: Optional[Dict[str, int]] = None,
) -> None:
    if ip_cache is None:
        ip_cache = {}
    if tier2_warn_state is None:
        tier2_warn_state = {}
    fetcher = fetch_url or default_fetch_url
    edges_path = record_path / "service_edges.csv"
    inbound_path = record_path / "service_inbound.csv"
    workers = max(1, int(max_workers or DEFAULT_MAX_WORKERS))

    def _submit(service: str) -> ServiceScrapeResult:
        return scrape_one_service(service, ip_cache.get(service), fetcher)

    results: List[ServiceScrapeResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_submit, service): service for service in services}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                svc = futs[fut]
                log.warning("%s  WARNING  scrape %s raised: %s", utc_now(), svc, exc)
    _apply_scrape_results(
        results,
        ip_cache,
        edges_path,
        inbound_path,
        timestamp,
        poll_index,
        tier2_warn_state,
        run_cmd,
    )
```

Replace it with:

```python
def poll_once(
    record_path: Path,
    services: List[str],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[HttpFetcher] = None,
    ip_cache: Optional[Dict[str, str]] = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    poll_index: int = 0,
    tier2_warn_state: Optional[Dict[str, int]] = None,
) -> None:
    if ip_cache is None:
        ip_cache = {}
    if tier2_warn_state is None:
        tier2_warn_state = {}
    # Tick 0 uses run_scenario.py's one-time seed as-is (zero kubectl calls,
    # matching today's start-of-run behavior). Every later tick refreshes
    # the whole cache from a fresh whole-namespace pod list, so a healthy
    # HPA-driven replica addition is scraped on the very next tick without
    # needing a prior fetch failure first.
    if poll_index > 0:
        refresh_ip_cache(ip_cache, services, run_cmd=run_cmd)
    fetcher = fetch_url or default_fetch_url
    edges_path = record_path / "service_edges.csv"
    inbound_path = record_path / "service_inbound.csv"
    workers = max(1, int(max_workers or DEFAULT_MAX_WORKERS))

    def _submit(service: str) -> ServiceScrapeResult:
        return scrape_one_service(service, ip_cache.get(service), fetcher)

    results: List[ServiceScrapeResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_submit, service): service for service in services}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                svc = futs[fut]
                log.warning("%s  WARNING  scrape %s raised: %s", utc_now(), svc, exc)
    _apply_scrape_results(
        results,
        ip_cache,
        edges_path,
        inbound_path,
        timestamp,
        poll_index,
        tier2_warn_state,
    )
```

Then find this exact function (immediately below `poll_once`):

```python
def _apply_scrape_results(
    results: List[ServiceScrapeResult],
    ip_cache: Dict[str, str],
    edges_path: Path,
    inbound_path: Path,
    timestamp: str,
    poll_index: int,
    tier2_warn_state: Dict[str, int],
    run_cmd: Optional[CommandRunner] = None,
) -> None:
    for result in sorted(results, key=lambda r: r.service):
        if result.evict_ip:
            ip_cache.pop(result.service, None)
        if result.warning:
            if "tier2" in result.warning:
                if should_log_tier2(result.service, poll_index, tier2_warn_state):
                    log.warning("%s  WARNING  %s", utc_now(), result.warning)
                    new_ips = discover_pod_ips(result.service, run_cmd=run_cmd)
                    if new_ips:
                        ip_cache[result.service] = join_ip_list(new_ips)
            else:
                log.warning("%s  WARNING  %s", utc_now(), result.warning)
        if result.edges is not None and result.inbound is not None:
            write_edges_csv(edges_path, timestamp, result.service, result.edges)
            write_inbound_csv(inbound_path, timestamp, result.service, result.inbound)
```

Replace it with:

```python
def _apply_scrape_results(
    results: List[ServiceScrapeResult],
    ip_cache: Dict[str, str],
    edges_path: Path,
    inbound_path: Path,
    timestamp: str,
    poll_index: int,
    tier2_warn_state: Dict[str, int],
) -> None:
    for result in sorted(results, key=lambda r: r.service):
        if result.evict_ip:
            # Only matters on tick 0 (before the first refresh_ip_cache
            # call ever runs) — every later tick already rebuilds ip_cache
            # from scratch in poll_once, so a stale/dead IP cannot survive
            # past the next tick regardless of this eviction.
            ip_cache.pop(result.service, None)
        if result.warning:
            if "tier2" in result.warning:
                # Rate-limited log line only now — rediscovery itself is
                # handled unconditionally every tick by refresh_ip_cache()
                # in poll_once, not by this failure signal.
                if should_log_tier2(result.service, poll_index, tier2_warn_state):
                    log.warning("%s  WARNING  %s", utc_now(), result.warning)
            else:
                log.warning("%s  WARNING  %s", utc_now(), result.warning)
        if result.edges is not None and result.inbound is not None:
            write_edges_csv(edges_path, timestamp, result.service, result.edges)
            write_inbound_csv(inbound_path, timestamp, result.service, result.inbound)
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `python experiments/test_envoy_retry_collector.py TestPollOnceIpCacheRefresh -v`
Expected: `OK` (5 tests).

- [ ] **Step 5: Run the whole test file to confirm no regressions**

Run: `python experiments/test_envoy_retry_collector.py -v`
Expected: `OK`, all tests pass — including every pre-existing class (`TestParseEdges`, `TestParseInbound`, `TestScrapeOneServiceHttp`, `TestPollOnceNetwork`, `TestPollOnceThreadPoolSerialWrites`, `TestRunCollectorNetwork`, etc.), since none of them pass `poll_index > 0` and are therefore unaffected by the new refresh branch. `TestTier2Reseed` no longer exists (replaced in Step 1); nothing else references it.

- [ ] **Step 6: Run the sibling collector test files to confirm this plan touched nothing else**

Run: `python experiments/test_run_scenario.py -v 2>&1 | tail -5` and `python experiments/test_resource_usage_collector.py -v 2>&1 | tail -5` and `python experiments/test_topfull_throttle_collector.py -v 2>&1 | tail -5`
Expected: `OK` on all three — this plan never touches `run_scenario.py` or the other two collectors, so any pre-existing pass/fail state there is unrelated to this change and must be identical before and after.

- [ ] **Step 7: Commit**

```bash
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "fix: refresh mesh collector IP cache every poll tick instead of only on fetch failure"
```

---

## Self-review

**1. Spec coverage.** The one concrete requirement from this conversation — "the frontend mesh collector should be accurate also with added pods, not just the first replica, without periodic-rediscovery blind windows, and keep `run_scenario.py`'s one-time seed as-is, with the collector ignoring that seed after the first tick" — is fully covered: Task 1 builds the whole-namespace discovery primitives; Task 2 wires them in so `poll_index == 0` uses the seed untouched (zero kubectl calls, tested explicitly) and every `poll_index >= 1` tick refreshes unconditionally (tested explicitly, including the exact "healthy scale-up, zero fetch failures" case the 2026-09-20 review flagged as unproven). The accepted cost model (one extra `kubectl get pods -o json` call per tick from `poll_index >= 1`) is documented as a Global Constraint, not silently introduced.

**2. Placeholder scan.** Every step has complete, runnable code — no `TODO`, no "add error handling," no "similar to Task 1." Task 2's `poll_once`/`_apply_scrape_results` replacements are the full function bodies, not diffs described in prose.

**3. Type/signature consistency.** `poll_once(...)` keeps its exact existing signature across both tasks — no caller (`run_collector`, any test) needs to change how it invokes `poll_once`. `_apply_scrape_results`'s dropped `run_cmd` parameter is verified (Task 2 background) to have no direct test caller, since it's a private (`_`-prefixed) function only ever reached through `poll_once`. `refresh_ip_cache`'s `Dict[str, str]` / `List[str]` types match `ip_cache`'s existing type everywhere else in the file (`join_ip_list`, `parse_ip_list`, `scrape_one_service`). `fetch_pod_list`'s `Optional[dict]` return matches the `None`-on-failure convention already used by `discover_pod_ip`/`discover_pod_ips` and by `resource_usage_collector.py`'s `fetch_deployments_json`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-21-mesh-collector-per-tick-ip-refresh.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
