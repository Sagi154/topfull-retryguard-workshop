# Mesh Collector Network Scrape Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Using the writing-plans skill** to turn [2026-09-13-mesh-collector-network-scrape-design.md](../specs/2026-09-13-mesh-collector-network-scrape-design.md) into bite-sized TDD tasks. Do not re-litigate that spec.

**Goal:** Replace every Envoy mesh scrape (`kubectl exec` and `docker exec`) with a plain HTTP GET to `http://<pod_ip>:15020/stats/prometheus` from `topfull-master`, keep `service_edges.csv` / `service_inbound.csv` column names identical, fill outbound `2xx`/`4xx`/`5xx` from live Prometheus class counters, and delete the worker-local exec path.

**Architecture:** One collector process on master. Orchestrator seeds `service → pod_ip` once via `kubectl`. Each poll a thread pool GETs port 15020, parsers read Prometheus exposition format (label-block dict, not fixed label order), main thread writes CSVs serially into `record_path`. Fetch failure rate-limits a per-service re-seed (`TIER2_WARN_EVERY_POLLS`). Config field is `transport: network_prometheus` (no `exec_mode`).

**Tech Stack:** Python 3 stdlib (`urllib.request`, `concurrent.futures`, `csv`, `json`, `re`, `unittest`). OpenSSH host alias `topfull-master`. No new pip dependencies.

## Global Constraints

- Do not edit the spec. Do not change `EDGES_CSV_COLUMNS` / `INBOUND_CSV_COLUMNS`. Do not edit `retryguard.py`, `mentor_charts.py`, `resource_usage_collector.py`, or `topfull_throttle_collector.py`. Do not change `ensure_envoy_stats_enabled`.
- Do not backfill `campaign_48/` or `august_38/`.
- Single transport: `network_prometheus`. Remove `kubectl` / `docker_local` code paths; do not keep them as fallbacks.
- Rename `exec_mode` → `transport` in YAML, params JSON, and `run_manifest.json`. Manifest always records `transport: network_prometheus` and `exec_host: topfull-master`.
- Parse Prometheus `{...}` labels as key="value" pairs. Do not regex-anchor a fixed label order.
- Outbound class columns come from `envoy_cluster_upstream_rq{response_code_class="2xx|4xx|5xx",...}`, not from `response_code="200"` lines.
- Tier-2 (pod recreated / stale IP): rate-limited warning **and** rate-limited `kubectl` re-seed on master. Never crash `poll_once`. Never stop scraping other services.
- Thread pool for GET+parse; CSV writes stay serial on the main thread (no locking of `write_edges_csv` / `write_inbound_csv`).
- Unit tests: injected `CommandRunner` / `HttpFetcher` only — no real HTTP, SSH, Docker, or kubectl.
- Flip all 16 scenario YAML `transport` keys and delete `infra.worker_ssh_host` **after** the Task 8 live S1 credit trio, not before.
- Commits are optional. Use the wording "Commit (only if the user has asked to commit)" — do not commit mid-plan unless the user has asked.
- SSH: host aliases only; User is `idozacharia`. Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md).

## File map

| File | Responsibility |
|---|---|
| Modify: `experiments/envoy_retry_collector.py` | Prometheus parsers, HTTP GET fetch, `discover_pod_ip`, network-only `poll_once`, delete exec/docker |
| Modify: `experiments/test_envoy_retry_collector.py` | Replace admin-format + docker tests with Prometheus + HTTP + Tier-2 self-heal tests |
| Modify: `experiments/run_scenario.py` | Master-only start; seed pod IPs; delete worker deploy/stop/two-hop pull; manifest `transport` |
| Modify: `experiments/test_run_scenario.py` | Replace `TestMeshCollectorWorkerWiring`; update `TestEnvoyRetryCollectorWiring` |
| Modify: `experiments/configs/scenario_*.yaml` (all 16) | Task 9 only: `transport: network_prometheus`, drop `exec_mode` and `worker_ssh_host` |
| Modify: `AGENTS.md`, `Guides and Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md`, `Guides and Info/METRICS-GATHERED.md`, `Guides and Info/METRICS-COLLECTION-GUIDE.md`, `Guides and Info/PER-SERVICE-METRICS.md`, `experiments/README.md` | Task 9: collector now master-only HTTP 15020; RetryGuard live `service_inbound.csv` restored |

---

### Task 1: Live verification of port 15020 on all 11 Boutique pods

**Files:** none (commands only). If the VMs are `TERMINATED` or SSH times out, record the failure and continue to Task 2 using the spec §3.3 frontend shapes as the locked HTTP family. Re-run this task before Task 8 if the cluster was down. Never hardcode public IPs.

**Interfaces:**
- Consumes: nothing.
- Produces: a written lock — (a) master can GET `:15020/stats/prometheus` on every Boutique pod IP or a named exception list; (b) inbound metric family per service (copy exact metric names); (c) `redis-cart` parse is empty-edges / zero-inbound, not an error.

- [ ] **Step 1: Confirm SSH to master as `idozacharia` and list Boutique pods + IPs**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "whoami; kubectl get pods -n default -o custom-columns=NAME:.metadata.name,APP:.metadata.labels.app,IP:.status.podIP --no-headers"
```

Expected: `whoami` is `idozacharia`; 11 Boutique app pods with IPv4 addresses. If timeout / `TERMINATED`, record it and skip to Task 2.

- [ ] **Step 2: Confirm port 15020 from master on every listed pod IP**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get pods -n default -o jsonpath='{range .items[*]}{.metadata.labels.app}{\" \"}{.status.podIP}{\"\\n\"}{end}' | while read app ip; do [ -z \"\$ip\" ] && continue; code=\$(curl -s -o /tmp/p_\$app.txt -w '%{http_code}' --max-time 4 http://\$ip:15020/stats/prometheus); echo \$app \$ip HTTP_\$code lines=\$(wc -l < /tmp/p_\$app.txt); done"
```

Expected: every Boutique service prints `HTTP_200` and a non-zero line count. Record any service that is not 200.

- [ ] **Step 3: Lock inbound metric-name families (HTTP vs gRPC vs redis)**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "for app in frontend cartservice checkoutservice productcatalogservice paymentservice recommendationservice shippingservice currencyservice emailservice adservice redis-cart; do echo ===== \$app; grep -E 'downstream_rq_total|downstream_rq\{' /tmp/p_\$app.txt | head -n 8; done"
```

Decision (write it in the Task 8 notes / PR description, not in the spec):

- Same `envoy_http_inbound_<listener>_downstream_rq_*` family on every HTTP/gRPC service → Task 2 implements **only** that family.
- A different family on a named service → copy those exact metric names into Task 2's inbound fixture and add a second match in `parse_inbound` for that family only. Do not invent a family this step did not print.
- `redis-cart`: no HTTP inbound / no `outbound|*||*.default.svc.cluster.local` Boutique edges → Task 2 `parse_edges` empty dict and `parse_inbound` all zeros is success.

- [ ] **Step 4: Confirm outbound class counters exist on frontend**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "grep 'envoy_cluster_upstream_rq{' /tmp/p_frontend.txt | grep response_code_class | head -n 6; echo ---totals---; grep 'envoy_cluster_upstream_rq_total{' /tmp/p_frontend.txt | grep 'default.svc.cluster.local' | head -n 4; echo ---retry---; grep 'envoy_cluster_upstream_rq_retry{' /tmp/p_frontend.txt | grep 'default.svc.cluster.local' | head -n 4"
```

