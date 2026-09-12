# Mesh Collector Worker-Local Exec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Using the writing-plans skill** to turn [2026-09-12-mesh-collector-worker-local-exec-design.md](../specs/2026-09-12-mesh-collector-worker-local-exec-design.md) into bite-sized TDD tasks. Do not re-litigate that spec.

**Goal:** Move the full-mesh Envoy scrape loop from sequential `kubectl exec` on `topfull-master` to local `docker exec` on `topfull-worker-1`, keep `service_edges.csv` / `service_inbound.csv` byte-identical, and pull those files into the master's results folder at teardown.

**Architecture:** Keep a single `experiments/envoy_retry_collector.py` with `--exec-mode {kubectl,docker_local}` (params JSON can set the same key). Parsers and CSV writers stay untouched. `kubectl` mode is the default and preserves today's master-side sequential path so existing tests keep passing. `docker_local` uses the spec's two-tier discovery (orchestrator seeds `service → pod_name` once via `kubectl` on master; the worker resolves `pod_name → container_id` via `docker ps` labels), a 3–4 worker thread pool for exec+parse, and serial CSV writes on the main thread. `run_scenario.py` deploys/starts/stops the collector on `infra.worker_ssh_host` (`topfull-worker-1`) and two-hop `scp`s CSVs worker → Windows temp → master dest. **Fork rejected:** a second script would duplicate parsers/writers and split the test file for no gain.

**Tech Stack:** Python 3 stdlib (`concurrent.futures`, `csv`, `json`, `subprocess`, `argparse`, `unittest`), OpenSSH host aliases (`topfull-master`, `topfull-worker-1`), Docker CLI via cri-dockerd on the worker. No new pip dependencies.

## Global Constraints

- CRI is `docker exec` / `docker ps` via cri-dockerd; `crictl` is a documented fallback only if Task 1 proves `idozacharia` cannot use Docker on the worker.
- Two-tier discovery: orchestrator seeds `service → pod_name` once via `kubectl` on master; worker resolves container ID via `docker ps` labels (`io.kubernetes.pod.name`, `io.kubernetes.pod.namespace`, `io.kubernetes.container.name`).
- Thread pool of 3–4 workers for exec+parse; CSV writes stay serial on the main thread (no locking of `write_edges_csv` / `write_inbound_csv`).
- Two-hop `scp` at teardown only (orchestrator: worker → local temp → master dest). No shared filesystem. No worker→master SSH trust. No per-poll `scp`.
- New `infra.worker_ssh_host` (SSH alias, never a hardcoded IP). Always connect as `idozacharia` via the host alias.
- Byte-identical CSV schemas: `EDGES_CSV_COLUMNS` / `INBOUND_CSV_COLUMNS`, `OUTBOUND_RE` / `INBOUND_RE`, `parse_edges` / `parse_inbound`, `write_edges_csv` / `write_inbound_csv` — zero changes.
- Tier-2 pod recreation (new pod name) is an accepted v1 gap: log a rate-limited warning, keep scraping other services, do not self-heal via `kubectl` on the worker.
- Do not move `resource_usage_collector.py` or `topfull_throttle_collector.py`. Do not change `ensure_envoy_stats_enabled`. Do not edit `mentor_charts.py`. Do not backfill `campaign_48/` or `august_38/`.
- Do not edit the spec. No new pip dependencies. Unit tests use injected `CommandRunner` / mocked SSH — no real subprocess, SSH, Docker, or kubectl.
- Accepted v1 consequence of teardown-only pull: RetryGuard on master reads `{record_path}/service_inbound.csv` *during* the run. With `docker_local`, that file is on the worker until teardown, so `measure_value()` will SKIP for the whole run. Spec §3.4 already deferred periodic pull; do not add it here.
- Commits are optional. Use the wording "Commit (only if the user has asked to commit)" — do not commit mid-plan unless the user has asked.

## File map

| File | Responsibility |
|---|---|
| Modify: `experiments/envoy_retry_collector.py` | `--exec-mode`, docker command builders, container-ID cache, `scrape_one_service`, thread-pool `poll_once` branch, `record_path` from params |
| Modify: `experiments/test_envoy_retry_collector.py` | Tests for docker builders, seed consumption, Tier 1/2, serial writes after `as_completed()` |
| Modify: `experiments/run_scenario.py` | `scp_from`, seed discovery, start/stop on worker, two-hop pull, manifest `exec_mode` |
| Modify: `experiments/test_run_scenario.py` | Wiring tests for seed / worker start / stop / two-hop / manifest |
| Modify: `experiments/configs/scenario_*.yaml` (all 16) | `infra.worker_ssh_host`, `envoy_retry_collector.exec_mode`, `max_workers` |
| Modify: `AGENTS.md`, `Guides and Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md`, `Guides and Info/METRICS-GATHERED.md`, `Guides and Info/METRICS-COLLECTION-GUIDE.md`, `experiments/README.md` | Where the collector runs, teardown pull, accepted Tier-2 / RetryGuard-live gaps |

---

### Task 1: Pre-implementation verification on the VMs

**Files:** none (commands only). If the VMs are `TERMINATED` or SSH times out, still run every command below, record the failure, and continue to Task 2 assuming `docker exec` works (the design lock). Come back here before Task 9 live smoke. Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md) / `.cursor/rules/topfull-ssh.mdc` if IPs are stale — never hardcode IPs; use host aliases; User is `idozacharia`.

**Interfaces:**
- Consumes: nothing.
- Produces: a written decision — primary CRI is `docker` (expected) or `crictl` (only if Docker is unusable). Python on the worker is `python3` with no venv required (collector is stdlib-only).

- [ ] **Step 1: Confirm the SSH alias reaches the worker as `idozacharia`**

Run (from the Windows checkout, PowerShell):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "hostname; whoami; id; groups"
```

Expected: hostname of the worker VM; `whoami` prints `idozacharia`; `groups` is a space-separated list. If `Permission denied` or timeout, fix SSH per CONNECT-VMS.md (refresh `HostName`, do not invent an IP) and re-run this step. If the VM is down, record `TERMINATED` / timeout and continue.

- [ ] **Step 2: Confirm Docker group / passwordless `docker ps`**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "docker ps --format '{{.ID}} {{.Names}}' | head -n 20"
```

Expected: a list of container IDs/names including Boutique `k8s_istio-proxy_*` / `k8s_server_*` rows, exit 0, no password prompt.

If `permission denied` while trying to connect to the Docker daemon, run the fallback permission check (do not implement `crictl` yet — only record whether it would work):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "sudo -n docker ps >/dev/null && echo SUDO_DOCKER_OK; ls -l /var/run/docker.sock /var/run/cri-dockerd.sock; which crictl || echo NO_CRICTL; groups"
```

Decision:

- `docker ps` works as `idozacharia` → CRI = `docker` (locked). Do not implement `crictl`.
- only `sudo -n docker` works → stop and get `idozacharia` into the `docker` group (`sudo usermod -aG docker idozacharia`, then a new SSH login) before coding. Non-interactive tmux cannot type a sudo password.
- neither Docker path works but `crictl` + `cri-dockerd.sock` is readable → implement Task 2 command builders with the `crictl` shapes from spec §3.3 instead of `docker`. Same function names (`docker_ps_container_id_cmd` becomes a misnomer — rename to `local_ps_container_id_cmd` / `local_exec_stats_cmd` in that case only).
- VMs down → assume Docker works; implement `docker` builders.

- [ ] **Step 3: Confirm cri-dockerd Kubernetes labels on a live `istio-proxy` container**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "CID=$(docker ps --filter 'label=io.kubernetes.container.name=istio-proxy' --filter 'label=io.kubernetes.pod.namespace=default' --format '{{.ID}}' | head -n 1); echo CID=$CID; docker inspect `$CID --format '{{index .Config.Labels \"io.kubernetes.pod.name\"}} {{index .Config.Labels \"io.kubernetes.pod.namespace\"}} {{index .Config.Labels \"io.kubernetes.container.name\"}}'"
```

If PowerShell eats the nested quotes, run the inspect as a single remote script:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "CID=`$(docker ps --filter label=io.kubernetes.container.name=istio-proxy --filter label=io.kubernetes.pod.namespace=default --format '{{.ID}}' | head -n 1); echo CID=`$CID; docker inspect `$CID --format '{{json .Config.Labels}}'"
```

Expected: JSON labels include exactly `io.kubernetes.pod.name`, `io.kubernetes.pod.namespace`=`default`, `io.kubernetes.container.name`=`istio-proxy`. If the keys differ, stop and update the three `--filter label=` strings in Task 2 to the live keys before writing tests — do not invent aliases.

- [ ] **Step 4: Confirm local `docker exec` can curl Envoy admin**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "CID=`$(docker ps --filter label=io.kubernetes.container.name=istio-proxy --filter label=io.kubernetes.pod.namespace=default --format '{{.ID}}' | head -n 1); docker exec `$CID curl -s http://localhost:15000/stats | head -n 5"
```

