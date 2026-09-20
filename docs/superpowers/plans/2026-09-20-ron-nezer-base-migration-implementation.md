# Ron-Nezer Base Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry out the six real work items in [2026-09-20-ron-nezer-base-migration-design.md](../specs/2026-09-20-ron-nezer-base-migration-design.md) §10 (checklist items #1–#6) — port Ron Nezer's CPU/replica footprint into the **workshop tree** (`/home/idozacharia/TopFull` on `topfull-master`) as the new experiment base, fixed to fit `topfull-worker1`'s real capacity, while first closing a single-pod aggregation gap in our own collectors that HPA-driven multi-replica frontend would otherwise silently corrupt.

**Architecture:** This is not a self-contained application — it is a mix of (a) small, TDD-able Python changes to `experiments/topfull_cpu_quotas.py`, `experiments/envoy_retry_collector.py`, and `experiments/run_scenario.py` (all live in this git repo and are pushed to `topfull-master` at the start of every scenario run via `run_scenario.py`'s existing `deploy_repo_script()` mechanism — see `AGENTS.md` §6), and (b) a sequence of one-time, manual `ssh`/`kubectl` commands against the **live cluster and the live, uncommitted `/home/idozacharia/TopFull` tree on `topfull-master`**, which is not tracked in this git repo (only a clean KAIST upstream copy lives here, under the `TopFull/` submodule). Task 1 (collector fix) must land **before** Task 4 (the live CPU patch) and Task 5 (the frontend HPA), because HPA-driven multi-replica frontend is the first case that would expose the aggregation gap, and finding it might otherwise change how those later tasks need to be sequenced.

**Tech Stack:** Python 3 (`unittest`, no pytest dependency — see Global Constraints), PyYAML, `kubectl` / `ssh` / `scp` against a self-managed `kubeadm` Kubernetes cluster, Istio 1.17, Go (`go run`, no separate build step) for `proxy_online_boutique.go`.

## Global Constraints

- **SSH:** always use the OpenSSH host aliases `topfull-master`, `topfull-worker-1`, `topfull-load` — **never hardcode IPs** (`.cursor/rules/topfull-ssh.mdc`, always-applied). Connect as **`idozacharia`** (owns `/home/idozacharia/TopFull`, `/home/idozacharia/experiments`) — never as `idoza` (a different Linux account) for tooling paths. Use `-o BatchMode=yes -o ConnectTimeout=10 -o ControlMaster=no` for every non-interactive SSH call, matching `experiments/run_scenario.py`'s `ssh()` helper.
- **The Kubernetes node name is `topfull-worker1`** (no hyphen before the digit) — distinct from the SSH host alias `topfull-worker-1`. Confirmed live 2026-09-20: `kubectl describe node topfull-worker1` reports `Allocatable: cpu: 16`.
- **Container name is not always `server`.** Confirmed live 2026-09-20: `redis-cart`'s pod template container is named `redis`; every other of the 11 Boutique Deployments uses `server`. Any `kubectl patch`/`kubectl get -o jsonpath=...containers[0]...` against `redis-cart` that assumes `server` silently fails to match.
- **This is a design port, not a re-derivation.** Every CPU millicore value in this plan comes from spec §4d verbatim. Do **not** recompute the 77% trim or invent new numbers — if Ron replies with different real numbers (spec §9), only the tables in Task 2/Task 4 need updating, using the same method.
- **Test framework is stdlib `unittest`**, run directly with `python experiments/test_<module>.py` or `python -m unittest experiments.test_<module>` from the repo root — this repo has no `pytest` dependency declared anywhere (`experiments/README.md`, all 13 existing `experiments/test_*.py` files use `unittest.TestCase` + `if __name__ == "__main__": unittest.main()`). Do not introduce `pytest`.
- **No live-cluster access required to merge Tasks 1–3** (pure Python, mocked `ssh`/`kubectl`, matching existing test style in `experiments/test_run_scenario.py` / `experiments/test_envoy_retry_collector.py` / `experiments/test_topfull_cpu_quotas.py`). Tasks 4–7 require the VMs to be `RUNNING` and reachable — re-verify with `ssh topfull-master "kubectl get nodes"` before starting them (`AGENTS.md` §"Live infra caveat").
- **Out of scope (per design spec §8 — do not add tasks for these):** S1–S6 scenario-methodology rework, the S4A/productcatalog-HPA conflict, the loadgen layer (task weights/`GETPRODUCT`/split-cart `frontend.sh`), and any fresh campaign or frozen-capacity recalibration run. `campaign_48/`, `august_38/`, and `experiments/capacity/capacity_frozen.json` are historical after this migration and are not touched by this plan (spec decision 6).
- **Do not commit anything under `experiments/results/`, `experiments/capacity/`, or modify `TopFull/` (the git submodule)** — none of this plan's tasks touch those paths.

---

## Known finding that changes Task 2's scope (read before starting)

Design spec §10 item #1 describes `topfull_run_quotas.json` as "**currently S3/S4-conditional**" and frames the work as making the overlay call unconditional. **Live reading of `experiments/run_scenario.py` on 2026-09-20 shows this is already not true**: `run()` calls `write_run_quotas_json(cfg)` and `ensure_detector_quota_overlay(cfg)` unconditionally for every scenario (S1/S2/S5/S6 included), not only when `scale_constraints` is set — this was generalized during the 2026-09-09/2026-09-10 quota-sync work (`AGENTS.md` §4) and the spec's description is stale relative to the current code. **The actually-missing generalization is different and more consequential**: `topfull_cpu_quotas.py`'s `PAPER_CPU_LIMIT_MILLICORES` table (the "paper table" the sync mechanism reconciles *to* on every run, both at start and in the `finally` block) still holds the **old KAIST-paper-quota values**, not the new Ron-config-regime §4d values. If Task 4's live CPU patch is applied without first landing Task 2's table update, `run_scenario.py`'s own `reconcile_paper_cpu_limits()` will silently revert every Boutique Deployment's CPU limit back to the old paper-quota numbers the very next time any scenario is run — undoing Task 4. Task 2 must land before Task 4, and this dependency is the real form that "generalizing the quota-sync mechanism" (spec §10 #1+#2) takes in this codebase.

---

### Task 1: Fix single-pod IP assumption in the Envoy mesh collector

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (`discover_pod_ip` region, `ServiceScrapeResult`, `scrape_one_service`, `_apply_scrape_results`)
- Modify: `experiments/run_scenario.py:740-756` (`discover_service_pod_ips`)
- Test: `experiments/test_envoy_retry_collector.py`
- Test: `experiments/test_run_scenario.py:900-914` (`test_discover_service_pod_ips_uses_master_kubectl`)
- Test (audit-only, new regression tests, no implementation change): `experiments/test_topfull_throttle_collector.py`, `experiments/test_resource_usage_collector.py`

**Interfaces:**
- Consumes: nothing from later tasks.
- Produces: `envoy_retry_collector.parse_ip_list(raw: Optional[str]) -> List[str]`, `envoy_retry_collector.join_ip_list(ips: List[str]) -> str`, `envoy_retry_collector.discover_pod_ips(service: str, run_cmd=None, namespace="default") -> List[str]`, `envoy_retry_collector.sum_edge_maps(edge_maps: List[Dict[str, Dict[str, int]]]) -> Dict[str, Dict[str, int]]`, `envoy_retry_collector.sum_inbound_maps(inbound_maps: List[Dict[str, Any]]) -> Dict[str, Any]` — used internally by `scrape_one_service` (unchanged signature: `scrape_one_service(service: str, pod_ip: Optional[str], fetch_url: HttpFetcher) -> ServiceScrapeResult`). `run_scenario.discover_service_pod_ips(cfg, services) -> Dict[str, str]` keeps its existing signature and return type — the string value is now **comma-joined pod IPs** instead of a single IP, e.g. `{"frontend": "10.0.0.5,10.0.0.9"}`.

#### Background: why this design is a comma-joined string, not a new type

`envoy_retry_collector.py`'s `ip_cache: Dict[str, str]` (one IP string per service) is threaded through `poll_once`, `_apply_scrape_results`, `run_collector`, and 10+ existing tests in `test_envoy_retry_collector.py`. Changing the value type to `List[str]` would touch every one of those call sites and tests. Instead, this task keeps the field as a `str` but lets it hold **one or more comma-separated IPs** (`"10.0.0.1"` for today's 1-replica services, `"10.0.0.1,10.0.0.2"` once frontend has 2 replicas under its HPA). A single IP with no comma behaves identically to today — every existing test in `test_envoy_retry_collector.py` keeps passing unchanged, because `parse_ip_list("10.0.0.1") == ["10.0.0.1"]`.