Expected: at least one `response_code_class="2xx"` line with `cluster_name="outbound|...||<svc>.default.svc.cluster.local"`. This is the locked outbound class source.

- [ ] **Step 5: No commit**

This task does not change the repo.

---

### Task 2: Prometheus label parser and rewrite `parse_edges` / `parse_inbound`

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (replace `OUTBOUND_RE` / `INBOUND_RE` and the two parse functions; keep CSV writers unchanged)
- Modify: `experiments/test_envoy_retry_collector.py` (`SAMPLE_MESH_STATS`, `TestParseEdges`, `TestParseInbound`; add `TestParsePromLabels`)

**Interfaces:**
- Consumes: spec §3.3 metric shapes; Task 1 inbound-family lock if the cluster was up.
- Produces:
  - `parse_prom_labels(label_block: str) -> Dict[str, str]`
  - `target_from_cluster_name(cluster_name: str) -> Optional[str]`
  - `parse_edges(stats_text: str) -> Dict[str, Dict[str, int]]` — same return shape as today (`OUTBOUND_METRICS` keys, missing → 0)
  - `parse_inbound(stats_text: str) -> Dict[str, int]` — same keys as `INBOUND_METRICS`; if multiple inbound listeners appear, keep the listener with the largest `total` (do **not** sum)
  - `EDGES_CSV_COLUMNS` / `INBOUND_CSV_COLUMNS` unchanged

- [ ] **Step 1: Replace the fixture and add failing parser tests**

In `experiments/test_envoy_retry_collector.py`, replace `SAMPLE_MESH_STATS` with Prometheus text (label order on the 4xx line is **reversed** on purpose):

```python
SAMPLE_MESH_STATS = """\
envoy_cluster_upstream_rq_total{cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 100
envoy_cluster_upstream_rq{response_code_class="2xx",cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 90
envoy_cluster_upstream_rq{cluster_name="outbound|80||cartservice.default.svc.cluster.local",response_code_class="4xx"} 8
envoy_cluster_upstream_rq{response_code_class="5xx",cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 2
envoy_cluster_upstream_rq_retry{cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 12
envoy_cluster_upstream_rq_total{cluster_name="outbound|9555||productcatalogservice.default.svc.cluster.local"} 50
envoy_cluster_upstream_rq_retry{cluster_name="outbound|9555||productcatalogservice.default.svc.cluster.local"} 3
envoy_cluster_upstream_rq{response_code="200",cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 90
envoy_cluster_upstream_rq_total{cluster_name="outbound|15010||istiod.istio-system.svc.cluster.local"} 9
envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 200
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="2xx"} 180
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="4xx"} 15
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="5xx"} 5
envoy_http_inbound_0_0_0_0_8080_downstream_rq_completed{} 180
"""
```

Keep existing `TestParseEdges` / `TestParseInbound` assertions (same numbers). Add:

```python
class TestParsePromLabels(unittest.TestCase):
    def test_empty_braces(self):
        self.assertEqual(erc.parse_prom_labels("{}"), {})

    def test_order_independent(self):
        a = erc.parse_prom_labels(
            '{response_code_class="2xx",cluster_name="outbound|80||cartservice.default.svc.cluster.local"}'
        )
        b = erc.parse_prom_labels(
            '{cluster_name="outbound|80||cartservice.default.svc.cluster.local",response_code_class="2xx"}'
        )
        self.assertEqual(a, b)
        self.assertEqual(a["response_code_class"], "2xx")
        self.assertEqual(
            a["cluster_name"],
            "outbound|80||cartservice.default.svc.cluster.local",
        )

    def test_strips_optional_braces(self):
        self.assertEqual(erc.parse_prom_labels('k="v"'), {"k": "v"})


class TestTargetFromClusterName(unittest.TestCase):
    def test_default_namespace_target(self):
        self.assertEqual(
            erc.target_from_cluster_name(
                "outbound|3550||productcatalogservice.default.svc.cluster.local"
            ),
            "productcatalogservice",
        )

    def test_ignores_istio_system(self):
        self.assertIsNone(
            erc.target_from_cluster_name(
                "outbound|15010||istiod.istio-system.svc.cluster.local"
            )
        )


class TestParseInboundDoesNotMergeListeners(unittest.TestCase):
    def test_keeps_listener_with_largest_total(self):
        text = (
            "envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 100\n"
            "envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class=\"2xx\"} 90\n"
            "envoy_http_inbound_0_0_0_0_9090_downstream_rq_total{} 50\n"
            "envoy_http_inbound_0_0_0_0_9090_downstream_rq{response_code_class=\"2xx\"} 50\n"
        )
        inbound = erc.parse_inbound(text)
        self.assertEqual(inbound["total"], 100)
        self.assertEqual(inbound["2xx"], 90)
```

Change `TestParseInbound.test_multiple_listener_ports_are_summed` to the class above (do not keep the old sum-to-150 assertion).

If Task 1 locked a second inbound family, add one fixture line of that exact metric and one assertion that `parse_inbound["total"]` picks it up.

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python experiments/test_envoy_retry_collector.py TestParsePromLabels TestTargetFromClusterName TestParseEdges TestParseInbound TestParseInboundDoesNotMergeListeners
```

Expected: FAIL — `parse_prom_labels` / `target_from_cluster_name` missing, or old admin-format parsers return `{}`.

- [ ] **Step 3: Implement parsers**

Replace `OUTBOUND_RE` / `INBOUND_RE` in `experiments/envoy_retry_collector.py` with:

```python
PROM_LINE_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
    r"(?P<labels>\{[^}]*\})?"
    r"\s+(?P<value>[0-9]+(?:\.[0-9]+)?)$"
)
CLUSTER_TARGET_RE = re.compile(
    r"^outbound\|[^|]*\|[^|]*\|"
    r"(?P<target>[\w-]+)\.default\.svc\.cluster\.local$"
)
LABEL_PAIR_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)="([^"]*)"')
INBOUND_TOTAL_NAME_RE = re.compile(
    r"^envoy_http_inbound_(?P<listener>[\w]+)_downstream_rq_total$"
)
INBOUND_CLASS_NAME_RE = re.compile(
    r"^envoy_http_inbound_(?P<listener>[\w]+)_downstream_rq$"
)


def parse_prom_labels(label_block: str) -> Dict[str, str]:
    text = (label_block or "").strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    return {m.group(1): m.group(2) for m in LABEL_PAIR_RE.finditer(text)}


def target_from_cluster_name(cluster_name: str) -> Optional[str]:
    m = CLUSTER_TARGET_RE.match(cluster_name or "")
    return m.group("target") if m else None
