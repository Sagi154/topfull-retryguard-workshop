# Mesh collector: worker-local exec instead of master `kubectl exec`

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Design (spec only, no implementation) for moving the full-mesh Envoy scrape loop off `topfull-master` and onto `topfull-worker-1`, so each poll's 11 sidecar scrapes go through the **local container runtime** (`cri-dockerd` via `docker exec` / `crictl exec`) instead of `kubectl exec` round-tripping through the kube-apiserver and kubelet. Extends [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md) (current implementation, sequential `kubectl exec` from master) and is motivated by the measured cost documented in [2026-09-11-slo-fail-and-mu-estimator-design.md](2026-09-11-slo-fail-and-mu-estimator-design.md) §8 (direct GET `/cart` P95 during S2 load: ~1.45 s with mesh+throttle collectors off vs ~1.84 s with them on at 1 s poll interval). CSV schemas, parsers, and every downstream consumer (RetryGuard's `measure_value()` — [2026-09-10-retryguard-mesh-measure-value-design.md](2026-09-10-retryguard-mesh-measure-value-design.md) — and `mentor_charts.py` if/when wired) are unchanged.

---

## 1. Purpose and scope

**Problem.** `experiments/envoy_retry_collector.py` (current implementation, see [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md)) runs in a tmux session on `topfull-master` and, every poll (`poll_interval_seconds`, often **1 s** per scenario YAML), sequentially does, for each of 11 Boutique services:

```
kubectl get pods -n default -l app=<service> -o jsonpath=...   # pod discovery (cached after first success)
kubectl exec <pod> -n default -c istio-proxy -- curl -s http://localhost:15000/stats
```

Both hops go **master → kube-apiserver → kubelet on `topfull-worker-1` → attach into the pod's network namespace → curl its loopback admin port** (Istio does not bind Envoy admin on `0.0.0.0`, so this attach-and-curl is the only way in). 11 sequential exec round-trips through the API server every second is not free: it adds control-plane and worker-node load *during the exact experiment* being measured, and the 2026-09-11 latency-split check found the direct (no-goproxy) GET `/cart` path measurably slower with the mesh+throttle collectors on than off at 1 s poll. This spec proposes running the scrape loop **locally on `topfull-worker-1`**, using the local CRI runtime directly, bypassing the API server and kubelet for every poll.

**In scope**