- [ ] **Step 1: Audit `resource_usage_collector.py` and `topfull_throttle_collector.py` — confirm (or fix) their multi-pod aggregation, before touching the mesh collector**

Read `experiments/resource_usage_collector.py`'s `parse_stats_summary()` (loops over every pod in `summary.get("pods")`, maps pod name → service via `pod_name_to_service`, and **sums** `cpu_millicores`/`memory_working_set_bytes` across every pod matching that service — see `prev_cpu, prev_mem = totals.get(service, (0, 0)); totals[service] = (prev_cpu + cpu_sum, prev_mem + mem_sum)`). This is already multi-pod safe: it never assumes one pod per service.

Read `experiments/topfull_throttle_collector.py`'s `container_ids_from_pod_list()` (appends **every** matching container ID per service into a list, not just the first) and `aggregate_cpu()` (averages over however many values are in that list, filtering any `<= CPU_SKIP_BELOW`). This is already multi-pod safe too.

**Conclusion: only `envoy_retry_collector.py` has the single-pod bug** (`discover_pod_ip` takes `jsonpath={.items[0].status.podIP}` — hardcoded index `[0]`, and `poll_once`/`scrape_one_service` only ever fetch that one cached IP). Lock in the two already-safe collectors with regression tests so a future edit cannot reintroduce a single-pod assumption there without a test failing.

Add to `experiments/test_resource_usage_collector.py` (find the existing `class TestParseStatsSummary(unittest.TestCase):` block at line 100 and add this test inside it, using the same `summary` dict shape as its sibling tests in that class):

```python
    def test_sums_across_multiple_pods_of_the_same_service(self):
        # Regression guard for the 2026-09-20 Ron-Nezer migration: frontend
        # can have up to 4 replicas under its new HPA. This collector must
        # keep summing across every matching pod, not just the first.
        summary = {
            "pods": [
                {
                    "podRef": {"name": "frontend-abc123-11111", "namespace": "default"},
                    "containers": [
                        {"name": "server",
                         "cpu": {"usageNanoCores": 200_000_000},
                         "memory": {"workingSetBytes": 1000}},
                    ],
                },
                {
                    "podRef": {"name": "frontend-abc123-22222", "namespace": "default"},
                    "containers": [
                        {"name": "server",
                         "cpu": {"usageNanoCores": 300_000_000},
                         "memory": {"workingSetBytes": 1500}},
                    ],
                },
            ],
        }
        totals = ruc.parse_stats_summary(summary, ["frontend"])
        self.assertEqual(totals["frontend"], (500, 2500))
```