```

Replace `parse_edges` / `parse_inbound`:

```python
def parse_edges(stats_text: str) -> Dict[str, Dict[str, int]]:
    edges: Dict[str, Dict[str, int]] = {}

    def bucket(target: str) -> Dict[str, int]:
        if target not in edges:
            edges[target] = {k: 0 for k in OUTBOUND_METRICS}
        return edges[target]

    for line in stats_text.splitlines():
        m = PROM_LINE_RE.match(line.strip())
        if not m:
            continue
        labels = parse_prom_labels(m.group("labels") or "")
        target = target_from_cluster_name(labels.get("cluster_name", ""))
        if not target:
            continue
        name = m.group("name")
        value = int(float(m.group("value")))
        if name == "envoy_cluster_upstream_rq_total":
            bucket(target)["total"] = value
        elif name == "envoy_cluster_upstream_rq_retry":
            bucket(target)["retry"] = value
        elif name == "envoy_cluster_upstream_rq":
            klass = labels.get("response_code_class")
            if klass in ("2xx", "4xx", "5xx"):
                bucket(target)[klass] = value
    return edges


def parse_inbound(stats_text: str) -> Dict[str, int]:
    per_listener: Dict[str, Dict[str, int]] = {}

    def bucket(listener: str) -> Dict[str, int]:
        if listener not in per_listener:
            per_listener[listener] = {k: 0 for k in INBOUND_METRICS}
        return per_listener[listener]

    for line in stats_text.splitlines():
        m = PROM_LINE_RE.match(line.strip())
        if not m:
            continue
        name = m.group("name")
        value = int(float(m.group("value")))
        labels = parse_prom_labels(m.group("labels") or "")
        total_m = INBOUND_TOTAL_NAME_RE.match(name)
        class_m = INBOUND_CLASS_NAME_RE.match(name)
        if total_m:
            bucket(total_m.group("listener"))["total"] = value
        elif class_m:
            klass = labels.get("response_code_class")
            if klass in ("2xx", "4xx", "5xx"):
                bucket(class_m.group("listener"))[klass] = value
    if not per_listener:
        return {k: 0 for k in INBOUND_METRICS}
    chosen = max(per_listener.values(), key=lambda d: d["total"])
    return {k: chosen[k] for k in INBOUND_METRICS}
```

If Task 1 locked a second inbound family, add a third `if` on `name` using those exact strings. Do not add unused families.

Leave `write_edges_csv` / `write_inbound_csv` untouched.

- [ ] **Step 4: Run parser tests**

```powershell
python experiments/test_envoy_retry_collector.py TestParsePromLabels TestTargetFromClusterName TestParseEdges TestParseInbound TestParseInboundDoesNotMergeListeners TestWriteEdgesCsv TestWriteInboundCsv
```

Expected: `OK`. Docker / `poll_once` tests may still fail later; do not "fix" them by restoring admin-format parsers.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "Parse Envoy mesh stats from Prometheus exposition format"
```

---

### Task 3: HTTP GET fetch and `discover_pod_ip`

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (URL builder, `default_fetch_url`, `fetch_stats_text`, `discover_pod_ip`; delete docker helpers and `discover_pod_name` / old kubectl-exec `fetch_stats_text`)
- Modify: `experiments/test_envoy_retry_collector.py` (replace `TestDiscoverPodName` / `TestFetchStatsText` / all docker test classes that call deleted symbols)

**Interfaces:**
- Consumes: `SimpleResult`, `default_run_cmd`, `NAMESPACE`, `KUBECTL_TIMEOUT_SECONDS` (keep for kubectl discover).
- Produces:
  - `TRANSPORT_NETWORK_PROMETHEUS = "network_prometheus"`
  - `PROMETHEUS_STATS_PORT = 15020`
  - `HTTP_TIMEOUT_SECONDS = 15`
  - `HttpFetcher = Callable[[str], object]`
  - `prometheus_stats_url(pod_ip: str, port: int = PROMETHEUS_STATS_PORT) -> str` → `http://<ip>:15020/stats/prometheus`
  - `default_fetch_url(url: str) -> SimpleResult`
  - `fetch_stats_text(pod_ip: str, fetch_url: Optional[HttpFetcher] = None) -> Optional[str]`
  - `discover_pod_ip(service: str, run_cmd: Optional[CommandRunner] = None, namespace: str = NAMESPACE) -> Optional[str]`
- Deleted: `EXEC_MODE_*`, `resolve_exec_mode`, `docker_*`, `discover_container_id`, `fetch_stats_text_docker`, `discover_pod_name`, kubectl-exec `fetch_stats_text` argv.

`poll_once` still exists and will be broken until Task 4 — that is expected. After this task, parser tests and the new fetch/discover tests must pass. Delete docker unit-test classes in this task so `python experiments/test_envoy_retry_collector.py` does not import missing names. Leave `TestPollOnce` / `TestRunCollector` / docker poll tests failing or delete them here and rewrite in Task 4 — **delete them here** so the file is not red for missing symbols.

- [ ] **Step 1: Write failing fetch/discover tests; delete obsolete test classes**

Delete these classes from `experiments/test_envoy_retry_collector.py`: `TestDiscoverPodName`, `TestFetchStatsText`, `TestDockerPsContainerIdCmd`, `TestDiscoverContainerId`, `TestDockerExecStatsCmd`, `TestFetchStatsTextDocker`, `TestScrapeOneServiceDocker`, `TestPollOnce`, `TestPollOnceDockerLocal`, `TestPollOnceThreadPoolSerialWrites`, `TestResolveExecMode`, `TestRunCollector`, `TestRunCollectorDockerLocal`.

Add:

```python
class TestPrometheusStatsUrl(unittest.TestCase):
    def test_default_port_and_path(self):
        self.assertEqual(
            erc.prometheus_stats_url("192.168.148.90"),
            "http://192.168.148.90:15020/stats/prometheus",
        )


class TestDiscoverPodIp(unittest.TestCase):
    def test_builds_kubectl_jsonpath_for_pod_ip(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="192.168.148.90\n", stderr="")

        ip = erc.discover_pod_ip("frontend", run_cmd=runner)
        self.assertEqual(ip, "192.168.148.90")
        self.assertEqual(calls[0][:3], ["kubectl", "get", "pods"])
        self.assertIn("app=frontend", calls[0])
        self.assertTrue(any("podIP" in part for part in calls[0]))

    def test_returns_none_on_failure(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="error")

        self.assertIsNone(erc.discover_pod_ip("frontend", run_cmd=runner))

    def test_returns_none_on_empty_stdout(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="\n", stderr="")

        self.assertIsNone(erc.discover_pod_ip("frontend", run_cmd=runner))


class TestFetchStatsTextHttp(unittest.TestCase):
    def test_requests_prometheus_url(self):
        calls = []

        def fetch(url):
            calls.append(url)
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        text = erc.fetch_stats_text("192.168.148.90", fetch_url=fetch)
        self.assertEqual(text, SAMPLE_MESH_STATS)
        self.assertEqual(calls, [erc.prometheus_stats_url("192.168.148.90")])

    def test_returns_none_on_nonzero(self):
        def fetch(url):
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        self.assertIsNone(erc.fetch_stats_text("10.0.0.1", fetch_url=fetch))

    def test_returns_none_on_timeout_exception(self):
        def fetch(url):
            raise TimeoutError("timed out")

        self.assertIsNone(erc.fetch_stats_text("10.0.0.1", fetch_url=fetch))
```