Expected: at least one `cluster.` or `http.` stats line, exit 0. This is the command Task 2's `docker_exec_stats_cmd` must build.

- [ ] **Step 5: Confirm Python 3 on the worker (no TopFull venv required)**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "python3 --version; test -x /home/idozacharia/TopFull/venv/bin/python && echo HAS_TOPFULL_VENV || echo NO_TOPFULL_VENV; mkdir -p /home/idozacharia/experiments && echo EXPERIMENTS_DIR_OK"
```

Expected: `Python 3.x.y` (3.8+ is fine); `NO_TOPFULL_VENV` is acceptable — the collector is stdlib-only, so the worker launcher uses `python3`, not master's `venv_activate`. `EXPERIMENTS_DIR_OK` means `/home/idozacharia/experiments` is writable.

- [ ] **Step 6: Confirm master can still seed pod names (one-time kubectl, not per poll)**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get pods -n default -l app=frontend -o jsonpath='{.items[0].metadata.name}'; echo; whoami"
```

Expected: a pod name like `frontend-xxxxxxxxxx-xxxxx` and `idozacharia`. This is the selector Task 6's `discover_service_pod_map` must use.

- [ ] **Step 7: No commit**

This task does not change the repo.

---

### Task 2: Docker command builders and local discover/fetch

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (constants + two cmd builders + `discover_container_id` + `fetch_stats_text_docker`)
- Test: `experiments/test_envoy_retry_collector.py`

**Interfaces:**
- Consumes: existing `CommandRunner`, `NAMESPACE`, `KUBECTL_TIMEOUT_SECONDS`, `default_run_cmd`, `utc_now`, `log`.
- Produces:
  - `EXEC_MODE_KUBECTL = "kubectl"`
  - `EXEC_MODE_DOCKER_LOCAL = "docker_local"`
  - `DEFAULT_MAX_WORKERS = 4`
  - `TIER2_WARN_EVERY_POLLS = 30`
  - `docker_ps_container_id_cmd(pod_name: str, namespace: str = NAMESPACE) -> List[str]`
  - `docker_exec_stats_cmd(container_id: str) -> List[str]`
  - `discover_container_id(pod_name: str, run_cmd: Optional[CommandRunner] = None, namespace: str = NAMESPACE) -> Optional[str]`
  - `fetch_stats_text_docker(container_id: str, run_cmd: Optional[CommandRunner] = None) -> Optional[str]`
- Existing `discover_pod_name` / `fetch_stats_text` stay unchanged (kubectl mode).

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_envoy_retry_collector.py` (keep every existing class):

```python
class TestDockerPsContainerIdCmd(unittest.TestCase):
    def test_filters_three_k8s_labels(self):
        cmd = erc.docker_ps_container_id_cmd("frontend-abc123")
        self.assertEqual(cmd[0], "docker")
        self.assertIn("ps", cmd)
        self.assertIn("--filter", cmd)
        joined = " ".join(cmd)
        self.assertIn("label=io.kubernetes.pod.name=frontend-abc123", joined)
        self.assertIn("label=io.kubernetes.pod.namespace=default", joined)
        self.assertIn("label=io.kubernetes.container.name=istio-proxy", joined)
        self.assertIn("--format", cmd)
        self.assertIn("{{.ID}}", cmd)


class TestDiscoverContainerId(unittest.TestCase):
    def test_builds_docker_ps_and_returns_id(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="deadbeef12ab\n", stderr="")

        cid = erc.discover_container_id("frontend-abc123", run_cmd=runner)
        self.assertEqual(cid, "deadbeef12ab")
        self.assertEqual(calls[0], erc.docker_ps_container_id_cmd("frontend-abc123"))

    def test_returns_none_on_failure(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="error")

        self.assertIsNone(erc.discover_container_id("frontend-abc123", run_cmd=runner))

    def test_returns_none_on_empty_stdout(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="\n", stderr="")

        self.assertIsNone(erc.discover_container_id("frontend-abc123", run_cmd=runner))


class TestDockerExecStatsCmd(unittest.TestCase):
    def test_exact_argv(self):
        self.assertEqual(
            erc.docker_exec_stats_cmd("deadbeef12ab"),
            ["docker", "exec", "deadbeef12ab", "curl", "-s", "http://localhost:15000/stats"],
        )