(`ruc` is this test module's existing import alias for `resource_usage_collector` — check the `import resource_usage_collector as ruc` line near the top of the file and reuse it; do not add a second import.)

Add to `experiments/test_topfull_throttle_collector.py` (find the existing pod-list test class containing `test_...frontend...front123...` around line 355-361 — the one asserting `ids["frontend"] == ["front123"]` — and add a sibling test in the same class):

```python
    def test_collects_multiple_container_ids_for_same_service(self):
        # Regression guard for the 2026-09-20 Ron-Nezer migration: frontend
        # can have up to 4 replicas under its new HPA. aggregate_cpu()
        # already averages a list — this locks in that the list itself can
        # have more than one entry for one service.
        pod_list = {
            "items": [
                {
                    "metadata": {"name": "frontend-abc123-11111"},
                    "status": {"containerStatuses": [
                        {"name": "server", "containerID": "docker://front111"},
                    ]},
                },
                {
                    "metadata": {"name": "frontend-abc123-22222"},
                    "status": {"containerStatuses": [
                        {"name": "server", "containerID": "docker://front222"},
                    ]},
                },
            ],
        }
        ids = ttc.container_ids_from_pod_list(pod_list, ["frontend"])
        self.assertEqual(ids["frontend"], ["front111", "front222"])
```

(`ttc` is this test module's existing import alias for `topfull_throttle_collector`.)

- [ ] **Step 2: Run the two new regression tests — confirm they pass against the existing, unmodified collectors**

```bash
python experiments/test_resource_usage_collector.py -k test_sums_across_multiple_pods_of_the_same_service
python experiments/test_topfull_throttle_collector.py -k test_collects_multiple_container_ids_for_same_service
```

If `-k` is not supported by your Python's `unittest` runner, use the fully-qualified path instead:

```bash
python -m unittest experiments.test_resource_usage_collector.TestParseStatsSummary.test_sums_across_multiple_pods_of_the_same_service -v
python -m unittest experiments.test_topfull_throttle_collector.TestContainerIdsFromPodList.test_collects_multiple_container_ids_for_same_service -v
```

Expected: both `PASS` — this proves both collectors are already multi-pod safe, with no implementation change. (Replace `TestContainerIdsFromPodList` with whatever the actual enclosing class name is once you've located the sibling test at line ~355.)

- [ ] **Step 3: Commit the audit regression tests**

```bash
git add experiments/test_resource_usage_collector.py experiments/test_topfull_throttle_collector.py
git commit -m "test: lock in multi-pod aggregation already correct in resource/throttle collectors"
```

- [ ] **Step 4: Write the failing tests for `parse_ip_list` / `join_ip_list`**

Add near the top of `experiments/test_envoy_retry_collector.py`, as a new test class (place it right after `class TestDiscoverPodIp(unittest.TestCase):`, i.e. after line 286):

```python
class TestParseIpList(unittest.TestCase):
    def test_single_ip_no_comma(self):
        self.assertEqual(erc.parse_ip_list("192.168.1.10"), ["192.168.1.10"])

    def test_multiple_comma_joined_ips(self):
        self.assertEqual(
            erc.parse_ip_list("192.168.1.10,192.168.1.11"),
            ["192.168.1.10", "192.168.1.11"],
        )

    def test_none_or_empty_returns_empty_list(self):
        self.assertEqual(erc.parse_ip_list(None), [])
        self.assertEqual(erc.parse_ip_list(""), [])

    def test_strips_whitespace_around_commas(self):
        self.assertEqual(
            erc.parse_ip_list("192.168.1.10, 192.168.1.11"),
            ["192.168.1.10", "192.168.1.11"],
        )


class TestJoinIpList(unittest.TestCase):
    def test_single_ip(self):
        self.assertEqual(erc.join_ip_list(["192.168.1.10"]), "192.168.1.10")

    def test_multiple_ips(self):
        self.assertEqual(
            erc.join_ip_list(["192.168.1.10", "192.168.1.11"]),
            "192.168.1.10,192.168.1.11",
        )

    def test_empty_list(self):
        self.assertEqual(erc.join_ip_list([]), "")
```

- [ ] **Step 5: Run the new tests to verify they fail (functions do not exist yet)**

```bash
python experiments/test_envoy_retry_collector.py
```

Expected: `AttributeError: module 'envoy_retry_collector' has no attribute 'parse_ip_list'` (and similarly for `join_ip_list`).

- [ ] **Step 6: Implement `parse_ip_list` / `join_ip_list`**

In `experiments/envoy_retry_collector.py`, add immediately above `def discover_pod_ip(` (currently at line 502):

```python
def parse_ip_list(raw: Optional[str]) -> List[str]:
    """
    Split a cached pod-IP field into individual IPs. A field with no
    comma is a single IP (the shape every service had before any
    service could have more than one replica) and returns a one-element
    list; a multi-replica service (e.g. frontend under its HPA, see the
    2026-09-20 Ron-Nezer migration) is comma-joined, e.g.
    "10.0.0.1,10.0.0.2".
    """
    if not raw:
        return []
    return [ip.strip() for ip in raw.split(",") if ip.strip()]


def join_ip_list(ips: List[str]) -> str:
    return ",".join(ips)
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
python experiments/test_envoy_retry_collector.py
```

Expected: all tests `PASS` (0 failures, 0 errors).

- [ ] **Step 8: Commit**

```bash
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "feat: add parse_ip_list/join_ip_list helpers to envoy_retry_collector"
```

- [ ] **Step 9: Write the failing tests for `discover_pod_ips` (plural)**

Add to `experiments/test_envoy_retry_collector.py`, right after the existing `class TestDiscoverPodIp(unittest.TestCase):` block (after line 286, before `class TestFetchStatsTextHttp`):

```python
class TestDiscoverPodIps(unittest.TestCase):
    def test_returns_every_pod_ip_not_just_first(self):
        def runner(cmd):
            return SimpleNamespace(
                returncode=0, stdout="192.168.1.10\n192.168.1.11\n", stderr=""
            )

        ips = erc.discover_pod_ips("frontend", run_cmd=runner)
        self.assertEqual(ips, ["192.168.1.10", "192.168.1.11"])

    def test_single_pod_service(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="192.168.1.10\n", stderr="")

        self.assertEqual(erc.discover_pod_ips("checkoutservice", run_cmd=runner), ["192.168.1.10"])

    def test_returns_empty_list_on_failure(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="error")

        self.assertEqual(erc.discover_pod_ips("frontend", run_cmd=runner), [])

    def test_returns_empty_list_on_empty_stdout(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="\n", stderr="")

        self.assertEqual(erc.discover_pod_ips("frontend", run_cmd=runner), [])

    def test_uses_range_jsonpath_over_all_items(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="192.168.1.10\n", stderr="")

        erc.discover_pod_ips("frontend", run_cmd=runner)
        self.assertIn("app=frontend", calls[0])
        self.assertIn("range .items[*]", calls[0][-1])
```

- [ ] **Step 10: Run to verify failure**

```bash
python experiments/test_envoy_retry_collector.py
```

Expected: `AttributeError: module 'envoy_retry_collector' has no attribute 'discover_pod_ips'`.

- [ ] **Step 11: Implement `discover_pod_ips`**

In `experiments/envoy_retry_collector.py`, add immediately after the existing `discover_pod_ip` function (after line 528, i.e. right before `@dataclass\nclass ServiceScrapeResult:`):

```python
def discover_pod_ips(
    service: str,
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> List[str]:
    """
    Return every Running pod IP for `service` — not just the first.
    Needed once a service (frontend, under its 2026-09-20 HPA) can have
    more than one replica; the older discover_pod_ip() (jsonpath
    `.items[0]`) would silently scrape only 1 of up to 4 frontend
    replicas. Returns [] on any kubectl failure or no pods yet.
    """
    runner = run_cmd or default_run_cmd
    cmd = [
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", f"app={service}",
        "-o", 'jsonpath={range .items[*]}{.status.podIP}{"\\n"}{end}',
    ]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  discover ips %s failed: %s", utc_now(), service, exc)
        return []
    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  discover ips %s exit=%s stderr=%s",
            utc_now(),
            service,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return []
    stdout = getattr(result, "stdout", "") or ""
    return [ip.strip() for ip in stdout.splitlines() if ip.strip()]
```

- [ ] **Step 12: Run to verify pass, then commit**

```bash
python experiments/test_envoy_retry_collector.py
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "feat: add discover_pod_ips to fetch every replica IP for a service"
```

- [ ] **Step 13: Write the failing tests for `sum_edge_maps` / `sum_inbound_maps`**

Add to `experiments/test_envoy_retry_collector.py`, right after `class TestParseInboundDoesNotMergeListeners(unittest.TestCase):` (after line 174, before `class TestWriteEdgesCsv`):

```python
class TestSumEdgeMaps(unittest.TestCase):
    def test_sums_matching_targets_across_pods(self):
        pod_a = {"cartservice": {"total": 10, "2xx": 9, "4xx": 1, "5xx": 0,
                                  "retry": 2, "rq_time_sum_ms": 100, "rq_time_count": 10}}
        pod_b = {"cartservice": {"total": 20, "2xx": 18, "4xx": 2, "5xx": 0,
                                  "retry": 3, "rq_time_sum_ms": 200, "rq_time_count": 20}}
        summed = erc.sum_edge_maps([pod_a, pod_b])
        self.assertEqual(summed["cartservice"], {
            "total": 30, "2xx": 27, "4xx": 3, "5xx": 0,
            "retry": 5, "rq_time_sum_ms": 300, "rq_time_count": 30,
        })

    def test_target_seen_by_only_one_pod_is_not_lost(self):
        pod_a = {"cartservice": {"total": 10, "2xx": 9, "4xx": 1, "5xx": 0,
                                  "retry": 2, "rq_time_sum_ms": 100, "rq_time_count": 10}}
        pod_b = {"paymentservice": {"total": 5, "2xx": 5, "4xx": 0, "5xx": 0,
                                     "retry": 0, "rq_time_sum_ms": 50, "rq_time_count": 5}}
        summed = erc.sum_edge_maps([pod_a, pod_b])
        self.assertEqual(set(summed.keys()), {"cartservice", "paymentservice"})
        self.assertEqual(summed["paymentservice"]["total"], 5)

    def test_empty_list_returns_empty_dict(self):
        self.assertEqual(erc.sum_edge_maps([]), {})


class TestSumInboundMaps(unittest.TestCase):
    def test_sums_scalar_metrics_across_pods(self):
        pod_a = {"total": 100, "2xx": 90, "4xx": 8, "5xx": 2, "resets": 0,
                  "rq_time_sum_ms": 500, "rq_time_count": 100, "rq_time_buckets": '{"10":50,"+Inf":100}'}
        pod_b = {"total": 50, "2xx": 45, "4xx": 4, "5xx": 1, "resets": 0,
                  "rq_time_sum_ms": 250, "rq_time_count": 50, "rq_time_buckets": '{"10":25,"+Inf":50}'}
        summed = erc.sum_inbound_maps([pod_a, pod_b])
        self.assertEqual(summed["total"], 150)
        self.assertEqual(summed["2xx"], 135)
        self.assertEqual(summed["4xx"], 12)
        self.assertEqual(summed["5xx"], 3)
        self.assertEqual(summed["rq_time_sum_ms"], 750)
        self.assertEqual(summed["rq_time_count"], 150)
        import json
        buckets = json.loads(summed["rq_time_buckets"])
        self.assertEqual(buckets["10"], 75)
        self.assertEqual(buckets["+Inf"], 150)

    def test_single_pod_passthrough(self):
        pod_a = {"total": 100, "2xx": 90, "4xx": 8, "5xx": 2, "resets": 0,
                  "rq_time_sum_ms": 500, "rq_time_count": 100, "rq_time_buckets": ""}
        self.assertEqual(erc.sum_inbound_maps([pod_a])["total"], 100)

    def test_empty_list_returns_zeros(self):
        summed = erc.sum_inbound_maps([])
        self.assertEqual(summed["total"], 0)
        self.assertEqual(summed["rq_time_buckets"], "")

    def test_no_buckets_present_leaves_empty_string(self):
        pod_a = {"total": 10, "2xx": 10, "4xx": 0, "5xx": 0, "resets": 0,
                  "rq_time_sum_ms": 0, "rq_time_count": 0, "rq_time_buckets": ""}
        pod_b = {"total": 20, "2xx": 20, "4xx": 0, "5xx": 0, "resets": 0,
                  "rq_time_sum_ms": 0, "rq_time_count": 0, "rq_time_buckets": ""}
        summed = erc.sum_inbound_maps([pod_a, pod_b])
        self.assertEqual(summed["rq_time_buckets"], "")
```

- [ ] **Step 14: Run to verify failure**

```bash
python experiments/test_envoy_retry_collector.py
```

Expected: `AttributeError: module 'envoy_retry_collector' has no attribute 'sum_edge_maps'`.

- [ ] **Step 15: Implement `sum_edge_maps` / `sum_inbound_maps`**

In `experiments/envoy_retry_collector.py`, add immediately after `def parse_inbound(...)` (after line 403, before `def write_edges_csv(`):

```python
def sum_edge_maps(
    edge_maps: List[Dict[str, Dict[str, int]]],
) -> Dict[str, Dict[str, int]]:
    """
    Sum per-target outbound metrics across multiple pods of the same
    calling service (e.g. frontend at replicas=1..4 under its HPA, see
    the 2026-09-20 Ron-Nezer migration). Each element of `edge_maps` is
    one pod's parse_edges() output. A target missing from one pod's map
    contributes 0 for that pod, not a dropped row.
    """
    summed: Dict[str, Dict[str, int]] = {}
    for edges in edge_maps:
        for target, metrics in edges.items():
            bucket = summed.setdefault(target, {k: 0 for k in OUTBOUND_METRICS})
            for key in OUTBOUND_METRICS:
                bucket[key] += metrics.get(key, 0)
    return summed


def sum_inbound_maps(inbound_maps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sum inbound listener metrics across multiple pods of the same callee
    service. Scalar counters (total/2xx/4xx/5xx/resets/rq_time_sum_ms/
    rq_time_count) sum linearly across independent pods. rq_time_buckets
    (cumulative histogram counts keyed by `le`, JSON-encoded by
    parse_inbound()) also sum per-bucket across pods — each pod's
    buckets are independent cumulative counters over that pod's own
    requests, so bucket-for-bucket addition is the correct merge.
    """
    if not inbound_maps:
        empty: Dict[str, Any] = {k: 0 for k in INBOUND_METRICS}
        empty["rq_time_buckets"] = ""
        return empty

    totals: Dict[str, Any] = {k: 0 for k in INBOUND_METRICS}
    bucket_totals: Dict[str, int] = {}
    for inbound in inbound_maps:
        for key in INBOUND_METRICS:
            totals[key] += inbound.get(key, 0)
        buckets_raw = inbound.get("rq_time_buckets") or ""
        if buckets_raw:
            try:
                buckets = json.loads(buckets_raw) if isinstance(buckets_raw, str) else buckets_raw
            except (TypeError, ValueError, json.JSONDecodeError):
                buckets = {}
            for le, count in buckets.items():
                bucket_totals[le] = bucket_totals.get(le, 0) + int(count)

    out: Dict[str, Any] = dict(totals)
    out["rq_time_buckets"] = (
        json.dumps(bucket_totals, separators=(",", ":")) if bucket_totals else ""
    )
    return out
```

- [ ] **Step 16: Run to verify pass, then commit**

```bash
python experiments/test_envoy_retry_collector.py
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "feat: add sum_edge_maps/sum_inbound_maps for multi-pod aggregation"
```

- [ ] **Step 17: Write the failing test for multi-IP `scrape_one_service`**

Add to `experiments/test_envoy_retry_collector.py`, inside the existing `class TestScrapeOneServiceHttp(unittest.TestCase):` block (after the existing `test_fetch_failure_evicts_without_raising` method, before the blank line at line 397-399):

```python
    def test_scrapes_and_sums_multiple_comma_joined_ips(self):
        fetch_log = []

        def fetch(url):
            fetch_log.append(url)
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            # Second replica: half the traffic of the first, same shape.
            stats = SAMPLE_MESH_STATS.replace(
                'cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 100',
                'cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 40',
            )
            return SimpleNamespace(returncode=0, stdout=stats, stderr="")

        result = erc.scrape_one_service(
            "frontend", "192.168.1.10,192.168.1.11", fetch
        )
        self.assertEqual(len(fetch_log), 2)
        self.assertIsNone(result.warning)
        self.assertEqual(result.edges["cartservice"]["total"], 140)
        self.assertEqual(result.inbound["total"], 400)  # 200 + 200

    def test_partial_failure_sums_only_surviving_ips_and_warns(self):
        def fetch(url):
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        result = erc.scrape_one_service(
            "frontend", "192.168.1.10,192.168.1.11", fetch
        )
        self.assertIsNotNone(result.edges)
        self.assertEqual(result.edges["cartservice"]["total"], 100)
        self.assertTrue(result.had_partial_failure)
        self.assertIn("tier2", result.warning)
        self.assertIn("192.168.1.11", result.warning)

    def test_all_ips_fail_evicts_like_single_ip_failure(self):
        def fetch(url):
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        result = erc.scrape_one_service(
            "frontend", "192.168.1.10,192.168.1.11", fetch
        )
        self.assertTrue(result.evict_ip)
        self.assertIsNone(result.edges)
```

- [ ] **Step 18: Run to verify failure**

```bash
python experiments/test_envoy_retry_collector.py
```

Expected: `AttributeError: 'ServiceScrapeResult' object has no attribute 'had_partial_failure'` (or an assertion failure on totals, since `scrape_one_service` currently only reads the first IP).

- [ ] **Step 19: Rewrite `ServiceScrapeResult` and `scrape_one_service`**

In `experiments/envoy_retry_collector.py`, replace the existing `ServiceScrapeResult` dataclass (lines 532-538) and `scrape_one_service` function (lines 549-569):

```python
@dataclass
class ServiceScrapeResult:
    service: str
    edges: Optional[Dict[str, Dict[str, int]]] = None
    inbound: Optional[Dict[str, Any]] = None
    evict_ip: bool = False
    had_partial_failure: bool = False
    warning: Optional[str] = None


def should_log_tier2(service: str, poll_index: int, state: Dict[str, int]) -> bool:
    last = state.get(service)
    if last is None or poll_index - last >= TIER2_WARN_EVERY_POLLS:
        state[service] = poll_index
        return True
    return False


def scrape_one_service(
    service: str,
    pod_ip: Optional[str],
    fetch_url: HttpFetcher,
) -> ServiceScrapeResult:
    ips = parse_ip_list(pod_ip)
    if not ips:
        return ServiceScrapeResult(
            service=service, warning=f"no seeded ip for service={service}"
        )

    edge_maps: List[Dict[str, Dict[str, int]]] = []
    inbound_maps: List[Dict[str, Any]] = []
    failed_ips: List[str] = []
    for ip in ips:
        stats_text = fetch_stats_text(ip, fetch_url=fetch_url)
        if stats_text is None:
            failed_ips.append(ip)
            continue
        edge_maps.append(parse_edges(stats_text))
        inbound_maps.append(parse_inbound(stats_text))

    if not edge_maps:
        return ServiceScrapeResult(
            service=service,
            evict_ip=True,
            warning=f"tier2 fetch failed service={service} ip={pod_ip}",
        )

    warning = None
    if failed_ips:
        warning = (
            f"tier2 partial fetch failure service={service} "
            f"failed_ips={','.join(failed_ips)} of {len(ips)} total"
        )
    return ServiceScrapeResult(
        service=service,
        edges=sum_edge_maps(edge_maps),
        inbound=sum_inbound_maps(inbound_maps),
        had_partial_failure=bool(failed_ips),
        warning=warning,
    )
```

(Note: `should_log_tier2` is unchanged — it already existed just above `scrape_one_service`; it is included here only to show its position relative to the rewritten block, do not duplicate it if it already sits between these two in the file.)

- [ ] **Step 20: Run to verify pass**

```bash
python experiments/test_envoy_retry_collector.py
```

Expected: all tests in `TestScrapeOneServiceHttp` `PASS`, including the 3 new ones. The pre-existing `test_parses_when_ip_present` and `test_missing_ip_is_warning` and `test_fetch_failure_evicts_without_raising` must **still pass unchanged** — this is the check that the comma-string design didn't break single-IP behavior.

- [ ] **Step 21: Commit**

```bash
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "feat: scrape and sum every comma-joined replica IP in scrape_one_service"
```

- [ ] **Step 22: Write the failing test for multi-IP reseed in `_apply_scrape_results`**

Add to `experiments/test_envoy_retry_collector.py`, inside `class TestTier2Reseed(unittest.TestCase):` (after the existing `test_reseed_is_rate_limited` method, before `class TestRunCollectorNetwork`):

```python
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

- [ ] **Step 23: Run to verify failure**

```bash
python experiments/test_envoy_retry_collector.py
```

Expected: `AssertionError` — `cache.get("frontend")` is still `"10.0.0.1,10.0.0.2"` because `_apply_scrape_results` still calls the singular `discover_pod_ip`.

- [ ] **Step 24: Update `_apply_scrape_results` to reseed with the plural discovery + comma-join**

In `experiments/envoy_retry_collector.py`, find the existing `_apply_scrape_results` function (lines 627-651) and replace the body of its `if result.warning:` branch:

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

(This is the same function shape as before — only the reseed line changed from `discover_pod_ip(...)` / `ip_cache[result.service] = new_ip` to `discover_pod_ips(...)` / `ip_cache[result.service] = join_ip_list(new_ips)`. The single-IP `TestTier2Reseed.test_fetch_failure_reseeds_new_ip_next_poll` test must still pass: `discover_pod_ips` returning `["10.0.0.2"]` joins to `"10.0.0.2"`, identical to the old single-IP behavior.)

- [ ] **Step 25: Run the full test file to verify everything passes**

```bash
python experiments/test_envoy_retry_collector.py -v
```

Expected: every test in the file passes, including all pre-existing `TestTier2Reseed`, `TestPollOnceNetwork`, `TestPollOnceThreadPoolSerialWrites`, and `TestRunCollectorNetwork` tests (none of their fixtures use multi-IP strings, so they exercise the single-IP passthrough path).

- [ ] **Step 26: Commit**

```bash
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "feat: reseed full replica IP list on tier2 fetch failure"
```

- [ ] **Step 27: Write the failing test for `run_scenario.discover_service_pod_ips` seeding every replica**

In `experiments/test_run_scenario.py`, replace the existing `test_discover_service_pod_ips_uses_master_kubectl` test (lines 901-914):

```python
    @mock.patch("run_scenario.ssh")
    def test_discover_service_pod_ips_uses_master_kubectl(self, mock_ssh):
        mock_ssh.side_effect = [
            SimpleNamespace(returncode=0, stdout="192.168.1.10\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="192.168.1.11\n", stderr=""),
        ]
        got = run_scenario.discover_service_pod_ips(
            self._cfg(), ["frontend", "checkoutservice"]
        )
        self.assertEqual(
            got, {"frontend": "192.168.1.10", "checkoutservice": "192.168.1.11"}
        )
        self.assertEqual(mock_ssh.call_args_list[0].args[0], "topfull-master")
        self.assertIn("app=frontend", mock_ssh.call_args_list[0].args[1])
        self.assertIn("range .items[*]", mock_ssh.call_args_list[0].args[1])

    @mock.patch("run_scenario.ssh")
    def test_discover_service_pod_ips_joins_multiple_replicas_with_comma(self, mock_ssh):
        mock_ssh.side_effect = [
            SimpleNamespace(returncode=0, stdout="192.168.1.10\n192.168.1.20\n", stderr=""),
        ]
        got = run_scenario.discover_service_pod_ips(self._cfg(), ["frontend"])
        self.assertEqual(got, {"frontend": "192.168.1.10,192.168.1.20"})
```

- [ ] **Step 28: Run to verify failure**

```bash
python experiments/test_run_scenario.py
```

Expected: `test_discover_service_pod_ips_uses_master_kubectl` fails on `self.assertIn("range .items[*]", ...)` (current code still uses `jsonpath={.items[0].status.podIP}`), and `test_discover_service_pod_ips_joins_multiple_replicas_with_comma` fails because `got == {"frontend": "192.168.1.10"}` (only the first line of stdout is read via `r.stdout.strip()` today).

- [ ] **Step 29: Rewrite `discover_service_pod_ips` in `run_scenario.py`**

In `experiments/run_scenario.py`, replace the existing function (lines 740-756):

```python
def discover_service_pod_ips(cfg: dict, services: list) -> dict:
    """
    Seed the mesh collector's per-service pod-IP cache with EVERY
    Running pod IP for that service, comma-joined
    (envoy_retry_collector.parse_ip_list splits on comma) — not just the
    first pod. Needed once a service (frontend, under its 2026-09-20
    HPA) can have more than one replica; seeding only the first pod's IP
    would silently scrape 1 of up to 4 frontend replicas forever.
    """
    master = cfg["infra"]["master_ssh_host"]
    out = {}
    for svc in services:
        r = ssh(
            master,
            f"kubectl get pods -n default -l app={svc} "
            "-o jsonpath='{range .items[*]}{.status.podIP}{\"\\n\"}{end}'",
            check=False,
        )
        ips = [ip.strip() for ip in (r.stdout or "").splitlines() if ip.strip()]
        if ips:
            out[svc] = ",".join(ips)
        else:
            print(f"[WARN] No pod IP for app={svc} during mesh seed "
                  f"(stderr={(r.stderr or '').strip()})")
    return out
```

- [ ] **Step 30: Run to verify pass**

```bash
python experiments/test_run_scenario.py
```

Expected: all tests pass, including `test_start_uploads_pod_ips_on_master` (line 924) which mocks `discover_service_pod_ips` directly and is unaffected by the internal jsonpath change.

- [ ] **Step 31: Commit**

```bash
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat: seed every replica pod IP (not just the first) for the mesh collector"
```

---

### Task 2: Rebase `topfull_cpu_quotas.py`'s CPU table to the Ron-config-regime values

**Files:**
- Modify: `experiments/topfull_cpu_quotas.py`
- Modify: `experiments/run_scenario.py:450-472` (`reconcile_paper_cpu_limits`)
- Test: `experiments/test_topfull_cpu_quotas.py`
- Test: `experiments/test_run_scenario.py` (any test asserting old paper-quota millicore values against `reconcile_paper_cpu_limits`)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `topfull_cpu_quotas.container_name_for(service: str) -> str` (new), and the existing `paper_limit_for`, `paper_request_for`, `RECONCILE_SERVICES`, `PAPER_CPU_LIMIT_MILLICORES` now return/hold the §4d Ron-config-regime values for all 11 Boutique services instead of the old KAIST-paper-quota values for 7-8 of them. Task 4 (the live `kubectl patch`) and Task 3 (the frontend-replica guard) both read `PAPER_CPU_LIMIT_MILLICORES` / `RECONCILE_SERVICES` / `container_name_for` from this module.

- [ ] **Step 1: Write the failing tests for the new CPU table**

In `experiments/test_topfull_cpu_quotas.py`, replace the existing `class TestPaperTable(unittest.TestCase):` block (lines 34-40):

```python
class TestPaperTable(unittest.TestCase):
    # Ron-Nezer base migration (2026-09-20 design spec §4d): all 11
    # Boutique services, request == limit for every one (Ron's own
    # January YAML has request == limit; the workshop trims his numbers
    # by ~77% to fit topfull-worker1's 16 vCPU — see spec §4).
    def test_all_eleven_services_have_explicit_trimmed_values(self):
        self.assertEqual(q.paper_limit_for("frontend"), 1150)
        self.assertEqual(q.paper_limit_for("checkoutservice"), 615)
        self.assertEqual(q.paper_limit_for("recommendationservice"), 1150)
        self.assertEqual(q.paper_limit_for("productcatalogservice"), 1535)
        self.assertEqual(q.paper_limit_for("cartservice"), 1920)
        self.assertEqual(q.paper_limit_for("currencyservice"), 770)
        self.assertEqual(q.paper_limit_for("shippingservice"), 770)
        self.assertEqual(q.paper_limit_for("redis-cart"), 540)
        self.assertEqual(q.paper_limit_for("emailservice"), 155)
        self.assertEqual(q.paper_limit_for("paymentservice"), 155)
        self.assertEqual(q.paper_limit_for("adservice"), 1150)

    def test_request_equals_limit_for_every_service(self):
        for svc in q.PAPER_CPU_LIMIT_MILLICORES:
            self.assertEqual(
                q.paper_request_for(svc), q.paper_limit_for(svc),
                msg=f"{svc}: request must equal limit in the Ron-config regime",
            )

    def test_reconcile_services_covers_all_eleven(self):
        self.assertEqual(
            set(q.RECONCILE_SERVICES),
            {
                "frontend", "checkoutservice", "recommendationservice",
                "productcatalogservice", "cartservice", "currencyservice",
                "shippingservice", "redis-cart", "emailservice",
                "paymentservice", "adservice",
            },
        )


class TestContainerNameFor(unittest.TestCase):
    def test_redis_cart_container_is_named_redis(self):
        self.assertEqual(q.container_name_for("redis-cart"), "redis")

    def test_default_container_name_is_server(self):
        self.assertEqual(q.container_name_for("frontend"), "server")
        self.assertEqual(q.container_name_for("checkoutservice"), "server")
```

Also update `TestEffectiveCpuQuotas.test_paper_plus_overwrite` (lines 92-105), whose expected `checkoutservice` fraction result is derived from the old 1000m paper limit:

```python
class TestEffectiveCpuQuotas(unittest.TestCase):
    def test_paper_plus_overwrite(self):
        got = q.effective_cpu_quotas(
            [
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit_fraction": 0.1,
                }
            ]
        )
        self.assertEqual(got["checkoutservice"], 61)  # int(615 * 0.1)
        self.assertEqual(got["productcatalogservice"], 1535)
        self.assertEqual(got["paymentservice"], 155)
```

And update `TestPaperTable`'s old assertions inline in `TestValidateScaleConstraints` if any hardcode `1000`/`500` (check `test_fraction_ok` and `test_unknown_service_fraction_is_error` at lines 66-89 — these do not assert specific millicore values, only that validation succeeds/fails, so they need **no** change).

- [ ] **Step 2: Run to verify failure**

```bash
python experiments/test_topfull_cpu_quotas.py
```

Expected: multiple `AssertionError`s (`paper_limit_for("frontend")` currently returns `1000`, not `1150`; `container_name_for` doesn't exist yet; `RECONCILE_SERVICES` currently has only 8 entries).

- [ ] **Step 3: Rewrite the CPU tables in `experiments/topfull_cpu_quotas.py`**

Replace lines 12-44 (from `DEFAULT_PAPER_LIMIT_MILLICORES = 1000` through the closing `)` of `RECONCILE_SERVICES`):

```python
DEFAULT_PAPER_LIMIT_MILLICORES = 1000

# Ron-Nezer base migration (2026-09-20 design spec §4d). All 11 Boutique
# services, request == limit (Ron's own January YAML has request ==
# limit for every service; these are his per-replica values trimmed by
# ~77% — spec §4b/§4c/§4d — to fit topfull-worker1's 16 vCPU allocatable
# after cAdvisor/istiod/calico-node/metrics-server + istio-proxy sidecar
# overhead). These are PROVISIONAL pending Ron's reply (spec §3/§9) — if
# he confirms different real numbers, redo this table with the same
# budget-then-trim method, nothing else in this module changes.
PAPER_CPU_LIMIT_MILLICORES: Dict[str, int] = {
    "frontend": 1150,               # x1-4 replicas under its HPA (Task 5)
    "checkoutservice": 615,
    "recommendationservice": 1150,
    "productcatalogservice": 1535,
    "cartservice": 1920,
    "currencyservice": 770,
    "shippingservice": 770,
    "redis-cart": 540,
    "emailservice": 155,
    "paymentservice": 155,
    "adservice": 1150,
}

# Ron-config regime: request == limit for every service (unlike the old
# KAIST-paper-quota table, which halved request relative to limit for
# some services). paper_request_for() falls back to paper_limit_for()
# below when a service has no explicit override here — leave this dict
# empty rather than duplicating PAPER_CPU_LIMIT_MILLICORES.
PAPER_CPU_REQUEST_MILLICORES: Dict[str, int] = {}

RECONCILE_SERVICES = (
    "frontend",
    "checkoutservice",
    "recommendationservice",
    "productcatalogservice",
    "cartservice",
    "currencyservice",
    "shippingservice",
    "redis-cart",
    "emailservice",
    "paymentservice",
    "adservice",
)

# redis-cart's pod template container is named "redis", not "server"
# (confirmed live 2026-09-20: `kubectl get deploy redis-cart -o
# jsonpath={.spec.template.spec.containers[0].name}` -> "redis"). Every
# other of the 11 Boutique Deployments uses "server".
CONTAINER_NAME_OVERRIDES: Dict[str, str] = {
    "redis-cart": "redis",
}


def container_name_for(service: str) -> str:
    return CONTAINER_NAME_OVERRIDES.get(service, "server")
```

- [ ] **Step 4: Run to verify pass**

```bash
python experiments/test_topfull_cpu_quotas.py
```

Expected: all tests pass.

- [ ] **Step 5: Fix `reconcile_paper_cpu_limits` in `run_scenario.py` to use the real container name**

In `experiments/run_scenario.py`, find `reconcile_paper_cpu_limits` (lines 450-472) and change the hardcoded `"name": "server"` to use the new lookup:

```python
def reconcile_paper_cpu_limits(cfg: dict, wait: bool = True) -> None:
    """Patch Boutique Deployments to the paper CPU limit/request table."""
    banner("Reconciling CPU limits to paper quotas")
    master = cfg["infra"]["master_ssh_host"]
    for dep in topfull_cpu_quotas.RECONCILE_SERVICES:
        lim = topfull_cpu_quotas.kubectl_cpu_quantity(
            topfull_cpu_quotas.paper_limit_for(dep)
        )
        req = topfull_cpu_quotas.kubectl_cpu_quantity(
            topfull_cpu_quotas.paper_request_for(dep)
        )
        container = topfull_cpu_quotas.container_name_for(dep)
        step(f"{dep}: limits.cpu={lim} requests.cpu={req} (container={container})")
        patch = json.dumps({
            "spec": {"template": {"spec": {"containers": [
                {"name": container, "resources": {
                    "limits": {"cpu": lim},
                    "requests": {"cpu": req},
                }}
            ]}}}
        })
        ssh(master, f"kubectl patch deployment {dep} -n default -p '{patch}'",
            check=False)
    if wait:
        wait_with_progress(20, "pods stabilising after paper CPU reconcile")
```

- [ ] **Step 6: Search for and update any test that hardcodes the old container name or old millicore values against `reconcile_paper_cpu_limits`**

```bash
grep -n "reconcile_paper_cpu_limits\|\"name\": \"server\"" experiments/test_run_scenario.py
```

If this returns any test asserting the patch JSON contains `"name": "server"` for **`redis-cart`** specifically, update that one assertion to expect `"name": "redis"` (leave assertions for any other service as `"server"` — they are still correct). If the grep returns no `redis-cart`-specific assertion (i.e. existing tests only ever patched services still named `"server"`), no test change is needed here — note that in the task's commit message.

- [ ] **Step 7: Run the full `run_scenario.py` and `topfull_cpu_quotas.py` test suites**

```bash
python experiments/test_run_scenario.py -v
python experiments/test_topfull_cpu_quotas.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add experiments/topfull_cpu_quotas.py experiments/run_scenario.py experiments/test_topfull_cpu_quotas.py experiments/test_run_scenario.py
git commit -m "feat: rebase CPU quota table to Ron-config-regime values (spec §4d)"
```

---

### Task 3: Guard against `scale_constraints` re-pinning frontend's replica count

**Files:**
- Modify: `experiments/topfull_cpu_quotas.py` (`validate_scale_constraints`)
- Test: `experiments/test_topfull_cpu_quotas.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `validate_scale_constraints` (existing signature, `List[dict] -> None`, raises `ValueError`) now also rejects a `method: replicas` constraint targeting `deployment: frontend`.

**Context:** Frontend's replica count becomes HPA-managed once Task 5 lands (`minReplicas: 1, maxReplicas: 4`). Any scenario YAML that still tried to `kubectl scale deployment frontend --replicas=N` via `scale_constraints` would fight the autoscaler (the HPA would immediately try to scale it back based on CPU). Live audit on 2026-09-20 found **no current scenario YAML does this today** (only `scenario_3_baseline.yaml` references `instance_scaling` in a comment, and that script is not invoked by `run_scenario.py` at all — grep confirms zero references to `instance_scaling` in `run_scenario.py`). This task is a forward-looking guard, not a fix for an existing bug.

- [ ] **Step 1: Write the failing test**

Add to `experiments/test_topfull_cpu_quotas.py`, inside `class TestValidateScaleConstraints(unittest.TestCase):` (after the existing `test_unknown_service_fraction_is_error` method, before `class TestEffectiveCpuQuotas`):

```python
    def test_frontend_replicas_constraint_is_rejected(self):
        # Ron-Nezer migration (2026-09-20): frontend's replica count is
        # HPA-managed (spec §4c/§10 #5) — a scenario YAML that still
        # tries to pin it would fight the autoscaler.
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {"deployment": "frontend", "method": "replicas", "replicas": 1}
            ])

    def test_other_services_replicas_constraint_is_still_allowed(self):
        q.validate_scale_constraints([
            {"deployment": "checkoutservice", "method": "replicas", "replicas": 2}
        ])
```

- [ ] **Step 2: Run to verify failure**

```bash
python experiments/test_topfull_cpu_quotas.py
```

Expected: `test_frontend_replicas_constraint_is_rejected` fails (no `ValueError` is raised today — `validate_scale_constraints` only inspects `method == "cpu_limit"` constraints, ignoring `"replicas"` entirely).

- [ ] **Step 3: Extend `validate_scale_constraints`**

In `experiments/topfull_cpu_quotas.py`, replace the function (lines 83-96):

```python
def validate_scale_constraints(constraints: List[dict]) -> None:
    known = set(PAPER_CPU_LIMIT_MILLICORES) | set(RECONCILE_SERVICES)
    for c in constraints or []:
        method = c.get("method")
        if method == "replicas" and c.get("deployment") == "frontend":
            raise ValueError(
                "scale_constraints cannot set replicas on frontend - its "
                "replica count is HPA-managed (minReplicas=1, maxReplicas=4, "
                "Ron-Nezer base migration); a fixed replicas constraint would "
                "fight the autoscaler"
            )
        if method != "cpu_limit":
            continue
        if "cpu_limit" in c:
            raise ValueError(
                "scale_constraints cpu_limit is removed; use cpu_limit_fraction"
            )
        if "cpu_limit_fraction" not in c:
            raise ValueError("cpu_limit constraint requires cpu_limit_fraction")
        dep = c.get("deployment")
        if dep not in known:
            raise ValueError(f"no paper quota for deployment {dep}")
        millicores_from_fraction(paper_limit_for(dep), float(c["cpu_limit_fraction"]))
```

- [ ] **Step 4: Run to verify pass**

```bash
python experiments/test_topfull_cpu_quotas.py -v
```

Expected: all tests pass, including the two new ones.

- [ ] **Step 5: Commit**

```bash
git add experiments/topfull_cpu_quotas.py experiments/test_topfull_cpu_quotas.py
git commit -m "feat: reject scale_constraints that would pin frontend's HPA-managed replicas"
```

---

### Task 4: Patch the live Boutique Deployments' CPU on `topfull-master` to the §4d table

> **This task edits the live cluster, not this git repo.** It must run **after** Task 2 has landed (so the very next `run_scenario.py` run's `reconcile_paper_cpu_limits()` reconciles to the *new* table instead of reverting this patch — see "Known finding" above). It has no automated test; verification is a `kubectl get` read-back.

**Pre-check — confirm the VMs are up and reachable:**

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default"
```

Expected: `topfull-master` and `topfull-worker1` both `Ready`; all 11 Boutique pods `Running`. If not, follow `AGENTS.md`'s "Live infra caveat" / `SETUP-GUIDE.md` before continuing.

- [ ] **Step 1: Snapshot the current live CPU table (for the rollback record)**

```bash
ssh topfull-master "kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,REPL:.spec.replicas,CPU_LIM:.spec.template.spec.containers[0].resources.limits.cpu,CPU_REQ:.spec.template.spec.containers[0].resources.requests.cpu"
```

Expected output before this task (confirmed live 2026-09-20 — this is the old KAIST-paper-quota table this task replaces):

```
NAME                    REPL   CPU_LIM   CPU_REQ
adservice               1      1         500m
cartservice             1      1         500m
checkoutservice         1      1         500m
currencyservice         1      1         500m
emailservice            1      1         200m
frontend                1      1         500m
paymentservice          1      1         200m
productcatalogservice   1      500m      250m
recommendationservice   1      2         1
redis-cart              1      125m      70m
shippingservice         1      1         500m
```

- [ ] **Step 2: Patch each of the 11 Deployments to the §4d trimmed values (request == limit)**

Run these one at a time (or paste as a block — each is independent). Every value matches `PAPER_CPU_LIMIT_MILLICORES` in Task 2's `topfull_cpu_quotas.py` exactly:

```bash
ssh topfull-master "kubectl patch deployment frontend -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"1150m\"},\"requests\":{\"cpu\":\"1150m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment checkoutservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"615m\"},\"requests\":{\"cpu\":\"615m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment recommendationservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"1150m\"},\"requests\":{\"cpu\":\"1150m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment productcatalogservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"1535m\"},\"requests\":{\"cpu\":\"1535m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment cartservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"1920m\"},\"requests\":{\"cpu\":\"1920m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment currencyservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"770m\"},\"requests\":{\"cpu\":\"770m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment shippingservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"770m\"},\"requests\":{\"cpu\":\"770m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment redis-cart -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"redis\",\"resources\":{\"limits\":{\"cpu\":\"540m\"},\"requests\":{\"cpu\":\"540m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment emailservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"155m\"},\"requests\":{\"cpu\":\"155m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment paymentservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"155m\"},\"requests\":{\"cpu\":\"155m\"}}}]}}}}'"
ssh topfull-master "kubectl patch deployment adservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"1150m\"},\"requests\":{\"cpu\":\"1150m\"}}}]}}}}'"
```

Note the `redis-cart` line uses container name `"redis"`, not `"server"` — matching `container_name_for("redis-cart")` from Task 2.

- [ ] **Step 3: Wait for pods to roll, then verify**

```bash
ssh topfull-master "kubectl rollout status deployment/frontend -n default --timeout=60s; kubectl rollout status deployment/checkoutservice -n default --timeout=60s; kubectl rollout status deployment/cartservice -n default --timeout=60s"
ssh topfull-master "kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,REPL:.spec.replicas,CPU_LIM:.spec.template.spec.containers[0].resources.limits.cpu,CPU_REQ:.spec.template.spec.containers[0].resources.requests.cpu"
```

Expected: every `CPU_LIM`/`CPU_REQ` pair matches the Step 2 values (`frontend 1150m/1150m`, `checkoutservice 615m/615m`, `recommendationservice 1150m/1150m`, `productcatalogservice 1535m/1535m`, `cartservice 1920m/1920m`, `currencyservice 770m/770m`, `shippingservice 770m/770m`, `redis-cart 540m/540m`, `emailservice 155m/155m`, `paymentservice 155m/155m`, `adservice 1150m/1150m`). All pods `Running` (no `Pending` from insufficient node CPU — total demand at 1 replica each is `1150+615+1150+1535+1920+770+770+540+155+155+1150 = 9910m`, well under the 16,000m allocatable).

- [ ] **Step 4: Check node-level headroom**

```bash
ssh topfull-master "kubectl describe node topfull-worker1 | grep -A 15 'Allocated resources'"
```

Expected: `cpu` requests total in the low-to-mid thousands of millicores, comfortably under 16,000m allocatable, leaving room for the frontend HPA to scale to 4 replicas (Task 5) without hitting `Pending` pods — matches spec §4b/§4d's ≈13,350m app-container budget at full scale-out.

_No code to commit for this task — it is a live-cluster state change only. Record completion by updating `AGENTS.md` §4 in a later, separate documentation pass (not part of this plan's scope)._

---

### Task 5: Create and apply the frontend HPA

**Pre-check:** confirm Task 4 has landed (frontend CPU limit is `1150m`, not the old `1000m`/`1` value) — the HPA's 85% CPU target is computed against whatever `resources.requests.cpu` currently is, so applying the HPA before Task 4 would target the wrong CPU baseline.

- [ ] **Step 1: Confirm no HPA exists yet**

```bash
ssh topfull-master "kubectl get hpa -n default"
```

Expected (confirmed live 2026-09-20, pre-migration): `No resources found in default namespace.`

- [ ] **Step 2: Write the HPA manifest locally, then copy it to master**

Create this file locally at `experiments/manifests/frontend-hpa.yaml` (new directory):

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 1
  maxReplicas: 4
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 85
```

This matches spec §4c/§10 #4: `minReplicas: 1, maxReplicas: 4`, 85% CPU target — same shape as Ron's `deployments/hpa.yaml` but with a ceiling of 4, not 20. `productcatalogservice` gets **no** HPA (deferred per spec decision 9) — do not create a second manifest for it.

```bash
scp -o BatchMode=yes -o ControlMaster=no experiments/manifests/frontend-hpa.yaml topfull-master:/tmp/frontend-hpa.yaml
```

- [ ] **Step 3: Apply it**

```bash
ssh topfull-master "kubectl apply -f /tmp/frontend-hpa.yaml"
```

Expected: `horizontalpodautoscaler.autoscaling/frontend-hpa created`.

- [ ] **Step 4: Verify**

```bash
ssh topfull-master "kubectl get hpa frontend-hpa -n default"
```

Expected: a row showing `TARGETS` near `<current>%/85%` (likely single-digit percent under no load), `MINPODS 1`, `MAXPODS 4`, `REPLICAS 1`. This requires `metrics-server` to be running and reporting pod CPU — confirmed live 2026-09-20 that `kubectl top node`/`kubectl top pod` already work on this cluster (Ron's HPA-dependent `hostNetwork: true` tweak was investigated and explicitly **not** adopted per spec §7 — the existing `metrics-server` setup already works without it).

- [ ] **Step 5: Commit the manifest to the repo**

```bash
git add experiments/manifests/frontend-hpa.yaml
git commit -m "feat: add frontend HPA manifest (minReplicas=1, maxReplicas=4, 85% CPU)"
```

_The `kubectl apply` itself (Step 3) is a live-cluster action, not something this commit replays — re-running `kubectl apply -f experiments/manifests/frontend-hpa.yaml` from a future session is how you'd recreate it if the object were ever deleted._

---

### Task 6: Port the proxy Host-match diff into the workshop's `proxy_online_boutique.go`

**Live diff already derived (2026-09-20)** by SSHing into `topfull-master` and running:

```bash
ssh topfull-master "diff -u /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go /home/user/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go"
```

The relevant hunk (the Host-match drop on `GET /cart` and `GET /product/*` — spec §7/§10 #6; the rest of the diff is Ron's unrelated path rewrite and whitespace, which must **not** be ported):

```diff
 var GetCartCondition goproxy.ReqConditionFunc = func (req *http.Request, ctx *goproxy.ProxyCtx) bool {
-	return req.URL.Host == global_config.FrontendUrl &&
-			req.Method == "GET"  &&
-			req.URL.Path == "/cart"
+    return req.Method == "GET" && req.URL.Path == "/cart"
 }
 var GetProductCondition goproxy.ReqConditionFunc = func (req *http.Request, ctx *goproxy.ProxyCtx) bool {
-	return req.URL.Host == global_config.FrontendUrl &&
-			req.Method == "GET"  &&
-			strings.Contains(req.URL.Path, "/product")
+    return req.Method == "GET" && strings.HasPrefix(req.URL.Path, "/product")
 }
```

This file lives only on `topfull-master` (`/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go`) — it is **not** in this git repo (only the clean KAIST upstream copy is, under the `TopFull/` submodule). `run_scenario.py`'s `start_master_stack()` runs it with `go run proxy_online_boutique.go` every scenario start — no separate build/compile step, so this patch takes effect on the next run after being applied.

- [ ] **Step 1: Back up the live file**

```bash
ssh topfull-master "cp /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go.bak.ron-migration-2026-09-20"
```

- [ ] **Step 2: Confirm the exact current text of both functions before patching (idempotency check)**

```bash
ssh topfull-master "grep -n 'GetCartCondition\|GetProductCondition' -A4 /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go"
```

Expected: the two function bodies match the `-` (removed) side of the diff hunk above exactly. If they don't (e.g. someone already hand-patched this), **stop and diff manually** rather than applying Step 3 blindly.

- [ ] **Step 3: Apply the patch with `sed` (two targeted in-place replacements)**

```bash
ssh topfull-master "python3 - <<'PYEOF'
from pathlib import Path
path = Path('/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go')
text = path.read_text(encoding='utf-8')

old_cart = '''var GetCartCondition goproxy.ReqConditionFunc = func (req *http.Request, ctx *goproxy.ProxyCtx) bool {
\treturn req.URL.Host == global_config.FrontendUrl &&
\t\t\treq.Method == \"GET\"  &&
\t\t\treq.URL.Path == \"/cart\"
}'''
new_cart = '''var GetCartCondition goproxy.ReqConditionFunc = func (req *http.Request, ctx *goproxy.ProxyCtx) bool {
    return req.Method == \"GET\" && req.URL.Path == \"/cart\"
}'''
if old_cart not in text:
    raise SystemExit(\"GetCartCondition body not found verbatim - abort, diff manually\")
text = text.replace(old_cart, new_cart)

old_product = '''var GetProductCondition goproxy.ReqConditionFunc = func (req *http.Request, ctx *goproxy.ProxyCtx) bool {
\treturn req.URL.Host == global_config.FrontendUrl &&
\t\t\treq.Method == \"GET\"  &&
\t\t\tstrings.Contains(req.URL.Path, \"/product\")
}'''
new_product = '''var GetProductCondition goproxy.ReqConditionFunc = func (req *http.Request, ctx *goproxy.ProxyCtx) bool {
    return req.Method == \"GET\" && strings.HasPrefix(req.URL.Path, \"/product\")
}'''
if old_product not in text:
    raise SystemExit(\"GetProductCondition body not found verbatim - abort, diff manually\")
text = text.replace(old_product, new_product)

path.write_text(text, encoding='utf-8')
print('patched')
PYEOF"
```

Expected output: `patched`. If either `SystemExit` fires instead, the live file's whitespace/tabs differ from what Step 2 showed — re-derive the exact `old_cart`/`old_product` strings from the live `grep -n ... -A4` output before retrying (do not force the patch).

- [ ] **Step 4: Verify the patch landed and the Go file still parses**

```bash
ssh topfull-master "grep -n 'GetCartCondition\|GetProductCondition' -A2 /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go"
ssh topfull-master "cd /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy && go vet ./... 2>&1 | head -30"
```

Expected: the two conditions now read `return req.Method == "GET" && req.URL.Path == "/cart"` and `return req.Method == "GET" && strings.HasPrefix(req.URL.Path, "/product")`; `go vet` reports no new errors (it may print pre-existing unrelated warnings from upstream code — compare against a `go vet` run on the `.bak.ron-migration-2026-09-20` backup file if unsure whether a warning is new).

- [ ] **Step 5: Smoke-test the proxy alone (no full scenario run yet)**

```bash
ssh topfull-master "cd /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy && timeout 15 go run proxy_online_boutique.go; echo exit_code=\$?"
```

Expected: the proxy starts and prints its normal startup log (matches what `run_scenario.py`'s `start_master_stack()` already tmux-launches every run) with no Go compile error, then is killed by `timeout` after 15s with a non-zero exit from the `timeout` wrapper itself (this is expected — it proves the file compiles and starts, not that it survived a real run).

_No code to commit for this task — the patched file lives only on `topfull-master`, not in this git repo. The diff and patch script above are the durable record; consider pasting Step 3's script into `Guides and Info/RON-NEZER-SETUP-VS-WORKSHOP.md`'s history in a later documentation pass (out of scope here)._

---

### Task 7: Final validation — node capacity + short live smoke run

- [ ] **Step 1: Re-check node capacity after Tasks 4-6**

```bash
ssh topfull-master "kubectl describe node topfull-worker1 | grep -A 15 'Allocated resources'"
ssh topfull-master "kubectl get pods -n default -o wide"
```

Expected: all 11 Boutique pods `Running` on `topfull-worker1` (not `Pending`), CPU requests total ≈9,910m at 1 frontend replica (Task 4's per-replica sum), well under 16,000m allocatable.

- [ ] **Step 2: Confirm the quota-sync overlay picks up the new table**

Run any short baseline scenario (S1 is the shortest at 5 minutes) and inspect the manifest it writes:

```bash
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
```

While it's running or after it finishes, check the pulled `run_manifest.json` / `service_capacity.json` for the run (per the runner's own printed `scp` command) — `effective_cpu_quotas.frontend` must read `1150`, not `1000` or `500`, confirming Task 2's table (not the stale KAIST-paper one) is what got written to `topfull_run_quotas.json` and loaded by the Detector.

- [ ] **Step 3: Confirm the mesh collector captured more than one frontend pod IP if the HPA scaled out**

```bash
ssh topfull-master "kubectl get hpa frontend-hpa -n default; kubectl get pods -n default -l app=frontend -o wide"
```

If `REPLICAS` is still `1` for the whole run (likely at S1's low, well-within-capacity load — this is exactly what S1 "Normal Operation" is supposed to look like), that's an expected null result, not a Task 1 regression: the comma-join path only differs from the old single-IP path once there are 2+ replicas. To force a real multi-replica exercise, re-run with `experiments/configs/scenario_2_baseline.yaml` (or a heavier phase) if frontend CPU actually crosses the HPA's 85% target and a scale-out event appears in `kubectl get hpa` `REPLICAS`. If a scale-out is observed, pull the run's `service_inbound.csv` and confirm rows for `frontend` in that window show `total` climbing roughly in proportion to replica count (not flatlining as if only one pod were being scraped) — this is the concrete signal that Task 1's fix is doing its job, not the audit-only regression tests from Task 1 Step 1-3.

- [ ] **Step 4: Record completion**

No code change in this step. This task's purpose is a go/no-go gate before trusting any post-migration experiment numbers — if Steps 1-3 all come back clean, the migration (Tasks 1-6) is validated end-to-end and the next session can plan a fresh campaign under the Ron-config regime (explicitly out of scope for this plan, per spec §8/decision 6).

---

## Self-review

**1. Spec coverage.** Design spec §10 items #1-#6 are each covered: #1+#2 → "Known finding" note + Task 2 (the real generalization gap, corrected from the spec's stale premise) + Task 3 (frontend-replica guard). #3 → Task 4 (live CPU patch). #4 → Task 5 (frontend HPA, no productcatalog HPA). #5 → Task 3 (guard) plus the live audit note that nothing currently force-pins frontend at run time. #6 → Task 6 (proxy diff, derived live, not guessed). Items #7-#9 (namespace ResourceQuota, OS/pip, `ronnezer/*`/`hostNetwork`) are explicitly no-action rows per the user's instruction and have no task, matching spec §10's own table. The mandatory multi-replica aggregation-audit task is Task 1, placed first as instructed, and its finding (only `envoy_retry_collector.py` was unsafe) changed nothing about Tasks 2-6's sequencing beyond confirming Task 1 had to land before Task 4/5 rather than after. Task 7 is the final validation task per spec §10's suggested order (`kubectl describe node topfull-worker1` after atomic steps, short live smoke run before trusting numbers).

**2. Placeholder scan.** Every code block is complete, runnable Python/YAML/Go/bash with real values (no `TODO`, no "add appropriate error handling", no "similar to Task N" — Task 6's patch script is written out in full rather than referencing Task 2's `DETECTOR_OVERLAY_SNIPPET` pattern by name only). All CPU millicore values are copied verbatim from spec §4d. All SSH commands use host aliases per the always-applied rule, never a raw IP.

**3. Type/signature consistency.** `discover_service_pod_ips(cfg, services) -> Dict[str, str]` keeps its return type across Task 1 (only the string's contents change, from a single IP to a comma-joined list) — every caller (`start_envoy_retry_collector`, tested by `test_start_uploads_pod_ips_on_master`) is unaffected. `scrape_one_service(service: str, pod_ip: Optional[str], fetch_url: HttpFetcher) -> ServiceScrapeResult` keeps its exact signature; only `ServiceScrapeResult`'s field `evict_ip` gains a sibling `had_partial_failure`, and every existing call site/test that only reads `.edges`/`.inbound`/`.warning`/`.evict_ip` is unaffected. `topfull_cpu_quotas.paper_limit_for`/`paper_request_for`/`RECONCILE_SERVICES`/`PAPER_CPU_LIMIT_MILLICORES` keep their exact names and types across Task 2 — only their contents change; the new `container_name_for(service: str) -> str` is a pure addition consumed by `run_scenario.reconcile_paper_cpu_limits` (Task 2 Step 5) and the Task 4 kubectl commands (which hardcode the same "redis" value manually, since Task 4 is a live-cluster action, not code that imports the module).