Keep `TestShouldLogTier2`, `TestResolveServices`, tick/sleep tests, parser tests, CSV tests, `TestResolveRecordPath`.

- [ ] **Step 2: Run the new tests to verify they fail**

```powershell
python experiments/test_envoy_retry_collector.py TestPrometheusStatsUrl TestDiscoverPodIp TestFetchStatsTextHttp
```

Expected: FAIL — `prometheus_stats_url` / `discover_pod_ip` missing, or `fetch_stats_text` still builds `kubectl exec`.

- [ ] **Step 3: Implement fetch + discover; delete exec/docker helpers**

Add `import urllib.error` and `import urllib.request`.

```python
TRANSPORT_NETWORK_PROMETHEUS = "network_prometheus"
PROMETHEUS_STATS_PORT = 15020
HTTP_TIMEOUT_SECONDS = 15

HttpFetcher = Callable[[str], object]


def prometheus_stats_url(pod_ip: str, port: int = PROMETHEUS_STATS_PORT) -> str:
    return f"http://{pod_ip}:{port}/stats/prometheus"


def default_fetch_url(url: str) -> SimpleResult:
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return SimpleResult(returncode=0, stdout=body, stderr="")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return SimpleResult(returncode=1, stdout="", stderr=str(exc))


def fetch_stats_text(
    pod_ip: str,
    fetch_url: Optional[HttpFetcher] = None,
) -> Optional[str]:
    fetcher = fetch_url or default_fetch_url
    url = prometheus_stats_url(pod_ip)
    try:
        result = fetcher(url)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  fetch stats %s failed: %s", utc_now(), pod_ip, exc)
        return None
    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  fetch stats %s exit=%s stderr=%s",
            utc_now(),
            pod_ip,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None
    return getattr(result, "stdout", None)


def discover_pod_ip(
    service: str,
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> Optional[str]:
    runner = run_cmd or default_run_cmd
    cmd = [
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", f"app={service}",
        "-o", "jsonpath={.items[0].status.podIP}",
    ]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  discover ip %s failed: %s", utc_now(), service, exc)
        return None
    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  discover ip %s exit=%s stderr=%s",
            utc_now(),
            service,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None
    ip = (getattr(result, "stdout", "") or "").strip()
    return ip or None
```

Delete `discover_pod_name`, the kubectl-exec `fetch_stats_text` (replaced above), `docker_ps_container_id_cmd`, `docker_exec_stats_cmd`, `discover_container_id`, `fetch_stats_text_docker`, `EXEC_MODE_KUBECTL`, `EXEC_MODE_DOCKER_LOCAL`, `resolve_exec_mode`.

`poll_once` / `scrape_one_service` / `run_collector` / `main` will not compile until Task 4–6. **Stub them minimally** so the module imports:

```python
def scrape_one_service(*_a, **_k):
    raise NotImplementedError("Task 4")


def poll_once(*_a, **_k):
    raise NotImplementedError("Task 4")


def run_collector(*_a, **_k):
    raise NotImplementedError("Task 6")
```

Keep `should_log_tier2` as-is. Keep `ServiceScrapeResult` for Task 4 to rewrite.

- [ ] **Step 4: Run the collector test file**

```powershell
python experiments/test_envoy_retry_collector.py
```

Expected: `OK` for every remaining class (parsers, CSV, discover, fetch, tick, resolve_services, resolve_record_path, should_log_tier2). No docker/exec tests remain.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "Scrape Envoy mesh stats over HTTP to pod IP port 15020"
```

---

### Task 4: Network `scrape_one_service`, thread-pool `poll_once`, serial CSV writes

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (`ServiceScrapeResult`, `scrape_one_service`, `poll_once`, `_apply_scrape_results`)
- Modify: `experiments/test_envoy_retry_collector.py` (add poll/scrape tests)

**Interfaces:**
- Consumes: `fetch_stats_text`, `parse_edges`, `parse_inbound`, `write_edges_csv`, `write_inbound_csv`, `should_log_tier2`, `DEFAULT_MAX_WORKERS`.
- Produces:
  - `ServiceScrapeResult(service, edges=None, inbound=None, evict_ip=False, warning=None)` — no `container_id`
  - `scrape_one_service(service: str, pod_ip: Optional[str], fetch_url: HttpFetcher) -> ServiceScrapeResult`
  - `poll_once(record_path, services, timestamp, run_cmd=None, fetch_url=None, ip_cache=None, max_workers=DEFAULT_MAX_WORKERS, poll_index=0, tier2_warn_state=None) -> None`
  - `_apply_scrape_results(...)` writes CSVs serially; on `evict_ip` pops `ip_cache[service]`. **Do not re-seed yet** (Task 5).

- [ ] **Step 1: Write failing scrape + poll tests**

```python
class TestScrapeOneServiceHttp(unittest.TestCase):
    def test_parses_when_ip_present(self):
        def fetch(url):
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        result = erc.scrape_one_service("frontend", "192.168.1.10", fetch)
        self.assertIn("cartservice", result.edges)
        self.assertEqual(result.inbound["total"], 200)
        self.assertFalse(result.evict_ip)
        self.assertIsNone(result.warning)

    def test_missing_ip_is_warning(self):
        result = erc.scrape_one_service(
            "frontend", None, lambda url: SimpleNamespace(returncode=0, stdout="", stderr="")
        )
        self.assertIsNone(result.edges)
        self.assertIn("no seeded ip", result.warning)

    def test_fetch_failure_evicts_without_raising(self):
        def fetch(url):
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        result = erc.scrape_one_service("frontend", "10.0.0.1", fetch)
        self.assertTrue(result.evict_ip)
        self.assertIsNone(result.edges)
        self.assertIsNotNone(result.warning)


class TestPollOnceNetwork(unittest.TestCase):
    def test_writes_edges_and_inbound_for_every_service(self):
        import tempfile

        def fetch(url):
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            stats = (
                "envoy_cluster_upstream_rq_total"
                '{cluster_name="outbound|50051||paymentservice.default.svc.cluster.local"} 7\n'
                "envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 30\n"
            )
            return SimpleNamespace(returncode=0, stdout=stats, stderr="")

        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["frontend", "checkoutservice"],
                timestamp="2026-09-13T12:00:00Z",
                fetch_url=fetch,
                ip_cache={
                    "frontend": "192.168.1.10",
                    "checkoutservice": "192.168.1.11",
                },
            )
            edges_rows = list(csv.DictReader((Path(td) / "service_edges.csv").open(newline="")))
            inbound_rows = list(csv.DictReader((Path(td) / "service_inbound.csv").open(newline="")))
        self.assertEqual(
            {(r["caller"], r["target"]) for r in edges_rows},
            {
                ("frontend", "cartservice"),
                ("frontend", "productcatalogservice"),
                ("checkoutservice", "paymentservice"),
            },
        )
        self.assertEqual(edges_rows[0]["2xx"] != "" or True, True)
        fe = next(r for r in edges_rows if r["caller"] == "frontend" and r["target"] == "cartservice")
        self.assertEqual(fe["2xx"], "90")
        self.assertEqual({r["service"] for r in inbound_rows}, {"frontend", "checkoutservice"})

    def test_survives_one_service_fetch_failure(self):
        import tempfile

        def fetch(url):
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=1, stdout="", stderr="fail")
            return SimpleNamespace(
                returncode=0,
                stdout="envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 30\n",
                stderr="",
            )

        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["frontend", "checkoutservice"],
                timestamp="2026-09-13T12:00:00Z",
                fetch_url=fetch,
                ip_cache={
                    "frontend": "192.168.1.10",
                    "checkoutservice": "192.168.1.11",
                },
            )
            self.assertFalse((Path(td) / "service_edges.csv").exists())
            rows = list(csv.DictReader((Path(td) / "service_inbound.csv").open(newline="")))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["service"], "checkoutservice")