- CRI choice for the local exec (confirm `cri-dockerd` / `docker exec` vs `crictl exec`) and the exact discovery/exec command shapes.
- Pod discovery: what stays one-time-via-`kubectl`-from-master vs what moves to a per-poll local lookup.
- Bounded-concurrency local exec (thread pool, 3–4 workers) replacing the current sequential per-service loop, without breaking the existing serial, non-thread-safe CSV writers.
- Getting `service_edges.csv` / `service_inbound.csv` (now produced on the worker's local disk) into the same place `run_scenario.py` already expects them (master's flat `results_base_path/<log_folder>/`, then the operator's `scp` pull to a Windows checkout) — given SSH+tmux orchestration and no shared filesystem between the three VMs.
- Failure modes: pod restarts in place (same pod name, new container ID) vs pod recreation (new pod name); the collector must survive both without crashing, analogous to today's `pod_cache.pop(service, None)` retry-discovery.
- Deployment/lifecycle: `run_scenario.py` today deploys collector scripts and starts them in tmux **on master only**; this spec adds the equivalent second SSH target (`topfull-worker-1`) with matching start/stop lifecycle.
- Testing strategy consistent with `experiments/test_envoy_retry_collector.py` (injected `CommandRunner`, `SimpleNamespace` results, no real subprocess/SSH in unit tests).
- Byte-identical `/stats` text format, `OUTBOUND_RE`/`INBOUND_RE` parsers, and CSV schemas — this is an execution-path change, not a data-model change.

**Out of scope (explicit)**

- Changing `service_edges.csv` / `service_inbound.csv` column names, types, or semantics. RetryGuard's `measure_value()` and any future `mentor_charts.py` wiring must not need to change.
- Changing the Envoy stats-inclusion annotation patching (`ensure_envoy_stats_enabled` in `run_scenario.py` already runs against the API server once per run, at Deployment-patch time, not per poll — that stays as-is; it is a control-plane mutation, not a hot-path scrape).
- Moving `resource_usage_collector.py` or `topfull_throttle_collector.py` to the worker. `resource_usage_collector.py` already scrapes kubelet `stats/summary` (a single per-node HTTP call, not 11 sequential execs) and `topfull_throttle_collector.py` reads local files/HTTP on master itself — neither has the same per-poll fan-out cost as the mesh collector. Revisiting them is a separate, later spec if their own overhead is ever measured as significant.
- Setting up a shared filesystem (NFS/sshfs) between the VMs. Considered and rejected in §3.4.
- Actually writing or modifying any `.py` file, scenario YAML, or `run_scenario.py` code. This document specifies the change; implementation is a separate task.
- Re-litigating the worker-local-exec direction itself — already agreed with the user; this spec only works out *how*.
- Backfilling `campaign_48/` or `august_38/` with worker-local-collector output — as with every prior mesh-collector change, only future runs get it.

---

## 2. Current behavior (baseline for comparison)

From `experiments/envoy_retry_collector.py` (see full read in [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md)):

- `ALL_SERVICES` — hardcoded list of the 11 Boutique Deployments.
- `discover_pod_name(service, run_cmd)` — `kubectl get pods -n default -l app=<service> -o jsonpath='{.items[0].metadata.name}'`. Result is cached per-service in `pod_cache: Dict[str, str]` for the life of the process; only re-queried if a subsequent `fetch_stats_text` call for that pod fails (`pod_cache.pop(service, None)`).
- `fetch_stats_text(pod, run_cmd)` — `kubectl exec <pod> -n default -c istio-proxy -- curl -s http://localhost:15000/stats`, 15 s timeout (`KUBECTL_TIMEOUT_SECONDS`).
- `poll_once(record_path, services, timestamp, run_cmd, pod_cache)` — `for service in sorted(services):` — **strictly sequential**, one service fully resolved+fetched+parsed+written before the next starts. A per-service failure (discovery or fetch) logs a warning and `continue`s; it never raises out of `poll_once`.
- `parse_edges` / `parse_inbound` — pure regex parsers over the `/stats` text (`OUTBOUND_RE`, `INBOUND_RE`), independent of how the text was obtained.
- `write_edges_csv` / `write_inbound_csv` — open the CSV in append mode, write header if new/empty, write rows, close. Called once per service per poll, from the single poll-loop thread — no locking exists today because there is no concurrency today.
- Runs via `run_scenario.py::start_envoy_retry_collector`: `deploy_repo_script(master, "envoy_retry_collector.py", script)` copies the file to master over SCP, writes a JSON params file (`poll_interval_seconds`, optional `services` override) via `write_remote_json`, writes a bash launcher via `write_remote_script`, and starts it with `tmux new-session -d -s envoyretry /tmp/rg_envoy_retry.sh`. Teardown is `pkill -f '[e]nvoy_retry_collector.py'` inside `stop_master_stack` (SIGTERM, no special flush needed since every CSV write is already synchronous/flushed-on-close per row).
- Output lands directly in `record_path` (from `global_config.json`, itself under `/home/idozacharia/TopFull/.../src/logs/`), which is on the **same host** (`master`) as `results_base_path`, so `collect_results()`'s `cp -r {src}/logs/. {dest}/` picks it up with no network hop — because master both runs the collector and holds the results directory.

**Cost measured.** [2026-09-11-slo-fail-and-mu-estimator-design.md](2026-09-11-slo-fail-and-mu-estimator-design.md) §8: at `poll_interval_seconds: 1` for both mesh + throttle collectors, direct GET `/cart` under S2 load was ~1.84 s (collectors on) vs ~1.45 s (collectors off) — the collectors are a measurable, not negligible, contributor to load-path latency during the very experiment measuring load-path latency. (That same check found the *proxy-path* latency blowup and the Locust P95 SLO miss are **not** primarily caused by the collectors — see that spec's §8 read #5 — but the ~0.4 s direct-path delta is real and worth removing since it is pure overhead, not signal.)

---

## 3. Proposed design

### 3.1 CRI: use `cri-dockerd` (Docker), not raw `crictl`

Per [SETUP-GUIDE.md](../../../Guides%20and%20Info/SETUP-GUIDE.md) §2a/§2d, this cluster is `kubeadm`-bootstrapped with `--cri-socket=unix:///var/run/cri-dockerd.sock`, i.e. Kubernetes talks to Docker through the `cri-dockerd` shim, and `AGENTS.md` §7's "known fixes" list explicitly names `cri-docker` as a systemd service already running on all nodes. So on `topfull-worker-1`, containers are real Docker containers under `dockerd`, and the simplest, most direct local tool is **`docker exec`** against the Docker CLI/daemon that's already there — not `crictl`, which would need `--runtime-endpoint unix:///var/run/cri-dockerd.sock` wired up separately and is a thinner, less familiar CLI for ad hoc debugging. `crictl exec` is kept as a documented fallback in case `docker` CLI access for `idozacharia` turns out to be restricted (see open verification items, §7) — the underlying container is the same either way; only the CLI used to reach it differs.

Both cri-dockerd and containerd-based CRIs label containers with the standard Kubernetes container-runtime-interface labels, which is what pod→container-ID resolution below depends on:

- `io.kubernetes.pod.name`
- `io.kubernetes.pod.namespace`
- `io.kubernetes.container.name`

These are **not** the same thing as a Kubernetes Pod's own `app=<service>` label (that is Pod/Deployment metadata; cri-dockerd does not generally mirror arbitrary Pod labels onto the Docker container's labels) — this distinction drives the two-tier discovery design in §3.2.

### 3.2 Pod discovery: one-time-via-master, then local-only per poll

Today's `discover_pod_name` is already a cache-then-refresh-on-failure pattern; the question here is *where the cache is seeded* and *what "refresh" means* once the collector's home host no longer has convenient `kubectl` access to the API server.

**Chosen design — two tiers:**

1. **Seed (once, at collector start, via master — not per poll).** `run_scenario.py` (the Windows-side orchestrator) already talks to `topfull-master`, which has a working kubeconfig. Before starting the worker-local collector, the orchestrator runs, once, over SSH to master:

   ```
   kubectl get pods -n default -l 'app in (frontend,cartservice,...)' \
     -o jsonpath='{range .items[*]}{.metadata.labels.app}={.metadata.name}{"\n"}{end}'
   ```

   (or 11 individual `-l app=<service>` calls, matching today's `discover_pod_name` selector exactly, one per service — either is fine, this happens once per run, not once per poll). The resulting `service → pod_name` map is written as part of the collector's params JSON (alongside `poll_interval_seconds`) and pushed to `topfull-worker-1` via the same `write_remote_json` helper `run_scenario.py` already uses for master. This requires **no new kubeconfig on the worker** and **no new SSH trust between VMs** — it's the orchestrator doing one extra `kubectl` call from a host that already has one, then handing the worker a small static file.

2. **Steady state (every poll, purely local on the worker).** Given a pod name, resolve it to today's live container ID entirely on `topfull-worker-1`:

   ```
   docker ps --filter "label=io.kubernetes.pod.name=<pod>" \
             --filter "label=io.kubernetes.pod.namespace=default" \
             --filter "label=io.kubernetes.container.name=istio-proxy" \
             --format '{{.ID}}'
   ```

   This never touches the API server or kubelet. The collector caches `pod_name → container_id` (renamed from today's `pod_cache`, same shape/eviction semantics) and only re-runs this `docker ps` lookup when the cached container ID's `docker exec` fails.

**Why not push pod discovery fully local (worker running its own `kubectl`)?** It's not wrong, just unnecessary: it would require installing a read-only kubeconfig on `topfull-worker-1` (a one-time setup step, same pattern as the multi-user kubeconfig fix already documented in `AGENTS.md` §7) purely to do something the orchestrator can already do for free before the worker process even starts. Keeping `kubectl` usage entirely on the orchestrator/master side for this feature keeps the worker's dependency surface unchanged (nothing new to install beyond what `cri-dockerd`/`docker` already provide) and keeps the "no per-poll API-server hop" property trivially true by construction — there is no code path on the worker that can reach for `kubectl` even by accident.

### 3.3 Local exec + curl (replaces `fetch_stats_text`'s `kubectl exec`)

```
docker exec <container_id> curl -s http://localhost:15000/stats
```

Same target URL, same `istio-proxy` container, same admin port — only the transport to reach that container's namespace changes (Docker's own exec into a container it already runs locally, vs. kubelet brokering an attach on behalf of a remote API-server request). Output text is unchanged, so `parse_edges` / `parse_inbound` need **zero changes**. Timeout handling mirrors today's `KUBECTL_TIMEOUT_SECONDS` pattern, just wrapping `docker exec` instead of `kubectl exec` in the same `subprocess.run(..., timeout=..., check=False)` → `TimeoutError` shape `default_run_cmd` already uses.

Fallback command, if `docker exec` access turns out to be restricted for `idozacharia` on the worker (see §7):

```
crictl --runtime-endpoint unix:///var/run/cri-dockerd.sock exec <container_id> curl -s http://localhost:15000/stats
```

### 3.4 Getting the CSVs from the worker to where `run_scenario.py` expects them

**Constraint, stated explicitly per the task:** SSH + tmux orchestration, three independent VMs, **no shared filesystem assumed** between them.

**Chosen design — orchestrator-mediated pull at teardown, matching the existing collection model.**

- The worker-local collector writes `service_edges.csv` / `service_inbound.csv` to a local directory on `topfull-worker-1`, e.g. `/home/idozacharia/experiments/mesh_local/<log_folder>/` (mirrors the flat `results_base_path/<log_folder>/` naming convention already used on master, just under a worker-local root so it's obviously not the final results tree). Every row is still written synchronously (open-append-close per call, exactly as `write_edges_csv`/`write_inbound_csv` do today) — so any poll that completed has already durably hit the worker's local disk, independent of when/whether teardown happens cleanly.
- `run_scenario.py`'s existing stop sequence (`stop_master_stack` today; this adds a `stop_worker_mesh_collector`-equivalent step against `topfull-worker-1`, matching the `pkill -f '[e]nvoy_retry_collector.py'`/tmux-kill pattern) sends the collector's shutdown signal and waits for the tmux session to end.
- `collect_results()` gains a **two-hop pull**, using the orchestrator (the Windows machine already running `run_scenario.py`, which already has working SSH aliases to *both* `topfull-master` and `topfull-worker-1` per `.cursor/rules/topfull-ssh.mdc`) as the relay — because there is no reason to assume `topfull-worker-1` can SSH to `topfull-master` (or vice versa), and setting that up would be a new, workshop-project-scoped trust relationship for a feature that doesn't need it:
  1. `scp -r topfull-worker-1:/home/idozacharia/experiments/mesh_local/<log_folder>/ <local temp dir>` (orchestrator pulls from worker).
  2. `scp <local temp dir>/*.csv topfull-master:{dest}/` (orchestrator pushes into the exact same `dest` folder `collect_results()` already assembles everything else into).
  - Filenames (`service_edges.csv`, `service_inbound.csv`) are unchanged, so they land in `dest` indistinguishably from how they land today — nothing downstream (the printed final `scp -r topfull-master:{dest} ...` pull-to-PC command, `run_manifest.json`, analysis scripts) needs to know the mesh collector ever ran anywhere other than master.

**Trade-off, stated explicitly:** this pull happens only **once, at teardown**. If `topfull-worker-1` crashes hard (VM preemption/reboot, OOM-killed collector process) *before* teardown, whatever CSV rows are still only on the worker's local disk are lost — there is no periodic push during the run. This is a real regression versus today's design, where the collector's output already lives on the same host as the results directory the instant it's written.

**Alternatives considered and why they were not chosen for v1:**

| Alternative | Why not (for v1) |
|---|---|
| Periodic push (e.g. every 30–60 s) via a background thread inside the collector itself, `scp`'ing to master directly from the worker | Requires establishing SSH key trust **worker → master** that does not currently exist and is not needed for anything else in this project; adds a new failure mode (transient SSH failures mid-run) to a process whose whole point is to reduce load-path interference. Worth adding later as a resilience improvement if mid-run worker crashes turn out to matter in practice — flagged as follow-up, not required for v1. |
| Periodic pull orchestrated from the Windows side during `run_scenario.py`'s existing wait-for-duration loop | Same benefit (bounded data loss window) without the new VM-to-VM trust relationship — the orchestrator already has both aliases. Slightly more orchestrator complexity (needs to interleave a pull with the existing sleep-for-duration wait). Also flagged as a follow-up, not required for v1, since it is strictly additive to the teardown-pull design above (same code path, just called more than once) and can be layered on later without changing the collector or the CSV schema. |
| Shared filesystem (NFS/sshfs) mount between worker and master | New infra dependency (a filesystem service, mount units, failure handling for a workshop project on 3 GCP VMs with no existing shared storage) to solve a problem two `scp` calls at teardown already solve; explicitly out of scope per the task framing ("no shared filesystem assumed"). |
| Write directly over the network from inside the collector's per-poll loop (e.g. `scp` one row at a time, or an SSH-piped `cat >> remote_file`) | Reintroduces a per-poll network round-trip and process-spawn (opening a fresh SSH connection every 1 s) — the exact class of overhead this whole design exists to remove, just moved from `kubectl exec` to `scp`. |

### 3.5 Bounded concurrency (thread pool), keeping CSV writes serial

Today's `poll_once` is a plain `for service in sorted(services):` loop — 11 fully sequential discover→fetch→parse→write cycles. Local `docker exec` is cheaper than `kubectl exec` (no API-server hop), but still not free (container namespace attach + curl + tini/shell overhead), and doing 11 of them strictly sequentially still adds up. Per the task's guidance, this design uses a **small thread pool (3–4 workers)** to bound concurrency rather than firing off all 11 at once (which could itself transiently spike CPU/exec load on the worker — the same class of self-inflicted-overhead problem this whole change exists to avoid, just smaller).

Concrete shape (illustrative, not implementation): within one `poll_once` call,

1. `concurrent.futures.ThreadPoolExecutor(max_workers=4)` (configurable via the collector's params JSON, default 4, matching the task's "3–4" guidance) submits one task per service. Each task does the **read-only, no-shared-state** work: resolve container ID (local cache or `docker ps` on miss), run `docker exec ... curl ...`, parse the returned text with the existing pure `parse_edges`/`parse_inbound` — and returns `(service, edges_dict, inbound_dict)` or `None` on failure, exactly like today's per-service try/except-and-continue, just as a return value instead of an inline `continue`.
2. The **main thread**, after `as_completed()` drains the batch, calls `write_edges_csv` / `write_inbound_csv` **serially**, exactly as today, once per successfully-scraped service.

This keeps the existing CSV writers completely unchanged (no new locking, no risk of interleaved partial writes from two threads open-appending to the same file at once) while still parallelizing the part that actually costs wall-clock time (the exec+curl+parse). A single slow or hung service also can no longer block the other 10 sequentially — it just occupies one of the 3–4 pool slots until its own subprocess timeout fires.

### 3.6 Failure modes

Two tiers, matching the note in §3.2 about what a "pod restart" can mean:

**Tier 1 — container restart in place (common; e.g. `istio-proxy` crashes and is restarted by kubelet, or the whole pod's containers are restarted without the Pod object being deleted/recreated).** Pod name is unchanged; only the container ID changes. Detected exactly as today's design detects a stale cached pod: `docker exec <old_container_id> ...` fails (nonzero exit / "No such container") → evict that service's cache entry → on the **next** poll, re-run the local `docker ps --filter label=io.kubernetes.pod.name=<pod>` lookup (§3.2 tier 2) to pick up the new container ID. No crash, no process restart, a small (one-poll) measurement gap for that service — this is the direct local-exec analogue of today's `pod_cache.pop(service, None)` behavior, just against `docker ps` instead of `kubectl get pods`.

**Tier 2 — pod deleted and recreated (rare; e.g. eviction, manual `kubectl delete pod`, node drain — none of which are expected to happen mid-run in the current fixed-replica, no-HPA, no-rolling-deploy scenario configs, but not impossible).** The Pod gets a **new** name (ReplicaSet-assigned suffix changes), so the seeded `service → pod_name` map from §3.2 tier 1 is now stale, and the local `docker ps` lookup for the old pod name will never succeed again for that service. v1 behavior: the collector logs a bounded/rate-limited `WARNING` for that service every poll it stays stale (not a hard failure — `poll_once` continues scraping every other service normally, exactly like today's "no pod for service" warning path) and does not attempt to self-heal, because self-healing would require either a fresh `kubectl` call from *somewhere* (reintroducing an API-server dependency into the worker's runtime, if done locally) or another orchestrator-mediated push (a live channel that doesn't exist mid-run today, same as the CSV-transfer gap in §3.4). **Documented mitigation for v1:** restart the run (or just the collector's tmux session, if `run_scenario.py` gains a manual "re-seed and restart" helper) — since the current scenario configs never rescale/redeploy Boutique mid-run, this is expected to be rare enough that a full data gap for one service, for the remainder of a run, is an acceptable v1 trade-off, explicitly analogous to Tier 2 already being an accepted gap in the *current* master-based design too (today's `discover_pod_name` would also just keep returning the old, now-wrong cached-then-refreshed pod name via the same `app=<service>` selector — actually today's design *would* self-heal automatically on the next `kubectl get pods -l app=<service>` re-query, since that query is label-based and always returns whatever pod currently matches the label, which is the one advantage the current design has that this proposal gives up). **Flagged directly: this is a real regression vs. today's collector for Tier 2 specifically, traded for removing the API-server hop from the Tier-1/steady-state hot path** — call this out to the user/mentors as an explicit, accepted cost, not a silently-dropped capability.

**docker daemon or worker-node issues** (e.g. `dockerd` briefly unresponsive) are handled the same way today's `kubectl exec` transport failures are: `default_run_cmd`'s `subprocess.TimeoutExpired` → `TimeoutError`, caught in the per-service task, logged, `None` returned for that service that poll — never propagates to crash `poll_once` or the main loop.

### 3.7 Deployment and lifecycle in `run_scenario.py`

Today, `run_scenario.py` only ever deploys/starts collector scripts against `cfg["infra"]["master_ssh_host"]`. This design adds `topfull-worker-1` as a **second deployment target**, following the exact same three-step pattern already used for master (`deploy_repo_script` → `write_remote_json` params → `write_remote_script` launcher + `tmux new-session -d`):

- New `infra.worker_ssh_host` field in scenario YAMLs (today's `infra:` block only has `master_ssh_host` and `loadgen_ssh_host`), set to `topfull-worker-1` — the SSH alias, never a hardcoded IP, per `.cursor/rules/topfull-ssh.mdc`.
- A new `start_mesh_collector_on_worker(cfg)`-equivalent function, mirroring `start_envoy_retry_collector`'s shape:
  1. `deploy_repo_script(worker, "envoy_retry_collector.py", <worker path under /home/idozacharia/...>)` — same helper, new host argument. (Whether this becomes a renamed/forked script or the same file with a `--local-exec` mode is an implementation decision, out of scope here — see §8 open items; either way it deploys the same way.)
  2. Orchestrator runs the one-time `kubectl get pods -l app=<service>` discovery **against master** (§3.2 tier 1) and folds the resulting `service → pod_name` map into the collector's params JSON, alongside `poll_interval_seconds` and the thread-pool size (§3.5), then `write_remote_json`s that params file **to the worker**, not master.
  3. `write_remote_script(worker, "/tmp/rg_mesh_local.sh", ...)` + `tmux new-session -d -s meshlocal /tmp/rg_mesh_local.sh` — same launcher pattern, new host, new tmux session name (distinct from any tmux sessions already used on master, since it's a different machine anyway — no collision risk, but keep the name distinct for operator clarity when SSHed into either box).
- Lifecycle-managed stats-inclusion patching (`ensure_envoy_stats_enabled`) **stays on master** (it's a `kubectl patch deployment` control-plane call, run once per run, unrelated to where the scrape loop executes) — no change needed there.
- Teardown: a new stop step (called alongside today's `stop_master_stack` / `stop_locust`) sends the equivalent of `pkill -f '[e]nvoy_retry_collector.py'; tmux kill-server` **to `topfull-worker-1`** instead of (or in addition to, if the legacy master-based collector is kept behind a flag during a transition period — see §8) master.
- Results collection: `collect_results()` gains the two-hop pull described in §3.4, called after the worker-side stop step completes (so the collector has definitely stopped writing before the files are copied — same ordering guarantee `stop_master_stack` → `collect_results()` already gives the master-based collectors today).
- `run_manifest.json` gains a field recording where the mesh collector actually ran for that run (e.g. `"envoy_retry_collector": {..., "exec_mode": "worker_local_docker_exec"}`), so a future analysis script (or a human comparing `campaign_48/` runs to whatever supersedes it) can tell which execution path produced a given run's `service_edges.csv` / `service_inbound.csv` without having to know the run date by heart — same spirit as the existing `paper_cpu_quotas`/`effective_cpu_quotas` manifest fields recording *which* quota map a run used.
- Scenario YAML changes needed to fully adopt this (adding `infra.worker_ssh_host`, and whatever new `envoy_retry_collector:` sub-keys the thread-pool size / exec-mode need) are **not** written by this spec — flagged as implementation follow-up, matching the task's "do not change scenario YAMLs" instruction.

---

## 4. Data contract: unchanged by design

Everything downstream of the CSV files is unaffected, by construction:

- `EDGES_CSV_COLUMNS` / `INBOUND_CSV_COLUMNS`, `OUTBOUND_RE` / `INBOUND_RE`, `parse_edges` / `parse_inbound`, `write_edges_csv` / `write_inbound_csv` — **zero changes**. Only `fetch_stats_text`'s transport (`kubectl exec` → `docker exec`) and `discover_pod_name`'s transport/cadence (per-poll-capable `kubectl get pods` → seed-once-then-local-`docker ps`) change.
- RetryGuard's `measure_value()` ([2026-09-10-retryguard-mesh-measure-value-design.md](2026-09-10-retryguard-mesh-measure-value-design.md)) reads `service_inbound.csv` by column name and has no dependency on which host produced the file.
- `mentor_charts.py` / `mentor_charts_data.py` — still Locust-only today per `AGENTS.md` §4's follow-up note; whenever they are wired to read `service_inbound.csv`/`service_edges.csv`, this change is invisible to them.
- Any run that used the *old* master-based collector (all of `campaign_48/`, `august_38/`, and every run before this spec's implementation) is completely unaffected; there is no migration or backfill implied by this design.

---

## 5. Testing strategy

Matches `experiments/test_envoy_retry_collector.py`'s existing conventions (stdlib `unittest`, injected `CommandRunner`, `SimpleNamespace` fake results, no real subprocess/SSH/Docker in unit tests):

- **Parsers stay covered by the existing tests as-is** (`parse_edges`, `parse_inbound`) — they take raw `/stats` text regardless of transport, so no new tests are needed there; this spec's changes are purely upstream of them.
- **New: local container-ID resolution.** A test analogous to today's `TestDiscoverPodName`, but for a `docker ps`-filter command builder — inject a fake `run_cmd` that asserts the built command contains `docker`, `ps`, `--filter`, and the three expected `label=` filter values (`io.kubernetes.pod.name=<pod>`, `io.kubernetes.pod.namespace=default`, `io.kubernetes.container.name=istio-proxy`), and returns a fake container ID via `stdout`. Mirror the "returns None on failure" / "returns None on empty stdout" cases from `TestDiscoverPodName`.
- **New: local exec+curl command builder.** Analogous to `TestFetchStatsText` — inject a fake `run_cmd`, assert the built command is `["docker", "exec", <container_id>, "curl", "-s", "http://localhost:15000/stats"]` (or the `crictl` fallback shape if that path is implemented), and reuse the existing "nonzero exit → None" / "timeout exception → None" test cases unchanged.
- **New: Tier-1 vs Tier-2 failure-mode tests**, matching the style of today's `test_survives_one_service_fetch_failure`:
  - Tier 1: seed a cached `pod_name → container_id`; make the fake `run_cmd` return failure for `docker exec <old_id>` but success for a subsequent `docker ps` lookup returning a *new* container ID for the *same* pod name; assert the next poll succeeds and the cache is updated to the new ID.
  - Tier 2: seed a cached pod name; make the fake `run_cmd` return empty/failure for `docker ps --filter label=io.kubernetes.pod.name=<pod>` indefinitely; assert `poll_once` logs a warning and continues scraping the other services without raising, and that repeated polls do not crash the loop (bounded/rate-limited logging, not a runaway warning per test tick — assert the logging call count is bounded if that mechanism is implemented, or at minimum that no exception propagates).
- **New: thread-pool batching does not break serial CSV writes.** A test that supplies a fake `run_cmd` returning distinct stats text per service and a small `max_workers` value, runs one `poll_once`-equivalent batch, and asserts (a) the resulting CSVs contain exactly one row per service per poll (no duplicate or missing rows from a race), and (b) — since real thread races are inherently flaky to assert on — that the CSV-writing calls themselves happen from the main thread/after `as_completed()`, by structuring the implementation so writers are unit-testable as pure serial calls, same as `TestWriteEdgesCsv`/`TestWriteInboundCsv` already do today (no new locking logic to test if writes stay serial by construction).
- **New: seed-discovery params consumption.** A test that the collector, given a params JSON containing a pre-seeded `service → pod_name` map (instead of discovering it itself), uses that map as its initial cache and does not call any discovery command for a service until that service's cached entry first fails — analogous to today's `TestResolveServices` (`test_defaults_to_all_services` / `test_override_via_params`).
- **`run_scenario.py` orchestration changes** (new `worker_ssh_host`, the one-time master-side discovery call, the two-hop `scp` pull) get unit-style tests analogous to `experiments/test_run_scenario.py`'s existing coverage of `deploy_repo_script` / `write_remote_json` / `write_remote_script` call shapes — asserting the right `ssh`/`scp` argument lists are built for the worker host, without actually shelling out (same mocking pattern already used there).
- No test in this suite performs a real SSH connection, real `docker`/`kubectl` call, or touches the actual VMs — consistent with every existing collector test file in this repo.

---

## 6. Success criteria

- A run with this design produces `service_edges.csv` / `service_inbound.csv` in the exact same location and shape (`run_manifest.json`-recorded `dest` folder, identical column sets) as today's master-based collector — verified by diffing schemas/column names against a `campaign_48/` run's files (values will legitimately differ; structure must not).
- Direct (no-goproxy) request latency under S2-equivalent load, measured the same way as [2026-09-11-slo-fail-and-mu-estimator-design.md](2026-09-11-slo-fail-and-mu-estimator-design.md) §8's curl matrix, shows the mesh-collector-on vs mesh-collector-off gap shrink relative to that spec's ~1.45 s vs ~1.84 s baseline (does not need to hit exactly 0 — some local-exec cost is expected and accepted per §3.5's bounded-concurrency reasoning — but the API-server/kubelet hop specifically should no longer be part of that gap).
- A simulated Tier-1 failure (container restart in place) recovers within one poll cycle without operator intervention, per §3.6/§5.
- A simulated Tier-2 failure (pod recreated) is logged clearly enough that an operator reviewing `*_collector.log` after a run can tell that service's data has a gap and why, without the collector process itself crashing or stopping other services' polling.
- `RetryGuard.measure_value()` and any future `mentor_charts.py` wiring require **zero code changes** to consume output produced by this design instead of the current one.
- Unit tests for the new local-exec/discovery/batching logic exist and pass under the same `python experiments/test_envoy_retry_collector.py`-style invocation (or a renamed/split test file, if the implementation forks the script rather than extending it) with no real subprocess/network access.

---

## 7. Open verification items (do before implementing)

Per this repo's existing pattern of flagging blocking pre-implementation checks (see [2026-09-09-topfull-throttle-collector-design.md](2026-09-09-topfull-throttle-collector-design.md) §5's "verify the real `resource_collector.py` on master" item):

1. **Confirm `idozacharia` on `topfull-worker-1` can run `docker exec`/`docker ps` without a password prompt.** The Docker daemon socket is typically root/`docker`-group-owned; confirm `idozacharia` is in the `docker` group on the worker (may not be, if the group was only ever granted on master for a different purpose) or that passwordless `sudo docker ...` is viable for a non-interactive tmux-launched script. If neither holds, fall back to `crictl` (§3.3) with equivalent permission checks against `/var/run/cri-dockerd.sock`.
2. **Confirm the container labels cri-dockerd actually sets** (`io.kubernetes.pod.name`, `io.kubernetes.pod.namespace`, `io.kubernetes.container.name`) by running one manual `docker inspect` against a live `istio-proxy` container on the worker — this design's §3.2 tier-2 lookup depends on these exact label keys, and different cri-dockerd/Docker versions have occasionally varied label naming.
3. **Confirm `topfull-worker-1` has Python 3 + whatever venv this collector needs** already available (today's collectors only ever ran on master, which has `TopFull`'s venv already `source`'d in every launcher script) — the worker may need its own venv/interpreter set up as a one-time prerequisite, analogous to master's existing `venv_activate` infra field.
4. **Decide fork-vs-flag for the script itself**: whether `envoy_retry_collector.py` grows a `--exec-mode {kubectl,docker_local}` switch (one file, two transports, selected by which host/params it's given) or whether this becomes a second script (e.g. `envoy_retry_collector_worker_local.py`) sharing the parsing/CSV-writer functions via import. Either is consistent with this spec; picking one is an implementation detail deferred to the implementing task, not decided here.

---

## Status

Design spec only (2026-09-12). No code, scenario YAML, or `run_scenario.py` changes made. Not implemented; no campaign data exists or is implied by this document.