class TestFetchStatsTextDocker(unittest.TestCase):
    def test_builds_docker_exec_command(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        text = erc.fetch_stats_text_docker("deadbeef12ab", run_cmd=runner)
        self.assertEqual(text, SAMPLE_MESH_STATS)
        self.assertEqual(calls[0], ["docker", "exec", "deadbeef12ab", "curl", "-s", "http://localhost:15000/stats"])

    def test_returns_none_on_nonzero_exit(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="No such container")

        self.assertIsNone(erc.fetch_stats_text_docker("oldid", run_cmd=runner))

    def test_returns_none_on_timeout_exception(self):
        def runner(cmd):
            raise TimeoutError("timed out")

        self.assertIsNone(erc.fetch_stats_text_docker("oldid", run_cmd=runner))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestDockerPsContainerIdCmd TestDiscoverContainerId TestDockerExecStatsCmd TestFetchStatsTextDocker`

Expected: FAIL with `AttributeError: module 'envoy_retry_collector' has no attribute 'docker_ps_container_id_cmd'` (or the first missing name).

- [ ] **Step 3: Implement the builders and local discover/fetch**

In `experiments/envoy_retry_collector.py`, add these constants next to `KUBECTL_TIMEOUT_SECONDS`:

```python
EXEC_MODE_KUBECTL = "kubectl"
EXEC_MODE_DOCKER_LOCAL = "docker_local"
DEFAULT_MAX_WORKERS = 4
TIER2_WARN_EVERY_POLLS = 30
```

Immediately after `fetch_stats_text`, add:

```python
def docker_ps_container_id_cmd(pod_name: str, namespace: str = NAMESPACE) -> List[str]:
    return [
        "docker",
        "ps",
        "--filter",
        f"label=io.kubernetes.pod.name={pod_name}",
        "--filter",
        f"label=io.kubernetes.pod.namespace={namespace}",
        "--filter",
        "label=io.kubernetes.container.name=istio-proxy",
        "--format",
        "{{.ID}}",
    ]


def docker_exec_stats_cmd(container_id: str) -> List[str]:
    return [
        "docker",
        "exec",
        container_id,
        "curl",
        "-s",
        "http://localhost:15000/stats",
    ]


def discover_container_id(
    pod_name: str,
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> Optional[str]:
    """Return the live istio-proxy container ID for pod_name, or None."""
    runner = run_cmd or default_run_cmd
    cmd = docker_ps_container_id_cmd(pod_name, namespace=namespace)
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001 — keep poll loop alive
        log.warning("%s  WARNING  docker ps %s failed: %s", utc_now(), pod_name, exc)
        return None

    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  docker ps %s exit=%s stderr=%s",
            utc_now(),
            pod_name,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None

    lines = [
        line.strip()
        for line in (getattr(result, "stdout", "") or "").splitlines()
        if line.strip()
    ]
    return lines[0] if lines else None


def fetch_stats_text_docker(
    container_id: str,
    run_cmd: Optional[CommandRunner] = None,
) -> Optional[str]:
    """docker exec into the local istio-proxy container and curl /stats."""
    runner = run_cmd or default_run_cmd
    cmd = docker_exec_stats_cmd(container_id)
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001 — TimeoutError etc.
        log.warning(
            "%s  WARNING  docker exec %s failed: %s", utc_now(), container_id, exc
        )
        return None

    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  docker exec %s exit=%s stderr=%s",
            utc_now(),
            container_id,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None

    return getattr(result, "stdout", None)
```

Do **not** change `parse_edges`, `parse_inbound`, `write_edges_csv`, `write_inbound_csv`, `discover_pod_name`, or `fetch_stats_text`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_envoy_retry_collector.py`

Expected: `OK` (existing classes plus the four new ones).

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "Add docker ps/exec builders for worker-local mesh scrape"
```

---

### Task 3: Seeded pod map, `scrape_one_service`, and docker_local `poll_once` (sequential)

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (`ServiceScrapeResult`, `scrape_one_service`, `should_log_tier2`, extend `poll_once`)
- Test: `experiments/test_envoy_retry_collector.py`

**Interfaces:**
- Consumes: Task 2 functions; existing `parse_edges` / `parse_inbound` / `write_edges_csv` / `write_inbound_csv`.
- Produces:
  - `ServiceScrapeResult(service, edges, inbound, container_id, evict_container, warning)`
  - `should_log_tier2(service: str, poll_index: int, state: Dict[str, int]) -> bool`
  - `scrape_one_service(service: str, pod_name: Optional[str], cached_container_id: Optional[str], run_cmd: CommandRunner) -> ServiceScrapeResult`
  - `poll_once(..., exec_mode: str = EXEC_MODE_KUBECTL, container_cache: Optional[Dict[str, str]] = None, pod_names: Optional[Dict[str, str]] = None, max_workers: int = DEFAULT_MAX_WORKERS, poll_index: int = 0, tier2_warn_state: Optional[Dict[str, int]] = None) -> None`
- `exec_mode=kubectl` (default) keeps today's sequential kubectl loop so `TestPollOnce` / `TestRunCollector` stay green. This task's docker_local branch is sequential; Task 4 wraps it in a thread pool.

- [ ] **Step 1: Write the failing tests**

Append:

```python
class TestShouldLogTier2(unittest.TestCase):
    def test_logs_first_then_is_bounded(self):
        state = {}
        logged = []
        for i in range(5):
            if erc.should_log_tier2("frontend", i, state):
                logged.append(i)
        self.assertEqual(logged, [0])

    def test_logs_again_after_interval(self):
        state = {}
        self.assertTrue(erc.should_log_tier2("frontend", 0, state))
        self.assertTrue(
            erc.should_log_tier2("frontend", erc.TIER2_WARN_EVERY_POLLS, state)
        )


class TestScrapeOneServiceDocker(unittest.TestCase):
    def test_uses_cached_id_without_docker_ps(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        result = erc.scrape_one_service(
            "frontend",
            pod_name="frontend-1",
            cached_container_id="cid-old",
            run_cmd=runner,
        )
        self.assertEqual(result.service, "frontend")
        self.assertIn("cartservice", result.edges)
        self.assertEqual(result.inbound["total"], 200)
        self.assertEqual(result.container_id, "cid-old")
        self.assertFalse(result.evict_container)
        self.assertIsNone(result.warning)
        self.assertTrue(all(c[:2] != ["docker", "ps"] for c in calls))

    def test_resolves_id_via_docker_ps_on_cache_miss(self):
        def runner(cmd):
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-new\n", stderr="")
            if cmd[:3] == ["docker", "exec", "cid-new"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        result = erc.scrape_one_service(
            "frontend",
            pod_name="frontend-1",
            cached_container_id=None,
            run_cmd=runner,
        )
        self.assertEqual(result.container_id, "cid-new")
        self.assertIsNotNone(result.edges)

    def test_exec_failure_evicts_without_raising(self):
        def runner(cmd):
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=1, stdout="", stderr="No such container")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        result = erc.scrape_one_service(
            "frontend",
            pod_name="frontend-1",
            cached_container_id="cid-old",
            run_cmd=runner,
        )
        self.assertTrue(result.evict_container)
        self.assertIsNone(result.edges)
        self.assertIsNotNone(result.warning)

    def test_missing_pod_name_is_warning_not_raise(self):
        result = erc.scrape_one_service(
            "frontend",
            pod_name=None,
            cached_container_id=None,
            run_cmd=lambda cmd: SimpleNamespace(returncode=0, stdout="", stderr=""),
        )
        self.assertIsNone(result.edges)
        self.assertIn("no seeded pod", result.warning)


class TestPollOnceDockerLocal(unittest.TestCase):
    def test_seeded_pod_names_skip_kubectl(self):
        import tempfile

        calls = []

        def runner(cmd):
            calls.append(cmd)
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-fe\n", stderr="")
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["frontend"],
                timestamp="2026-09-12T12:00:00Z",
                run_cmd=runner,
                exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                pod_names={"frontend": "frontend-1"},
                container_cache={},
            )
            inbound = list(
                csv.DictReader((Path(td) / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual(len(inbound), 1)
        self.assertEqual(inbound[0]["service"], "frontend")
        self.assertTrue(all(c[0] != "kubectl" for c in calls))

    def test_tier1_recovers_on_next_poll(self):
        import tempfile

        state = {"execs": 0}

        def runner(cmd):
            if cmd[:2] == ["docker", "exec"]:
                state["execs"] += 1
                if cmd[2] == "cid-old":
                    return SimpleNamespace(returncode=1, stdout="", stderr="No such container")
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-new\n", stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        cache = {"frontend-1": "cid-old"}
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-12T12:00:00Z",
                run_cmd=runner,
                exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                pod_names={"frontend": "frontend-1"},
                container_cache=cache,
            )
            self.assertFalse((record_path / "service_inbound.csv").exists())
            self.assertNotIn("frontend-1", cache)

            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-12T12:00:01Z",
                run_cmd=runner,
                exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                pod_names={"frontend": "frontend-1"},
                container_cache=cache,
            )
            inbound = list(
                csv.DictReader((record_path / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual(cache.get("frontend-1"), "cid-new")
        self.assertEqual(len(inbound), 1)

    def test_tier2_warns_and_continues_other_services(self):
        import tempfile
        from unittest import mock

        def runner(cmd):
            joined = " ".join(cmd)
            if cmd[:2] == ["docker", "ps"] and "missing-pod" in joined:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-ok\n", stderr="")
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        warn_state = {}
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            with mock.patch.object(erc.log, "warning") as warn:
                for i in range(5):
                    erc.poll_once(
                        record_path,
                        ["frontend", "checkoutservice"],
                        timestamp="2026-09-12T12:00:00Z",
                        run_cmd=runner,
                        exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                        pod_names={
                            "frontend": "missing-pod",
                            "checkoutservice": "checkout-1",
                        },
                        container_cache={},
                        poll_index=i,
                        tier2_warn_state=warn_state,
                    )
                self.assertLessEqual(warn.call_count, 2)
            inbound = list(
                csv.DictReader((record_path / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual({r["service"] for r in inbound}, {"checkoutservice"})
        self.assertEqual(len(inbound), 5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestShouldLogTier2 TestScrapeOneServiceDocker TestPollOnceDockerLocal`

Expected: FAIL — `scrape_one_service` / `should_log_tier2` missing.

- [ ] **Step 3: Implement scrape + docker_local sequential `poll_once`**

At the top of `experiments/envoy_retry_collector.py`, add:

```python
from dataclasses import dataclass
```

After `fetch_stats_text_docker`, add:

```python
@dataclass
class ServiceScrapeResult:
    service: str
    edges: Optional[Dict[str, Dict[str, int]]] = None
    inbound: Optional[Dict[str, int]] = None
    container_id: Optional[str] = None
    evict_container: bool = False
    warning: Optional[str] = None


def should_log_tier2(service: str, poll_index: int, state: Dict[str, int]) -> bool:
    last = state.get(service)
    if last is None or poll_index - last >= TIER2_WARN_EVERY_POLLS:
        state[service] = poll_index
        return True
    return False


def scrape_one_service(
    service: str,
    pod_name: Optional[str],
    cached_container_id: Optional[str],
    run_cmd: CommandRunner,
) -> ServiceScrapeResult:
    """
    Read-only scrape for one service in docker_local mode.

    Does not write CSVs and does not mutate caches. Main thread applies
    evict / container_id after the batch completes.
    """
    if not pod_name:
        return ServiceScrapeResult(
            service=service, warning=f"no seeded pod for service={service}"
        )

    container_id = cached_container_id
    if not container_id:
        container_id = discover_container_id(pod_name, run_cmd=run_cmd)
        if not container_id:
            return ServiceScrapeResult(
                service=service,
                evict_container=True,
                warning=(
                    f"tier2 stale pod service={service} pod={pod_name} "
                    "(pod recreated? v1 does not re-seed)"
                ),
            )

    stats_text = fetch_stats_text_docker(container_id, run_cmd=run_cmd)
    if stats_text is None:
        return ServiceScrapeResult(
            service=service,
            evict_container=True,
            warning=f"docker exec failed service={service} container={container_id}",
        )

    return ServiceScrapeResult(
        service=service,
        edges=parse_edges(stats_text),
        inbound=parse_inbound(stats_text),
        container_id=container_id,
    )
```

Replace `poll_once` with this version (kubectl branch is the current loop, unchanged):

```python
def poll_once(
    record_path: Path,
    services: List[str],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    pod_cache: Optional[Dict[str, str]] = None,
    exec_mode: str = EXEC_MODE_KUBECTL,
    container_cache: Optional[Dict[str, str]] = None,
    pod_names: Optional[Dict[str, str]] = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    poll_index: int = 0,
    tier2_warn_state: Optional[Dict[str, int]] = None,
) -> None:
    """
    One scrape of every service's sidecar. Writes rows into
    service_edges.csv and service_inbound.csv. Survives per-service
    failures (a failed exec just skips that service this poll).
    """
    if pod_cache is None:
        pod_cache = {}
    if container_cache is None:
        container_cache = {}
    if pod_names is None:
        pod_names = {}
    if tier2_warn_state is None:
        tier2_warn_state = {}
    runner = run_cmd or default_run_cmd

    edges_path = record_path / "service_edges.csv"
    inbound_path = record_path / "service_inbound.csv"

    if exec_mode == EXEC_MODE_DOCKER_LOCAL:
        results: List[ServiceScrapeResult] = []
        for service in sorted(services):
            pod = pod_names.get(service)
            cached = container_cache.get(pod) if pod else None
            results.append(
                scrape_one_service(service, pod, cached, runner)
            )
        _apply_scrape_results(
            results,
            pod_names,
            container_cache,
            edges_path,
            inbound_path,
            timestamp,
            poll_index,
            tier2_warn_state,
        )
        return

    for service in sorted(services):
        pod = pod_cache.get(service)
        if not pod:
            pod = discover_pod_name(service, run_cmd=runner)
            if pod:
                pod_cache[service] = pod
            else:
                log.warning("%s  WARNING  no pod for service=%s", utc_now(), service)
                continue

        stats_text = fetch_stats_text(pod, run_cmd=runner)
        if stats_text is None:
            pod_cache.pop(service, None)
            continue

        edges = parse_edges(stats_text)
        inbound = parse_inbound(stats_text)
        write_edges_csv(edges_path, timestamp, service, edges)
        write_inbound_csv(inbound_path, timestamp, service, inbound)


def _apply_scrape_results(
    results: List[ServiceScrapeResult],
    pod_names: Dict[str, str],
    container_cache: Dict[str, str],
    edges_path: Path,
    inbound_path: Path,
    timestamp: str,
    poll_index: int,
    tier2_warn_state: Dict[str, int],
) -> None:
    for result in sorted(results, key=lambda r: r.service):
        pod = pod_names.get(result.service)
        if result.evict_container and pod:
            container_cache.pop(pod, None)
        if result.container_id and pod and result.edges is not None:
            container_cache[pod] = result.container_id
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

`max_workers` is accepted but unused until Task 4 — do not delete the parameter.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_envoy_retry_collector.py`

Expected: `OK`. Existing `TestPollOnce` still uses default `exec_mode=kubectl`.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "Scrape mesh stats via seeded pods and local docker exec"
```

---

### Task 4: Thread-pool exec+parse, serial CSV writes

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (docker_local branch of `poll_once` only)
- Test: `experiments/test_envoy_retry_collector.py`

**Interfaces:**
- Consumes: `scrape_one_service`, `_apply_scrape_results`, `DEFAULT_MAX_WORKERS` from Task 3.
- Produces: docker_local `poll_once` submits one `scrape_one_service` per service to `concurrent.futures.ThreadPoolExecutor(max_workers=...)`, then calls `_apply_scrape_results` on the main thread after `as_completed()`.

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestPollOnceThreadPoolSerialWrites(unittest.TestCase):
    def test_one_inbound_row_per_service_and_writes_from_main_thread(self):
        import tempfile
        import threading
        from unittest import mock

        def runner(cmd):
            if cmd[:2] == ["docker", "ps"]:
                pod = "frontend-1" if "frontend-1" in " ".join(cmd) else "checkout-1"
                return SimpleNamespace(
                    returncode=0,
                    stdout=("cid-fe\n" if pod == "frontend-1" else "cid-co\n"),
                    stderr="",
                )
            if cmd[:2] == ["docker", "exec"]:
                if cmd[2] == "cid-fe":
                    return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
                stats = (
                    "cluster.outbound|50051||paymentservice.default."
                    "svc.cluster.local.upstream_rq_total: 7\n"
                    "http.inbound_0.0.0.0_8080.downstream_rq_total: 30\n"
                )
                return SimpleNamespace(returncode=0, stdout=stats, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

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
                    timestamp="2026-09-12T12:00:00Z",
                    run_cmd=runner,
                    exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                    pod_names={
                        "frontend": "frontend-1",
                        "checkoutservice": "checkout-1",
                    },
                    container_cache={},
                    max_workers=2,
                )
            inbound = list(
                csv.DictReader((Path(td) / "service_inbound.csv").open(newline=""))
            )
            edges = list(
                csv.DictReader((Path(td) / "service_edges.csv").open(newline=""))
            )

        self.assertEqual(
            {r["service"] for r in inbound},
            {"frontend", "checkoutservice"},
        )
        self.assertEqual(len(inbound), 2)
        self.assertEqual(
            {(r["caller"], r["target"]) for r in edges},
            {
                ("frontend", "cartservice"),
                ("frontend", "productcatalogservice"),
                ("checkoutservice", "paymentservice"),
            },
        )
        self.assertTrue(write_threads)
        self.assertTrue(all(t is threading.main_thread() for t in write_threads))

    def test_docker_local_branch_uses_thread_pool_executor(self):
        import inspect

        src = inspect.getsource(erc.poll_once)
        self.assertIn("ThreadPoolExecutor", src)
        self.assertIn("as_completed", src)
```

`test_one_inbound_row_per_service_and_writes_from_main_thread` already passes on the Task 3 sequential loop (writes are on the main thread) — keep it as the race/duplicate-row guard. `test_docker_local_branch_uses_thread_pool_executor` is the red test for this task.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestPollOnceThreadPoolSerialWrites`

Expected: FAIL — `AssertionError` that `ThreadPoolExecutor` is not in `poll_once` source.

- [ ] **Step 3: Wrap docker_local fetches in a thread pool**

Add the import at the top of `experiments/envoy_retry_collector.py`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
```

Replace only the docker_local body inside `poll_once` (the `if exec_mode == EXEC_MODE_DOCKER_LOCAL:` block) with:

```python
    if exec_mode == EXEC_MODE_DOCKER_LOCAL:
        workers = max(1, int(max_workers or DEFAULT_MAX_WORKERS))

        def _submit(service: str) -> ServiceScrapeResult:
            pod = pod_names.get(service)
            cached = container_cache.get(pod) if pod else None
            return scrape_one_service(service, pod, cached, runner)

        results: List[ServiceScrapeResult] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_submit, service): service for service in services}
            for fut in as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001 — never crash poll_once
                    svc = futs[fut]
                    log.warning(
                        "%s  WARNING  scrape %s raised: %s", utc_now(), svc, exc
                    )
        _apply_scrape_results(
            results,
            pod_names,
            container_cache,
            edges_path,
            inbound_path,
            timestamp,
            poll_index,
            tier2_warn_state,
        )
        return
```

Do not call `write_edges_csv` / `write_inbound_csv` from `_submit`. Cache mutation stays in `_apply_scrape_results` on the main thread.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_envoy_retry_collector.py`

Expected: `OK`, including `TestPollOnceThreadPoolSerialWrites` (writes still on the main thread) and both Tier-1 / Tier-2 tests.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "Parallelize worker-local Envoy scrapes with serial CSV writes"
```

---

### Task 5: `--exec-mode`, params, and `record_path` on the worker

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (`resolve_exec_mode`, `resolve_record_path`, `run_collector`, `main`)
- Test: `experiments/test_envoy_retry_collector.py`

**Interfaces:**
- Consumes: `EXEC_MODE_*`, `poll_once` kwargs from Tasks 2–4.
- Produces:
  - `resolve_exec_mode(params: dict, cli_exec_mode: Optional[str] = None) -> str` — CLI wins if set; else `params["exec_mode"]`; else `kubectl`
  - `resolve_record_path(params: dict, global_config_path: str = GLOBAL_CONFIG_PATH) -> Path` — `params["record_path"]` if present, else today's `load_record_path()`
  - `run_collector` reads `exec_mode`, `pod_names`, `max_workers` from params and passes them through; seeds `container_cache = {}` and `tier2_warn_state = {}`
  - `main()` adds `--exec-mode {kubectl,docker_local}`

The worker has no TopFull `global_config.json`. `docker_local` runs **must** get `record_path` from params (`/home/idozacharia/experiments/mesh_local/<log_folder>`).

- [ ] **Step 1: Write the failing tests**

Append:

```python
class TestResolveExecMode(unittest.TestCase):
    def test_defaults_to_kubectl(self):
        self.assertEqual(erc.resolve_exec_mode({}), erc.EXEC_MODE_KUBECTL)

    def test_params_then_cli_override(self):
        self.assertEqual(
            erc.resolve_exec_mode({"exec_mode": "docker_local"}),
            erc.EXEC_MODE_DOCKER_LOCAL,
        )
        self.assertEqual(
            erc.resolve_exec_mode(
                {"exec_mode": "docker_local"}, cli_exec_mode="kubectl"
            ),
            erc.EXEC_MODE_KUBECTL,
        )


class TestResolveRecordPath(unittest.TestCase):
    def test_params_override_skips_global_config(self):
        path = erc.resolve_record_path({"record_path": "C:/tmp/mesh_local/run1"})
        self.assertEqual(path, Path("C:/tmp/mesh_local/run1"))


class TestRunCollectorDockerLocal(unittest.TestCase):
    def test_uses_seeded_pod_names_and_record_path(self):
        import tempfile

        calls = []

        def runner(cmd):
            calls.append(cmd)
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-fe\n", stderr="")
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.run_collector(
                {
                    "poll_interval_seconds": 1,
                    "exec_mode": "docker_local",
                    "max_workers": 2,
                    "services": ["frontend"],
                    "pod_names": {"frontend": "frontend-1"},
                    "record_path": str(record_path),
                },
                record_path,
                run_cmd=runner,
                max_polls=1,
            )
            self.assertTrue((record_path / "service_inbound.csv").exists())
        self.assertTrue(all(c[0] != "kubectl" for c in calls))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestResolveExecMode TestResolveRecordPath TestRunCollectorDockerLocal`

Expected: FAIL — `resolve_exec_mode` missing.

- [ ] **Step 3: Implement params / main wiring**

Add next to `load_record_path`:

```python
def resolve_exec_mode(params: dict, cli_exec_mode: Optional[str] = None) -> str:
    if cli_exec_mode:
        return cli_exec_mode
    mode = params.get("exec_mode") or EXEC_MODE_KUBECTL
    if mode not in (EXEC_MODE_KUBECTL, EXEC_MODE_DOCKER_LOCAL):
        return EXEC_MODE_KUBECTL
    return mode


def resolve_record_path(
    params: dict, global_config_path: str = GLOBAL_CONFIG_PATH
) -> Path:
    override = params.get("record_path")
    if override:
        return Path(override)
    return load_record_path(global_config_path)
```

Replace `run_collector` with:

```python
def run_collector(
    params: dict,
    record_path: Path,
    run_cmd: Optional[CommandRunner] = None,
    max_polls: Optional[int] = None,
) -> None:
    """
    Main loop. Sleeps poll_interval_seconds between scrapes until SIGTERM
    or max_polls (used by tests).
    """
    services = resolve_services(params)
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    exec_mode = resolve_exec_mode(params)
    pod_names = dict(params.get("pod_names") or {})
    max_workers = int(params.get("max_workers", DEFAULT_MAX_WORKERS))
    pod_cache: Dict[str, str] = dict(pod_names) if exec_mode == EXEC_MODE_KUBECTL else {}
    container_cache: Dict[str, str] = {}
    tier2_warn_state: Dict[str, int] = {}

    log.info(
        "%s  START  poll_interval=%ss services=%d exec_mode=%s max_workers=%s",
        utc_now(), interval, len(services), exec_mode, max_workers,
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
            pod_cache=pod_cache,
            exec_mode=exec_mode,
            container_cache=container_cache,
            pod_names=pod_names,
            max_workers=max_workers,
            poll_index=polls,
            tier2_warn_state=tier2_warn_state,
        )
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break

    log.info("%s  EXIT", utc_now())
```

Replace `main()` with:

```python
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Envoy sidecar outbound retry-stats collector."
    )
    parser.add_argument(
        "--params",
        required=True,
        help="Path to collector params JSON "
        "(poll_interval_seconds, optional services list, optional exec_mode)",
    )
    parser.add_argument(
        "--exec-mode",
        choices=[EXEC_MODE_KUBECTL, EXEC_MODE_DOCKER_LOCAL],
        default=None,
        help="Transport used to reach istio-proxy (default: params or kubectl)",
    )
    args = parser.parse_args()

    params = load_params(args.params)
    if args.exec_mode:
        params["exec_mode"] = args.exec_mode
    record_path = resolve_record_path(params)
    record_path.mkdir(parents=True, exist_ok=True)
    setup_logging(record_path)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    run_collector(params, record_path)
```

Update the module docstring Usage line to mention both hosts / `--exec-mode docker_local`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_envoy_retry_collector.py`

Expected: `OK`.

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "Add --exec-mode and worker record_path for mesh collector"
```

---

### Task 6: Seed discovery and start the collector on the worker

**Files:**
- Modify: `experiments/run_scenario.py` (`WORKER_MESH_ROOT`, `mesh_exec_mode`, `discover_service_pod_map`, `start_mesh_collector_on_worker`, dispatch from `start_envoy_retry_collector`)
- Test: `experiments/test_run_scenario.py`

**Interfaces:**
- Consumes: existing `ssh`, `deploy_repo_script`, `write_remote_json`, `write_remote_script`, `ensure_envoy_stats_enabled`, `ALL_BOUTIQUE_SERVICES`.
- Produces:
  - `WORKER_MESH_ROOT = "/home/idozacharia/experiments/mesh_local"`
  - `mesh_exec_mode(cfg: dict) -> str` — `cfg["envoy_retry_collector"].get("exec_mode", "kubectl")`
  - `discover_service_pod_map(cfg: dict, services: list) -> dict` — one `kubectl get pods -n default -l app=<svc> -o jsonpath={.items[0].metadata.name}` per service **on master**
  - `start_mesh_collector_on_worker(cfg: dict) -> None`
  - `start_envoy_retry_collector` calls `start_mesh_collector_on_worker` when `mesh_exec_mode(cfg) == "docker_local"`; otherwise today's master path (existing `TestEnvoyRetryCollectorWiring` stays valid)

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_run_scenario.py`:

```python
class TestMeshCollectorWorkerWiring(unittest.TestCase):
    def _cfg(self, enabled=True, exec_mode="docker_local"):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "worker_ssh_host": "topfull-worker-1",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "envoy_retry_collector_script":
                    "/home/idozacharia/experiments/envoy_retry_collector.py",
            },
            "envoy_retry_collector": {
                "enabled": enabled,
                "poll_interval_seconds": 1,
                "exec_mode": exec_mode,
                "max_workers": 4,
            },
            "log_folder": "baseline_topfull_no_retryguard_sustained_overload_run99",
        }

    def test_mesh_exec_mode_defaults_to_kubectl(self):
        self.assertEqual(
            run_scenario.mesh_exec_mode({"envoy_retry_collector": {}}),
            "kubectl",
        )
        self.assertEqual(
            run_scenario.mesh_exec_mode(self._cfg(exec_mode="docker_local")),
            "docker_local",
        )

    @mock.patch("run_scenario.ssh")
    def test_discover_service_pod_map_uses_master_kubectl(self, mock_ssh):
        mock_ssh.side_effect = [
            SimpleNamespace(returncode=0, stdout="frontend-abc\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="checkout-def\n", stderr=""),
        ]
        cfg = self._cfg()
        got = run_scenario.discover_service_pod_map(
            cfg, ["frontend", "checkoutservice"]
        )
        self.assertEqual(
            got, {"frontend": "frontend-abc", "checkoutservice": "checkout-def"}
        )
        self.assertEqual(mock_ssh.call_count, 2)
        self.assertEqual(mock_ssh.call_args_list[0].args[0], "topfull-master")
        self.assertIn("app=frontend", mock_ssh.call_args_list[0].args[1])
        self.assertIn("jsonpath={.items[0].metadata.name}", mock_ssh.call_args_list[0].args[1])

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ensure_envoy_stats_enabled")
    @mock.patch("run_scenario.discover_service_pod_map")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_worker_uploads_seed_and_launches_meshlocal(
        self,
        mock_deploy,
        mock_ssh,
        mock_seed,
        mock_ensure,
        mock_write_json,
        mock_write_script,
        mock_wait,
    ):
        mock_seed.return_value = {"frontend": "frontend-abc"}
        cfg = self._cfg()
        cfg["envoy_retry_collector"]["services"] = ["frontend"]
        run_scenario.start_envoy_retry_collector(cfg)

        mock_deploy.assert_called_once_with(
            "topfull-worker-1",
            "envoy_retry_collector.py",
            "/home/idozacharia/experiments/envoy_retry_collector.py",
        )
        mock_ensure.assert_called_once_with(cfg, ["frontend"])
        json_host, json_path, params = mock_write_json.call_args[0][:3]
        self.assertEqual(json_host, "topfull-worker-1")
        self.assertEqual(json_path, "/tmp/envoy_retry_params.json")
        self.assertEqual(params["exec_mode"], "docker_local")
        self.assertEqual(params["max_workers"], 4)
        self.assertEqual(params["pod_names"], {"frontend": "frontend-abc"})
        self.assertEqual(
            params["record_path"],
            "/home/idozacharia/experiments/mesh_local/"
            "baseline_topfull_no_retryguard_sustained_overload_run99",
        )
        script_host, script_path, script_body = mock_write_script.call_args[0][:3]
        self.assertEqual(script_host, "topfull-worker-1")
        self.assertEqual(script_path, "/tmp/rg_mesh_local.sh")
        self.assertIn("python3", script_body)
        self.assertIn("--exec-mode docker_local", script_body)
        self.assertNotIn("source /home/idozacharia/TopFull/venv", script_body)
        tmux_calls = [
            c for c in mock_ssh.call_args_list
            if len(c.args) > 1 and "tmux new-session" in c.args[1] and "meshlocal" in c.args[1]
        ]
        self.assertEqual(len(tmux_calls), 1)
        self.assertEqual(tmux_calls[0].args[0], "topfull-worker-1")

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_still_uses_master_when_kubectl_mode(
        self, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(exec_mode="kubectl")
        run_scenario.start_envoy_retry_collector(cfg)
        mock_deploy.assert_called_once_with(
            "topfull-master",
            "envoy_retry_collector.py",
            "/home/idozacharia/experiments/envoy_retry_collector.py",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_run_scenario.py TestMeshCollectorWorkerWiring`

Expected: FAIL — `mesh_exec_mode` missing.

- [ ] **Step 3: Implement seed + worker start**

In `experiments/run_scenario.py`, immediately after `ALL_BOUTIQUE_SERVICES`, add:

```python
WORKER_MESH_ROOT = "/home/idozacharia/experiments/mesh_local"
MANIFEST_EXEC_MODE_DOCKER = "worker_local_docker_exec"


def mesh_exec_mode(cfg: dict) -> str:
    return cfg.get("envoy_retry_collector", {}).get("exec_mode", "kubectl")
```

Add these functions immediately before `start_envoy_retry_collector`:

```python
def discover_service_pod_map(cfg: dict, services: list) -> dict:
    """
    One-time seed: service → pod name via kubectl on master.
    Matches envoy_retry_collector.discover_pod_name's selector exactly.
    """
    master = cfg["infra"]["master_ssh_host"]
    out = {}
    for svc in services:
        r = ssh(
            master,
            f"kubectl get pods -n default -l app={svc} "
            f"-o jsonpath={{.items[0].metadata.name}}",
            check=False,
        )
        name = (r.stdout or "").strip()
        if name:
            out[svc] = name
        else:
            print(f"[WARN] No pod for app={svc} during mesh seed "
                  f"(stderr={(r.stderr or '').strip()})")
    return out


def start_mesh_collector_on_worker(cfg: dict):
    """
    Deploy envoy_retry_collector.py to topfull-worker-1 and start it
    with --exec-mode docker_local. Stats-inclusion patch stays on master.
    """
    erc_cfg = cfg.get("envoy_retry_collector", {})
    worker = cfg["infra"]["worker_ssh_host"]
    master_script = cfg["infra"].get(
        "envoy_retry_collector_script",
        "/home/idozacharia/experiments/envoy_retry_collector.py",
    )
    script = master_script
    log_folder = cfg["log_folder"]
    record_path = f"{WORKER_MESH_ROOT}/{log_folder}"
    services = list(erc_cfg.get("services", ALL_BOUTIQUE_SERVICES))

    ssh(worker, f"mkdir -p /home/idozacharia/experiments {record_path}", check=False)
    deploy_repo_script(worker, "envoy_retry_collector.py", script)
    ensure_envoy_stats_enabled(cfg, services)

    pod_names = discover_service_pod_map(cfg, services)
    step(f"Seeded service→pod map for {len(pod_names)}/{len(services)} services")

    params = {
        "poll_interval_seconds": int(erc_cfg.get("poll_interval_seconds", 5)),
        "exec_mode": "docker_local",
        "max_workers": int(erc_cfg.get("max_workers", 4)),
        "pod_names": pod_names,
        "record_path": record_path,
    }
    if "services" in erc_cfg:
        params["services"] = erc_cfg["services"]

    write_remote_json(worker, "/tmp/envoy_retry_params.json", params)
    start_script = (
        "#!/bin/bash\n"
        f"mkdir -p {record_path}\n"
        f"python3 {script} --params /tmp/envoy_retry_params.json "
        f"--exec-mode docker_local\n"
    )
    write_remote_script(worker, "/tmp/rg_mesh_local.sh", start_script)
    ssh(worker, "tmux new-session -d -s meshlocal /tmp/rg_mesh_local.sh")
    step(f"Started: Envoy mesh collector on {worker} "
         f"(tmux session: meshlocal, script: {script})")
    wait_with_progress(3, "Worker mesh collector init")
```

At the top of `start_envoy_retry_collector`, after the `enabled` early-return, add:

```python
    if mesh_exec_mode(cfg) == "docker_local":
        banner("Starting Envoy mesh collector (worker-local docker exec)")
        start_mesh_collector_on_worker(cfg)
        return
```

Leave the rest of `start_envoy_retry_collector` (master kubectl path) unchanged.

In `run()`'s banner block, after the existing Envoy poll_interval print, add:

```python
        print(f"    exec_mode      : "
              f"{cfg['envoy_retry_collector'].get('exec_mode', 'kubectl')}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_run_scenario.py`

Expected: `OK` (existing `TestEnvoyRetryCollectorWiring` still hits the master path because those fixtures omit `exec_mode`).

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "Start mesh collector on worker with a one-time pod seed"
```

---

### Task 7: Worker stop, two-hop `scp`, and manifest

**Files:**
- Modify: `experiments/run_scenario.py` (`scp_from`, `stop_worker_mesh_collector`, `pull_worker_mesh_csvs`, `envoy_collector_manifest`, `collect_results`, `run()` finally)
- Test: `experiments/test_run_scenario.py`

**Interfaces:**
- Consumes: `WORKER_MESH_ROOT`, `mesh_exec_mode`, `MANIFEST_EXEC_MODE_DOCKER` from Task 6.
- Produces:
  - `scp_from(host: str, remote_path: str, local_path: str, recursive: bool = False) -> None`
  - `stop_worker_mesh_collector(cfg: dict) -> None` — `pkill -f '[e]nvoy_retry_collector.py'; tmux kill-session -t meshlocal` on `worker_ssh_host` when that key exists
  - `pull_worker_mesh_csvs(cfg: dict, dest: str) -> None` — worker → local temp → `scp_to` each of `service_edges.csv`, `service_inbound.csv`, `envoy_retry_collector.log` onto master `{dest}/`
  - `envoy_collector_manifest(cfg: dict) -> dict`
  - `collect_results` calls `pull_worker_mesh_csvs` when `mesh_exec_mode == docker_local`; manifest records `exec_mode: worker_local_docker_exec` and `exec_host`
  - `run()` `finally` calls `stop_worker_mesh_collector(cfg)` after `stop_master_stack` and before `collect_results`

- [ ] **Step 1: Write the failing tests**

Append to `TestMeshCollectorWorkerWiring` in `experiments/test_run_scenario.py`:

```python
    @mock.patch("run_scenario.ssh")
    def test_stop_worker_pkills_on_worker_host(self, mock_ssh):
        run_scenario.stop_worker_mesh_collector(self._cfg())
        self.assertEqual(mock_ssh.call_args[0][0], "topfull-worker-1")
        cmd = mock_ssh.call_args[0][1]
        self.assertIn("[e]nvoy_retry_collector.py", cmd)
        self.assertIn("meshlocal", cmd)

    @mock.patch("run_scenario.ssh")
    def test_stop_worker_noop_without_worker_host(self, mock_ssh):
        run_scenario.stop_worker_mesh_collector(
            {"infra": {"master_ssh_host": "topfull-master"}}
        )
        mock_ssh.assert_not_called()

    @mock.patch("run_scenario.scp_to")
    @mock.patch("run_scenario.scp_from")
    def test_pull_worker_mesh_csvs_two_hop(self, mock_scp_from, mock_scp_to):
        def fake_scp_from(host, remote, local, recursive=False):
            self.assertEqual(host, "topfull-worker-1")
            self.assertTrue(remote.endswith(
                "/mesh_local/baseline_topfull_no_retryguard_sustained_overload_run99/"
            ))
            self.assertTrue(recursive)
            Path(local, "service_edges.csv").write_text("timestamp,caller\n", encoding="utf-8")
            Path(local, "service_inbound.csv").write_text("timestamp,service\n", encoding="utf-8")
            Path(local, "envoy_retry_collector.log").write_text("START\n", encoding="utf-8")

        mock_scp_from.side_effect = fake_scp_from
        cfg = self._cfg()
        run_scenario.pull_worker_mesh_csvs(
            cfg, "/home/idozacharia/experiments/results/test_run"
        )
        names = sorted(Path(c.args[0]).name for c in mock_scp_to.call_args_list)
        self.assertEqual(
            names,
            [
                "envoy_retry_collector.log",
                "service_edges.csv",
                "service_inbound.csv",
            ],
        )
        self.assertTrue(all(c.args[1] == "topfull-master" for c in mock_scp_to.call_args_list))

    @mock.patch("run_scenario.pull_worker_mesh_csvs")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_collect_results_pulls_when_docker_local(
        self, mock_ssh, mock_write_json, mock_pull
    ):
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        cfg = {
            "infra": {
                "master_ssh_host": "topfull-master",
                "worker_ssh_host": "topfull-worker-1",
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
                "exec_mode": "docker_local",
                "poll_interval_seconds": 1,
                "max_workers": 4,
            },
        }
        run_scenario.collect_results(cfg)
        mock_pull.assert_called_once()
        self.assertEqual(
            mock_pull.call_args[0][1],
            "/home/idozacharia/experiments/results/test_run",
        )
        manifest = [
            c.args[2]
            for c in mock_write_json.call_args_list
            if c.args[1].endswith("run_manifest.json")
        ][0]
        erc = manifest["envoy_retry_collector"]
        self.assertEqual(erc["exec_mode"], run_scenario.MANIFEST_EXEC_MODE_DOCKER)
        self.assertEqual(erc["exec_host"], "topfull-worker-1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_run_scenario.py TestMeshCollectorWorkerWiring`

Expected: FAIL — `stop_worker_mesh_collector` / `scp_from` missing.

- [ ] **Step 3: Implement `scp_from`, stop, two-hop pull, manifest**

Next to `scp_to` in `experiments/run_scenario.py`:

```python
def scp_from(host: str, remote_path: str, local_path: str, recursive: bool = False):
    """Copy a remote file or directory to the local machine."""
    cmd = ["scp", "-o", "BatchMode=yes", "-o", "ControlMaster=no"]
    if recursive:
        cmd.append("-r")
    cmd.extend([f"{host}:{remote_path}", local_path])
    subprocess.run(cmd, check=True)
```

After `stop_master_stack`:

```python
def stop_worker_mesh_collector(cfg: dict):
    worker = cfg.get("infra", {}).get("worker_ssh_host")
    if not worker:
        return
    step(f"Stopping worker mesh collector on {worker}...")
    ssh(
        worker,
        "pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; "
        "tmux kill-session -t meshlocal 2>/dev/null; "
        "true",
        check=False,
    )
```

Do **not** `tmux kill-server` on the worker (an operator may have another session). `pkill` plus `kill-session -t meshlocal` is the stop.

Add:

```python
def envoy_collector_manifest(cfg: dict) -> dict:
    raw = dict(cfg.get("envoy_retry_collector") or {})
    mode = mesh_exec_mode(cfg)
    if mode == "docker_local":
        raw["exec_mode"] = MANIFEST_EXEC_MODE_DOCKER
        raw["exec_host"] = cfg.get("infra", {}).get("worker_ssh_host", "topfull-worker-1")
    else:
        raw["exec_mode"] = "kubectl"
        raw["exec_host"] = cfg.get("infra", {}).get("master_ssh_host", "topfull-master")
    return raw


def pull_worker_mesh_csvs(cfg: dict, dest: str) -> None:
    """Two-hop pull: worker disk → orchestrator temp → master dest."""
    worker = cfg["infra"]["worker_ssh_host"]
    master = cfg["infra"]["master_ssh_host"]
    log_folder = cfg["log_folder"]
    remote_dir = f"{WORKER_MESH_ROOT}/{log_folder}/"
    names = ("service_edges.csv", "service_inbound.csv", "envoy_retry_collector.log")
    with tempfile.TemporaryDirectory() as td:
        try:
            scp_from(worker, remote_dir, td, recursive=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Could not pull worker mesh CSVs from {worker}:{remote_dir}: {exc}")
            return
        for name in names:
            local = os.path.join(td, name)
            if not os.path.isfile(local):
                nested = os.path.join(td, log_folder, name)
                if os.path.isfile(nested):
                    local = nested
            if not os.path.isfile(local):
                print(f"[WARN] worker mesh file missing after scp: {name}")
                continue
            scp_to(local, master, f"{dest}/{name}")
            step(f"Copied {name} from {worker} -> {master}:{dest}/")
```

In `collect_results`, after `ssh(master, f"cp -r {src}/logs/. {dest}/ 2>/dev/null; true", check=False)` add:

```python
    if mesh_exec_mode(cfg) == "docker_local" and cfg.get("envoy_retry_collector", {}).get("enabled", False):
        pull_worker_mesh_csvs(cfg, dest)
```

Replace the manifest's `"envoy_retry_collector": cfg.get("envoy_retry_collector", {}),` line with:

```python
        "envoy_retry_collector": envoy_collector_manifest(cfg),
```

In `run()` `finally`, after `stop_master_stack(cfg)` and before `collect_results(...)`:

```python
        stop_worker_mesh_collector(cfg)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_run_scenario.py`

Expected: `OK`. Existing `test_collect_results_writes_service_capacity_json` still passes (no `exec_mode`, so no pull).

- [ ] **Step 5: Commit (only if the user has asked to commit)**

```
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "Pull worker mesh CSVs to master at teardown"
```

---

### Task 8: Scenario YAMLs and docs

**Files:**
- Modify: all 16 files under `experiments/configs/scenario_*.yaml`
- Modify: `AGENTS.md` (§4 collector-host note, §6 `/tmp` cleanup)
- Modify: `Guides and Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md` (Status)
- Modify: `Guides and Info/METRICS-GATHERED.md` (Layer 1 writer location)
- Modify: `Guides and Info/METRICS-COLLECTION-GUIDE.md` (table + folder note)
- Modify: `experiments/README.md` (schema rows)
- Do **not** edit `docs/superpowers/specs/2026-09-12-mesh-collector-worker-local-exec-design.md`
- Do **not** bump `run_number` / `log_folder`

**Interfaces:** YAML keys locked here:

```yaml
envoy_retry_collector:
  enabled: true
  poll_interval_seconds: 1
  exec_mode: docker_local
  max_workers: 4

infra:
  worker_ssh_host: topfull-worker-1
```

- [ ] **Step 1: Update all 16 scenario YAMLs**

Files:

- `experiments/configs/scenario_1_baseline.yaml`
- `experiments/configs/scenario_1_retryguard.yaml`
- `experiments/configs/scenario_2_baseline.yaml`
- `experiments/configs/scenario_2_retryguard.yaml`
- `experiments/configs/scenario_3_baseline.yaml`
- `experiments/configs/scenario_3_retryguard.yaml`
- `experiments/configs/scenario_4a_baseline.yaml`
- `experiments/configs/scenario_4a_retryguard.yaml`
- `experiments/configs/scenario_4b_baseline.yaml`
- `experiments/configs/scenario_4b_retryguard.yaml`
- `experiments/configs/scenario_5_interval_10s.yaml`
- `experiments/configs/scenario_5_interval_20s.yaml`
- `experiments/configs/scenario_5_interval_30s.yaml`
- `experiments/configs/scenario_5_interval_60s.yaml`
- `experiments/configs/scenario_6_recovery_baseline.yaml`
- `experiments/configs/scenario_6_recovery_retryguard.yaml`

In each file:

1. Under `envoy_retry_collector:`, add `exec_mode: docker_local` and `max_workers: 4` (keep existing `enabled` / `poll_interval_seconds`).
2. Under `infra:`, add `worker_ssh_host: topfull-worker-1` immediately after `loadgen_ssh_host`.

Do not change S6 `run_number` (still the overwrite-risk slot). Do not enable a second master-side collector.

- [ ] **Step 2: Docs**

`experiments/README.md` schema table — add these rows next to the existing `envoy_retry_collector.*` / `infra.*` rows:

```
| `envoy_retry_collector.exec_mode` | string | `kubectl` (master, sequential) or `docker_local` (worker, docker exec). YAMLs default to `docker_local` |
| `envoy_retry_collector.max_workers` | int | Thread-pool size for docker_local exec+parse (default 4) |
| `infra.worker_ssh_host` | string | SSH alias for the Boutique worker (`topfull-worker-1`) |
```

Change the `infra.envoy_retry_collector_script` row to say the same path is used on master (`kubectl` mode) and on the worker (`docker_local` mode).

`AGENTS.md` §6 cleanup command — add a worker-side line after the existing master `sudo rm -f /tmp/rg_*.sh` command:

```
ssh topfull-worker-1 "sudo rm -f /tmp/rg_mesh_local.sh /tmp/envoy_retry_params.json"
```

`AGENTS.md` §4 (full-mesh Envoy collector bullet) — add: the scrape loop now runs on `topfull-worker-1` via `docker exec` when `exec_mode: docker_local`; CSVs are two-hop copied onto master at teardown. `campaign_48/` / `august_38/` are unchanged. RetryGuard's live `measure_value()` read of master's `service_inbound.csv` is dark for the duration of a `docker_local` run (accepted v1; periodic pull is a follow-up).

`Guides and Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md` Status — append a subsection:

```markdown
**Worker-local exec (2026-09-12).** When `envoy_retry_collector.exec_mode`
is `docker_local`, `experiments/envoy_retry_collector.py` runs on
`topfull-worker-1` and scrapes each sidecar with `docker exec` (cri-dockerd),
not `kubectl exec` from master. Parsers and CSV schemas are unchanged.
`run_scenario.py` seeds `service → pod_name` once via kubectl on master,
starts tmux session `meshlocal` on the worker, and at teardown two-hop
`scp`s `service_edges.csv` / `service_inbound.csv` /
`envoy_retry_collector.log` onto master's `results_base_path/<log_folder>/`.
Tier-2 pod recreation is an accepted v1 gap (rate-limited warning, no
re-seed). Do not treat this as a campaign-data change —
`campaign_48/` / `august_38/` still have whatever they had.
```

`Guides and Info/METRICS-GATHERED.md` Layer 1 **Writer:** sentence — change to:

```
**Writer:** `experiments/envoy_retry_collector.py`. With
`exec_mode: docker_local` (current YAML default) the process runs on
`topfull-worker-1` (`docker exec`); `run_scenario.py` copies the two CSVs
plus `envoy_retry_collector.log` onto master at teardown. `exec_mode:
kubectl` is the old master-side sequential `kubectl exec` path.
```

`Guides and Info/METRICS-COLLECTION-GUIDE.md` §1 table row for full-mesh Envoy — add "(process on `topfull-worker-1` when `exec_mode: docker_local`; files land in the master results folder at teardown)".

Do **not** claim `campaign_48/` has worker-local files. Do **not** edit the spec. Do **not** edit `mentor_charts.py`.

- [ ] **Step 3: Commit (only if the user has asked to commit)**

```
git add experiments/configs AGENTS.md "Guides and Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md" "Guides and Info/METRICS-GATHERED.md" "Guides and Info/METRICS-COLLECTION-GUIDE.md" experiments/README.md
git commit -m "Enable worker-local mesh collector in scenario configs and docs"
```

---

### Task 9: Live validation on the worker (no campaign run)

**Files:** none unless a live command shape forces a builder fix (then fix Task 2, re-run `python experiments/test_envoy_retry_collector.py`, and only then re-attempt this task).

**Interfaces:** none. Do **not** launch `run_scenario.py`. S6 YAMLs still point at a completed slot. This smoke writes only under `/tmp/mesh_local_smoke/` on `topfull-worker-1`.

If Task 1 found the VMs down, run Task 1 first; if they are still down, leave these checkboxes unchecked.

- [ ] **Step 1: Confirm cluster + worker Docker still match Task 1**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "whoami; docker ps --filter label=io.kubernetes.container.name=istio-proxy --format '{{.ID}} {{.Labels}}' | head -n 5"
```

Expected: nodes `Ready`; Boutique pods `Running` 2/2; `whoami` is `idozacharia`; at least one `istio-proxy` row. If SSH times out, stop — do not mark this task passed against a down cluster.

- [ ] **Step 2: Seed two pod names from master (same selector as `discover_service_pod_map`)**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get pods -n default -l app=frontend -o jsonpath='{.items[0].metadata.name}'; echo; kubectl get pods -n default -l app=checkoutservice -o jsonpath='{.items[0].metadata.name}'; echo"
```

Expected: two pod names. Put them into the params JSON in Step 4.

- [ ] **Step 3: Copy the collector to the worker**

```powershell
scp -o BatchMode=yes -o ControlMaster=no experiments/envoy_retry_collector.py topfull-worker-1:/tmp/envoy_retry_collector_smoke.py
```

Expected: exit 0.

- [ ] **Step 4: Write params and run 8 seconds on the worker**

Replace `FRONTEND_POD` and `CHECKOUT_POD` with the names from Step 2:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "mkdir -p /tmp/mesh_local_smoke; printf '%s\n' '{\"poll_interval_seconds\": 1, \"exec_mode\": \"docker_local\", \"max_workers\": 2, \"services\": [\"frontend\", \"checkoutservice\"], \"pod_names\": {\"frontend\": \"FRONTEND_POD\", \"checkoutservice\": \"CHECKOUT_POD\"}, \"record_path\": \"/tmp/mesh_local_smoke\"}' > /tmp/envoy_retry_smoke_params.json; timeout 8 python3 /tmp/envoy_retry_collector_smoke.py --params /tmp/envoy_retry_smoke_params.json --exec-mode docker_local; true"
```

Expected: `timeout` exits 124 (or 0 because of `true`); log lines contain `START` and `exec_mode=docker_local`; no Python traceback. If `docker` is missing from PATH inside this non-interactive ssh, that is a real bug — fix the worker PATH or the command builder, do not silently fall back to kubectl.

- [ ] **Step 5: Diff CSV schemas against a `campaign_48/` file (structure only)**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "python3 -c \"import csv; from pathlib import Path; p=Path('/tmp/mesh_local_smoke/service_edges.csv'); q=Path('/tmp/mesh_local_smoke/service_inbound.csv'); e=list(csv.DictReader(p.open())); i=list(csv.DictReader(q.open())); print('edges', list(e[0].keys()) if e else None, 'rows', len(e)); print('inbound', list(i[0].keys()) if i else None, 'rows', len(i)); assert list(e[0].keys())==['timestamp','caller','target','total','2xx','4xx','5xx','retry']; assert list(i[0].keys())==['timestamp','service','total','2xx','4xx','5xx']; print('SCHEMA_OK')\""
```

On the Windows checkout, confirm the same header exists in any `campaign_48/` run that has the files (many campaign folders do **not** — that is expected). If no campaign folder has them, assert against the constants in `experiments/envoy_retry_collector.py` (`EDGES_CSV_COLUMNS` / `INBOUND_CSV_COLUMNS`) instead. Values will differ; structure must not.

Expected: `SCHEMA_OK`.

- [ ] **Step 6: Confirm no kubectl on the worker during the smoke**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "grep -E 'kubectl|WARNING  tier2' /tmp/mesh_local_smoke/envoy_retry_collector.log || echo NO_KUBECTL_IN_LOG"
```

Expected: `NO_KUBECTL_IN_LOG` (or only `WARNING  tier2` if a pod was missing — that is a seed error, re-run Step 2). The log must not show `kubectl get` / `kubectl exec`.

- [ ] **Step 7: Confirm campaign folders on master were not touched**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ls /home/idozacharia/experiments/results/ | grep mesh_local_smoke || echo NONE_IN_RESULTS_ROOT"
```

Expected: `NONE_IN_RESULTS_ROOT`.

- [ ] **Step 8: Clean up smoke artifacts**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "rm -rf /tmp/mesh_local_smoke /tmp/envoy_retry_collector_smoke.py /tmp/envoy_retry_smoke_params.json"
```

Expected: exit 0.

- [ ] **Step 9: No commit needed**

This task only touches `/tmp` on the worker. If Step 4 required a command-builder fix, that commit already happened on the collector file.

---

## Self-review (spec coverage)

| Spec section | Task |
|---|---|
| §7 / §3.1 CRI = docker via cri-dockerd; crictl only if Docker unusable | Task 1 (verify) + Task 2 (builders) |
| §3.2 two-tier discovery (orchestrator kubectl seed, worker `docker ps` labels) | Task 2 + Task 3 + Task 6 |
| §3.3 `docker exec … curl localhost:15000/stats`; same timeout shape | Task 2 |
| §3.4 worker local dir + teardown two-hop scp; no shared FS; no worker→master SSH | Task 5 (`record_path`) + Task 7 |
| §3.5 thread pool 3–4; serial CSV writes on main thread | Task 4 |
| §3.6 Tier 1 recover next poll; Tier 2 warn + continue (accepted gap) | Task 3 |
| §3.7 `infra.worker_ssh_host`, start/stop on worker, stats patch stays on master, manifest exec_mode | Task 6 + Task 7 + Task 8 |
| §4 byte-identical parsers/CSV schemas; RetryGuard/charts need zero consumer changes | Global Constraints; no parser edits in any task |
| §5 unit tests: docker ps/exec builders, Tier 1/2, serial writes, seed params, runner ssh/scp shapes; no real SSH/Docker | Tasks 2–7 |
| §6 success criteria (schema, Tier 1/2, tests) | Tasks 3, 4, 9 |
| §8 fork-vs-flag | Architecture: `--exec-mode {kubectl,docker_local}` on the existing file |
| Out of scope: throttle/resource collectors, shared FS, YAML-in-the-spec, campaign backfill, charts | Global Constraints + Task 8 / Task 9 |

**Placeholder scan:** no TBD/TODO/"similar to Task N". Every code step has the full snippet.

**Signature consistency:**

- Collector: `EXEC_MODE_KUBECTL` / `EXEC_MODE_DOCKER_LOCAL`, `docker_ps_container_id_cmd`, `docker_exec_stats_cmd`, `discover_container_id`, `fetch_stats_text_docker`, `ServiceScrapeResult`, `scrape_one_service`, `should_log_tier2`, `poll_once(..., exec_mode, container_cache, pod_names, max_workers, poll_index, tier2_warn_state)`, `resolve_exec_mode`, `resolve_record_path`.
- Runner: `WORKER_MESH_ROOT`, `MANIFEST_EXEC_MODE_DOCKER`, `mesh_exec_mode`, `discover_service_pod_map`, `start_mesh_collector_on_worker`, `stop_worker_mesh_collector`, `scp_from`, `pull_worker_mesh_csvs`, `envoy_collector_manifest`.
- YAML/CLI: `exec_mode: docker_local`. Manifest analysis field: `worker_local_docker_exec`.

**Accepted gaps left unplanned on purpose (per spec):** periodic mid-run pull (RetryGuard live `measure_value()` stays dark under `docker_local`); Tier-2 self-heal; `crictl` unless Task 1 forces it; moving other collectors; chart wiring; a full `run_scenario.py` campaign run (Task 9 is a scratch-dir smoke only).