class TestPollOnceThreadPoolSerialWrites(unittest.TestCase):
    def test_one_inbound_row_per_service_and_writes_from_main_thread(self):
        import tempfile
        import threading
        from unittest import mock

        def fetch(url):
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            stats = (
                "envoy_cluster_upstream_rq_total"
                '{cluster_name="outbound|50051||paymentservice.default.svc.cluster.local"} 7\n'
                "envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 30\n"
            )
            return SimpleNamespace(returncode=0, stdout=stats, stderr="")

        write_threads = []
        real_write_inbound = erc.write_inbound_csv

        def spy_write_inbound(csv_path, timestamp, service, inbound):
            write_threads.append(threading.current_thread())
            return real_write_inbound(csv_path, timestamp, service, inbound)

        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(erc, "write_inbound_csv", side_effect=spy_write_inbound):
                erc.poll_once(
                    Path(td),
                    ["frontend", "checkoutservice"],
                    timestamp="2026-09-13T12:00:00Z",
                    fetch_url=fetch,
                    ip_cache={
                        "frontend": "192.168.1.10",
                        "checkoutservice": "192.168.1.11",
                    },
                    max_workers=2,
                )
            inbound = list(csv.DictReader((Path(td) / "service_inbound.csv").open(newline="")))
        self.assertEqual(len(inbound), 2)
        self.assertTrue(write_threads)
        self.assertTrue(all(t is threading.main_thread() for t in write_threads))

    def test_poll_once_uses_thread_pool_executor(self):
        import inspect

        src = inspect.getsource(erc.poll_once)
        self.assertIn("ThreadPoolExecutor", src)
        self.assertIn("as_completed", src)
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python experiments/test_envoy_retry_collector.py TestScrapeOneServiceHttp TestPollOnceNetwork TestPollOnceThreadPoolSerialWrites
```

Expected: FAIL — `NotImplementedError` or old `ServiceScrapeResult` fields.

- [ ] **Step 3: Implement scrape + poll**

```python
@dataclass
class ServiceScrapeResult:
    service: str
    edges: Optional[Dict[str, Dict[str, int]]] = None
    inbound: Optional[Dict[str, int]] = None
    evict_ip: bool = False
    warning: Optional[str] = None


def scrape_one_service(
    service: str,
    pod_ip: Optional[str],
    fetch_url: HttpFetcher,
) -> ServiceScrapeResult:
    if not pod_ip:
        return ServiceScrapeResult(
            service=service, warning=f"no seeded ip for service={service}"
        )
    stats_text = fetch_stats_text(pod_ip, fetch_url=fetch_url)
    if stats_text is None:
        return ServiceScrapeResult(
            service=service,
            evict_ip=True,
            warning=f"tier2 fetch failed service={service} ip={pod_ip}",
        )
    return ServiceScrapeResult(
        service=service,
        edges=parse_edges(stats_text),
        inbound=parse_inbound(stats_text),
    )


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
            else:
                log.warning("%s  WARNING  %s", utc_now(), result.warning)
        if result.edges is not None and result.inbound is not None:
            write_edges_csv(edges_path, timestamp, result.service, result.edges)
            write_inbound_csv(inbound_path, timestamp, result.service, result.inbound)
```

Task 5 will add the re-seed call inside the `should_log_tier2` branch. Do not call `discover_pod_ip` yet.

- [ ] **Step 4: Run collector tests**

```powershell
python experiments/test_envoy_retry_collector.py
```

Expected: `OK`.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "Poll mesh stats over HTTP with a serial CSV write path"
```

---

### Task 5: Tier-2 rate-limited re-seed

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (`_apply_scrape_results` only)
- Modify: `experiments/test_envoy_retry_collector.py`

**Interfaces:**
- Consumes: `discover_pod_ip`, `should_log_tier2`, `TIER2_WARN_EVERY_POLLS`.
- Produces: on `evict_ip` **and** `should_log_tier2(...)` is true, call `discover_pod_ip(service, run_cmd=run_cmd)` and if it returns an IP, set `ip_cache[service] = ip`. Re-seed at most once per `TIER2_WARN_EVERY_POLLS` polls per service (same gate as the warning).

- [ ] **Step 1: Write failing self-heal tests**

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
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python experiments/test_envoy_retry_collector.py TestTier2Reseed
```

Expected: FAIL — cache stays empty / no kubectl call, or re-seeds every poll (`len(kubectl_calls) == 5`).

- [ ] **Step 3: Re-seed inside the existing `should_log_tier2` branch**

In `_apply_scrape_results`, replace the tier2 warning block with:

```python
        if result.warning:
            if "tier2" in result.warning:
                if should_log_tier2(result.service, poll_index, tier2_warn_state):
                    log.warning("%s  WARNING  %s", utc_now(), result.warning)
                    new_ip = discover_pod_ip(result.service, run_cmd=run_cmd)
                    if new_ip:
                        ip_cache[result.service] = new_ip
            else:
                log.warning("%s  WARNING  %s", utc_now(), result.warning)
```

- [ ] **Step 4: Run the full collector suite**

```powershell
python experiments/test_envoy_retry_collector.py
```

Expected: `OK`.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "Re-seed mesh collector pod IPs after a rate-limited fetch failure"
```

---

### Task 6: `run_collector` and CLI — `transport` / `pod_ips` only

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (`run_collector`, `main`, module docstring)
- Modify: `experiments/test_envoy_retry_collector.py`

**Interfaces:**
- Consumes: `poll_once` from Task 4–5.
- Produces:
  - `run_collector(params, record_path, run_cmd=None, fetch_url=None, max_polls=None) -> None`
  - Reads `poll_interval_seconds`, `services`, `max_workers`, `pod_ips` (dict). Ignores `exec_mode` / `pod_names` if present.
  - Logs `transport=network_prometheus`.
  - `main()`: `--params` only (delete `--exec-mode`).

- [ ] **Step 1: Write failing `run_collector` test**

```python
class TestRunCollectorNetwork(unittest.TestCase):
    def test_uses_seeded_pod_ips(self):
        import tempfile

        calls = []

        def fetch(url):
            calls.append(url)
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.run_collector(
                {
                    "poll_interval_seconds": 1,
                    "max_workers": 2,
                    "services": ["frontend"],
                    "pod_ips": {"frontend": "192.168.1.10"},
                    "transport": "network_prometheus",
                },
                record_path,
                fetch_url=fetch,
                max_polls=1,
            )
            self.assertTrue((record_path / "service_inbound.csv").exists())
        self.assertEqual(calls, [erc.prometheus_stats_url("192.168.1.10")])
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
python experiments/test_envoy_retry_collector.py TestRunCollectorNetwork
```

Expected: FAIL — `NotImplementedError` or `run_collector` still reads `exec_mode` / `pod_names`.

- [ ] **Step 3: Implement `run_collector` and slim `main`**

```python
def run_collector(
    params: dict,
    record_path: Path,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[HttpFetcher] = None,
    max_polls: Optional[int] = None,
) -> None:
    services = resolve_services(params)
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    max_workers = int(params.get("max_workers", DEFAULT_MAX_WORKERS))
    ip_cache: Dict[str, str] = dict(params.get("pod_ips") or {})
    tier2_warn_state: Dict[str, int] = {}
    log.info(
        "%s  START  poll_interval=%ss services=%d transport=%s max_workers=%s",
        utc_now(), interval, len(services),
        TRANSPORT_NETWORK_PROMETHEUS, max_workers,
    )
    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        if max_polls is None:
            sleep_until_next_tick(interval)
            if _shutdown:
                break
        ts = tick_timestamp(interval)
        poll_once(
            record_path,
            services,
            timestamp=ts,
            run_cmd=run_cmd,
            fetch_url=fetch_url,
            ip_cache=ip_cache,
            max_workers=max_workers,
            poll_index=polls,
            tier2_warn_state=tier2_warn_state,
        )
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
    log.info("%s  EXIT", utc_now())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Envoy sidecar mesh-stats collector (Prometheus :15020)."
    )
    parser.add_argument(
        "--params",
        required=True,
        help="Path to collector params JSON "
        "(poll_interval_seconds, optional services, pod_ips, max_workers)",
    )
    args = parser.parse_args()
    params = load_params(args.params)
    record_path = resolve_record_path(params)
    record_path.mkdir(parents=True, exist_ok=True)
    setup_logging(record_path)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    run_collector(params, record_path)
```

Rewrite the module docstring Usage to:

```
Usage (on master, with venv active):
    python3 envoy_retry_collector.py --params /tmp/envoy_retry_params.json
```

Remove the worker / `--exec-mode` / `kubectl exec` sentences. Say each poll GETs `http://<pod_ip>:15020/stats/prometheus`.

- [ ] **Step 4: Run the full collector suite**

```powershell
python experiments/test_envoy_retry_collector.py
```

Expected: `OK`.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "Run the mesh collector with seeded pod IPs and one transport"
```

---

### Task 7: `run_scenario.py` — master-only deploy, seed IPs, delete worker path

**Files:**
- Modify: `experiments/run_scenario.py`
- Modify: `experiments/test_run_scenario.py`

**Interfaces:**
- Consumes: collector params keys from Task 6 (`pod_ips`, `transport`, `max_workers`).
- Produces:
  - `discover_service_pod_ips(cfg: dict, services: list) -> dict` — SSH master, `jsonpath={.items[0].status.podIP}`
  - `start_envoy_retry_collector(cfg)` always deploys to master, writes params with `transport: network_prometheus`, `pod_ips`, `max_workers`; tmux `envoyretry` / `/tmp/rg_envoy_retry.sh`; sources `venv_activate`
  - `envoy_collector_manifest(cfg) -> dict` sets `transport` and `exec_host` to master's SSH host
  - Deleted: `WORKER_MESH_ROOT`, `MANIFEST_EXEC_MODE_DOCKER`, `mesh_exec_mode`, `start_mesh_collector_on_worker`, `stop_worker_mesh_collector`, `pull_worker_mesh_csvs`, `discover_service_pod_map`
  - `collect_results` no longer two-hop pulls
  - `run()` no longer calls `stop_worker_mesh_collector`
  - Banner prints `transport: network_prometheus` instead of `exec_mode`

Existing `TestEnvoyRetryCollectorWiring` mocks `ssh` but does not mock seed. After this task, `start_envoy_retry_collector` will SSH once per service for IPs. **Patch those tests** to mock `discover_service_pod_ips`.

- [ ] **Step 1: Replace `TestMeshCollectorWorkerWiring` and update `TestEnvoyRetryCollectorWiring`**

Delete the entire `TestMeshCollectorWorkerWiring` class.

In `TestEnvoyRetryCollectorWiring`, add `@mock.patch("run_scenario.discover_service_pod_ips", return_value={})` to every test that calls `start_envoy_retry_collector` (upload, services override, patch-all, patch-override). In `test_start_uploads_params_and_launches_tmux` also assert:

```python
        self.assertEqual(params["transport"], "network_prometheus")
        self.assertEqual(params["pod_ips"], {})
        self.assertIn("max_workers", params)
        self.assertNotIn("exec_mode", params)
        self.assertNotIn("pod_names", params)
        self.assertNotIn("record_path", params)
```

Add a new class:

```python
class TestMeshCollectorNetworkWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "envoy_retry_collector_script":
                    "/home/idozacharia/experiments/envoy_retry_collector.py",
            },
            "envoy_retry_collector": {
                "enabled": enabled,
                "poll_interval_seconds": 1,
                "max_workers": 4,
            },
            "log_folder": "baseline_topfull_no_retryguard_sustained_overload_run99",
        }

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
        self.assertIn("jsonpath={.items[0].status.podIP}", mock_ssh.call_args_list[0].args[1])

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ensure_envoy_stats_enabled")
    @mock.patch("run_scenario.discover_service_pod_ips")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_uploads_pod_ips_on_master(
        self,
        mock_deploy,
        mock_ssh,
        mock_seed,
        mock_ensure,
        mock_write_json,
        mock_write_script,
        mock_wait,
    ):
        mock_seed.return_value = {"frontend": "192.168.1.10"}
        cfg = self._cfg()
        cfg["envoy_retry_collector"]["services"] = ["frontend"]
        run_scenario.start_envoy_retry_collector(cfg)
        mock_deploy.assert_called_once_with(
            "topfull-master",
            "envoy_retry_collector.py",
            "/home/idozacharia/experiments/envoy_retry_collector.py",
        )
        json_host, json_path, params = mock_write_json.call_args[0][:3]
        self.assertEqual(json_host, "topfull-master")
        self.assertEqual(params["transport"], "network_prometheus")
        self.assertEqual(params["pod_ips"], {"frontend": "192.168.1.10"})
        self.assertEqual(params["max_workers"], 4)
        self.assertNotIn("exec_mode", params)
        script_host, script_path, script_body = mock_write_script.call_args[0][:3]
        self.assertEqual(script_host, "topfull-master")
        self.assertEqual(script_path, "/tmp/rg_envoy_retry.sh")
        self.assertIn("source /home/idozacharia/TopFull/venv/bin/activate", script_body)
        self.assertIn("envoy_retry_collector.py --params /tmp/envoy_retry_params.json", script_body)
        self.assertNotIn("--exec-mode", script_body)
        tmux_calls = [
            c for c in mock_ssh.call_args_list
            if len(c.args) > 1 and "tmux new-session" in c.args[1] and "envoyretry" in c.args[1]
        ]
        self.assertEqual(len(tmux_calls), 1)
        self.assertEqual(tmux_calls[0].args[0], "topfull-master")

    @mock.patch("run_scenario.pull_worker_mesh_csvs", create=True)
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_collect_results_no_worker_pull(self, mock_ssh, mock_write_json, mock_pull):
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        cfg = {
            "infra": {
                "master_ssh_host": "topfull-master",
                "topfull_src_path": "/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src",
                "results_base_path": "/home/idozacharia/experiments/results",
            },
            "scenario_id": 2,
            "scenario_name": "sustained_overload",
            "condition": "baseline",
            "run_number": 99,
            "duration_seconds": 600,
            "retryguard": {"enabled": False},
            "log_folder": "test_run",
            "envoy_retry_collector": {
                "enabled": True,
                "poll_interval_seconds": 1,
                "max_workers": 4,
            },
        }
        run_scenario.collect_results(cfg)
        mock_pull.assert_not_called()
        manifest = [
            c.args[2]
            for c in mock_write_json.call_args_list
            if c.args[1].endswith("run_manifest.json")
        ][0]
        erc = manifest["envoy_retry_collector"]
        self.assertEqual(erc["transport"], "network_prometheus")
        self.assertEqual(erc["exec_host"], "topfull-master")
        self.assertNotIn("exec_mode", erc)
```

- [ ] **Step 2: Run the new tests to verify they fail**

```powershell
python experiments/test_run_scenario.py TestMeshCollectorNetworkWiring TestEnvoyRetryCollectorWiring
```

Expected: FAIL — `discover_service_pod_ips` missing, or start still branches to worker / writes `exec_mode`.

- [ ] **Step 3: Implement runner wiring and delete worker functions**

Replace `discover_service_pod_map` with:

```python
def discover_service_pod_ips(cfg: dict, services: list) -> dict:
    master = cfg["infra"]["master_ssh_host"]
    out = {}
    for svc in services:
        r = ssh(
            master,
            f"kubectl get pods -n default -l app={svc} "
            f"-o jsonpath={{.items[0].status.podIP}}",
            check=False,
        )
        ip = (r.stdout or "").strip()
        if ip:
            out[svc] = ip
        else:
            print(f"[WARN] No pod IP for app={svc} during mesh seed "
                  f"(stderr={(r.stderr or '').strip()})")
    return out
```

Rewrite `start_envoy_retry_collector` so the `docker_local` branch is gone. Always:

1. `deploy_repo_script(master, ...)`
2. `ensure_envoy_stats_enabled(cfg, services)`
3. `pod_ips = discover_service_pod_ips(cfg, services)`
4. params = `{poll_interval_seconds, transport: "network_prometheus", max_workers, pod_ips}` plus optional `services`
5. `write_remote_json(master, "/tmp/envoy_retry_params.json", params)`
6. launcher sources `venv_activate` and runs `python3 {script} --params /tmp/envoy_retry_params.json` (no `--exec-mode`)
7. `tmux new-session -d -s envoyretry /tmp/rg_envoy_retry.sh`

Delete `WORKER_MESH_ROOT`, `MANIFEST_EXEC_MODE_DOCKER`, `mesh_exec_mode`, `start_mesh_collector_on_worker`, `stop_worker_mesh_collector`, `pull_worker_mesh_csvs`.

```python
def envoy_collector_manifest(cfg: dict) -> dict:
    raw = dict(cfg.get("envoy_retry_collector") or {})
    raw.pop("exec_mode", None)
    raw["transport"] = "network_prometheus"
    raw["exec_host"] = cfg.get("infra", {}).get("master_ssh_host", "topfull-master")
    return raw
```

Remove the `if mesh_exec_mode == docker_local: pull_worker_mesh_csvs` block from `collect_results`.

Remove `stop_worker_mesh_collector(cfg)` from `run()`'s `finally`.

Replace the banner line `exec_mode` with `transport: network_prometheus`.

Grep the file for `worker_ssh_host`, `docker_local`, `mesh_exec_mode`, `exec_mode`, `mesh_local` — those strings must not remain except inside comments you are deleting.

- [ ] **Step 4: Run both test files**

```powershell
python experiments/test_envoy_retry_collector.py
python experiments/test_run_scenario.py
```

Expected: both `OK`.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "Run the mesh collector on master via seeded pod IPs"
```

---

### Task 8: Live S1 credit trio (gate before YAML defaults)

**Files:** none required except temporary edits to `experiments/configs/scenario_1_baseline.yaml` that you **restore** at the end of this task. Do not flip `transport` / delete `worker_ssh_host` on the other 15 YAMLs yet. Stale `exec_mode: docker_local` on S1 is ignored by Task 7 code.

**Interfaces:**
- Consumes: Task 7 runner + Task 6 collector on master.
- Produces: three scratch result folders on master and written P95/Fail deltas. Pass/fail is "mesh-on minus mesh-off is in the same ballpark as the documented throttle tax (+12 ms / +0.4pp)," not "zero" and not merely "better than +470 ms." The both-on arm is the same combined setting as campaign S1 / old run7 — record it so we can see whether throttle adds anything on top of the new mesh transport.

Read current `run_number` / `log_folder` in `scenario_1_baseline.yaml` first. As of the spec date that file was `run11` / `baseline_topfull_no_retryguard_normal_op_run11`. Use the **next free** trio (likely `run12` mesh-on/throttle-off, `run13` both off, `run14` both on). Never reuse a completed `log_folder`.

- [ ] **Step 1: Clear stale `/tmp` launchers and confirm cluster**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/rg_mesh_local.sh"
ssh topfull-master "kubectl get nodes; kubectl get pods -n default"
```

Expected: both nodes Ready; Boutique pods Running. If not, stop and fix per CONNECT-VMS.md / SETUP-GUIDE.md.

- [ ] **Step 2: Scratch run A — mesh ON, throttle OFF, 180 s, next free slot**

Edit only `experiments/configs/scenario_1_baseline.yaml`:

- `duration_seconds: 180`
- `topfull_throttle_collector.enabled: false`
- `envoy_retry_collector.enabled: true`
- `resource_usage_collector.enabled: true`
- bump `run_number` and `log_folder` to the next free **runN** (do not overwrite run11)

```powershell
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
```

Expected: collector tmux is `envoyretry` on **master** (not `meshlocal` on the worker). After teardown, `service_edges.csv` / `service_inbound.csv` / `envoy_retry_collector.log` exist **on master** under `results_base_path/<log_folder>/` with no two-hop pull. Header of `service_edges.csv` is still `timestamp,caller,target,total,2xx,4xx,5xx,retry`. At least one frontend→Boutique row has `2xx` **≠ 0** if Locust issued getcart/getproduct traffic.

- [ ] **Step 3: Scratch run B — mesh OFF, throttle OFF, 180 s, next free slot**

Same YAML: `envoy_retry_collector.enabled: false`, bump `run_number` / `log_folder` again, keep `duration_seconds: 180` and throttle off.

```powershell
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
```

Expected: no mesh CSVs in that folder.

- [ ] **Step 4: Scratch run C — mesh ON, throttle ON, 180 s, next free slot**

Same YAML: `envoy_retry_collector.enabled: true`, `topfull_throttle_collector.enabled: true`, `resource_usage_collector.enabled: true`, bump `run_number` / `log_folder` again, keep `duration_seconds: 180`.

```powershell
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
```

Expected: same mesh-file checks as Step 2 (CSVs on master, header unchanged, outbound `2xx` can be non-zero). Throttle CSVs (`topfull_throttle.csv` / `topfull_detect.csv`) are also present. This is the campaign-default collector pair (old run7).

- [ ] **Step 5: Compare getcart P95 and Fail (skip first 30 Locust seconds)**

Use each run's Locust `*_stats_history.csv` (or the same method used for the 2026-09-12 trio). Record:

| Slot | Arm | getcart P95 | getcart Fail |
|---|---|---|---|
| A | mesh on, throttle off | | |
| B | both off | | |
| C | mesh on, throttle on | | |

Mesh tax = A − B. Combined tax = C − B. Throttle-on-top-of-new-mesh = C − A. Compare mesh tax to documented throttle tax (+12 ms / +0.4pp) and old docker-exec tax (+470 ms / +25.2pp). Combined tax should look like old run7 vs run10 only if the new mesh is cheap; if C ≈ A, throttle is still negligible.

**Pass:** mesh tax is far closer to the throttle tax than to +470 ms (order of tens of ms / low Fail, not hundreds of ms / 25pp). **Fail:** tax still looks like docker-exec. Do not flip the 16 YAMLs (Task 9). Stop and diagnose (wrong process still exec'ing? collector still on worker?).

Do **not** raise Locust `user_counts`. These slots are not campaign S1.

- [ ] **Step 6: Restore `scenario_1_baseline.yaml` to campaign-ready defaults**

Set `duration_seconds: 300`, mesh+throttle+resource `enabled: true`, `run_number` / `log_folder` to the **next free slot after the three scratch runs**. Leave `exec_mode` / `worker_ssh_host` in place until Task 9.

- [ ] **Step 7: No commit unless the user asked** — do not commit scratch YAML mid-flight. Task 9 commits the restored + renamed keys together.

---

### Task 9: Flip 16 YAMLs and guides (only if Task 8 passed)

**Files:**
- Modify: all 16 `experiments/configs/scenario_*.yaml`
- Modify: `AGENTS.md` §4 mesh-collector bullet and §6 `/tmp` list (drop `rg_mesh_local.sh` as required)
- Modify: `Guides and Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md` (replace the 2026-09-12 worker-local paragraph)
- Modify: `Guides and Info/METRICS-GATHERED.md` Layer 1 writer paragraph
- Modify: `Guides and Info/METRICS-COLLECTION-GUIDE.md` mesh-collector rows
- Modify: `Guides and Info/PER-SERVICE-METRICS.md` if it still says worker-local / `exec_mode`
- Modify: `experiments/README.md` if it mentions `exec_mode` or `worker_ssh_host`

**Interfaces:**
- Consumes: Task 8 pass.
- Produces: every scenario YAML has `envoy_retry_collector.transport: network_prometheus` and no `exec_mode` / no `infra.worker_ssh_host`. Docs say master HTTP `:15020`, CSVs land in `record_path` during the run, RetryGuard can read inbound live, outbound class columns can be non-zero. `campaign_48/` / `august_38/` still historical.

- [ ] **Step 1: YAML search-replace on all 16 configs**

In each `experiments/configs/scenario_*.yaml`:

Replace:

```yaml
  exec_mode: docker_local
  # Thread-pool size for parallel docker exec scrapes on worker_ssh_host — NOT extra K8s/GCP worker VMs.
  max_workers: 4
```

with:

```yaml
  transport: network_prometheus
  # Thread-pool size for parallel HTTP GETs to pod :15020 — NOT extra K8s/GCP worker VMs.
  max_workers: 4
```

Delete the line `  worker_ssh_host: topfull-worker-1` from every `infra:` block.

- [ ] **Step 2: Confirm no leftover keys**

```powershell
python -c "from pathlib import Path; bad=[];
[bad.append(str(p)) for p in Path('experiments/configs').glob('scenario_*.yaml') if 'exec_mode' in p.read_text(encoding='utf-8') or 'worker_ssh_host' in p.read_text(encoding='utf-8')];
print('clean' if not bad else bad)"
```

Expected: `clean`.

- [ ] **Step 3: Guide edits (facts only)**

`METRICS-GATHERED.md` Layer 1 writer: collector process is on `topfull-master`; each poll is `GET http://<pod_ip>:15020/stats/prometheus`; files are written into the run `record_path` on master during the run (no worker two-hop). Mention `transport: network_prometheus`. State that outbound `2xx`/`4xx`/`5xx` on `service_edges.csv` are live on this transport (the old admin-port gap does not apply to **new** runs). Do not claim `campaign_48/` has those non-zero class columns.

`PER-SERVICE-MESH-COLLECTOR-DESIGN.md`: replace the **Worker-local exec (2026-09-12)** paragraph with a **Network scrape (2026-09-13)** paragraph matching the spec (master-only, port 15020, Tier-2 re-seed, RetryGuard live inbound). Keep the "no backfill" sentence.

`METRICS-COLLECTION-GUIDE.md`: table row and any `docker_local` / worker-local sentences.

`AGENTS.md` §4: mesh collector is master HTTP 15020; worker-local exec + teardown pull + RetryGuard-blind-for-the-run are no longer current. Do not duplicate the spec.

`experiments/README.md`: drop `exec_mode` / `worker_ssh_host` if mentioned.

Do not edit `retryguard.py`. One sentence in a guide is enough: with this transport, `measure_value()` can see `service_inbound.csv` mid-run because the file is on master.

- [ ] **Step 4: Re-run unit tests after YAML/docs-only edits**

```powershell
python experiments/test_envoy_retry_collector.py
python experiments/test_run_scenario.py
```

Expected: `OK`.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/configs AGENTS.md "Guides and Info" experiments/README.md
git commit -m "Default the mesh collector to master-side Prometheus scrapes"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|---|---|
| HTTP GET `:15020/stats/prometheus` | 3, 4 |
| Prometheus parsers + label-block dict + no fixed label order | 2 |
| Outbound class counters filled | 2 (fixture + `envoy_cluster_upstream_rq{response_code_class}`) + 8 live check |
| Master-only; delete worker deploy/stop/two-hop | 7 |
| Delete `kubectl`/`docker_local` transports | 3–7 |
| `transport` rename; single value `network_prometheus` | 6, 7, 9 |
| Seed `service → pod_ip` | 3, 7 |
| Tier-2 rate-limited re-seed | 5 |
| RetryGuard live inbound (side effect, no `retryguard.py` edit) | 7 (files on master) + 9 (doc) |
| Unchanged CSV column names | 2 (writers untouched) |
| Unit tests injected only | 2–7 |
| Live S1 credit trio before flipping 16 YAML defaults | 8 then 9 |
| Spec §7 verify all 11 pods / inbound families / redis-cart | 1 |
| Do not backfill campaigns; do not edit spec | Global + 9 |

No `TBD` / `TODO` left. `poll_once` / `scrape_one_service` / `run_collector` / `discover_service_pod_ips` names are consistent across tasks. Task 3 stubs `poll_once` only until Task 4 replaces the stub.
