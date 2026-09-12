# Mesh collector: network scrape (port 15020) instead of exec, master-only

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Design (spec only, no implementation) for removing the `docker exec`/`kubectl exec` transport from the full-mesh Envoy collector entirely, replacing it with a plain network HTTP GET to each pod's Istio pilot-agent merged-metrics port (`15020`), and collapsing the collector back onto `topfull-master` only. Motivated by a live-verified finding (2026-09-13): a scratch S1 credit trio (`run7`–`run10`, recorded in [2026-09-11-slo-fail-and-mu-estimator-design.md](2026-09-11-slo-fail-and-mu-estimator-design.md) §8 addendum) showed the worker-local `docker exec`-based mesh collector (`exec_mode: docker_local`, landed [2026-09-12](2026-09-12-mesh-collector-worker-local-exec-design.md)) costing **+470 ms getcart P95 / +25.2 percentage-point Fail** versus baseline — almost the entire collector tax, while the throttle collector cost only +12 ms / +0.4pp. Root cause, confirmed live against the running cluster: `docker exec <istio-proxy container> curl …` forks a new process **inside the sidecar's own cgroup**, competing for CPU with the same container that is serving the request. Port `15020` is reachable directly over the pod network (verified: `topfull-master → curl http://<pod_ip>:15020/stats/prometheus` → `HTTP 200` in 16 ms) and is served by `pilot-agent`, a process that does not fork per request and does not run inside the request-handling path's CPU budget in the same way.

---

## 1. Purpose and scope

**In scope**

- New scrape transport: HTTP GET to `http://<pod_ip>:15020/stats/prometheus`, replacing both existing transports (`kubectl exec` and `docker exec`).
- New parser functions for Prometheus text-exposition format (`metric{labels} value`), replacing the admin-port colon format (`metric: value`) parsers. **Verified live label/metric shapes** (§3.3) — not guessed.
- Fixing the "outbound class-counter gap" documented in [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md): live outbound `2xx`/`4xx`/`5xx` are available on port 15020 (`envoy_cluster_upstream_rq{response_code_class="…"}`) where the admin-port `/stats` never exposed them for outbound. `service_edges.csv` column values for those classes become real instead of always-0. **Column names/schema unchanged.**
- Collapsing the collector back to a single host (`topfull-master`): delete the worker-local deployment path (`start_mesh_collector_on_worker`, `stop_worker_mesh_collector`, `pull_worker_mesh_csvs`, `WORKER_MESH_ROOT`, `discover_service_pod_map`'s worker-seeding role, `docker_ps_container_id_cmd`/`docker_exec_stats_cmd`/`discover_container_id`/`fetch_stats_text_docker`/`ServiceScrapeResult`'s container-ID fields, `MANIFEST_EXEC_MODE_DOCKER`). Delete the now-unused `infra.worker_ssh_host` field from all 16 scenario YAMLs.
- Renaming the config/manifest field from `exec_mode` to `transport` (per explicit instruction — nothing is "exec"'d anymore). Single supported value: `network_prometheus`. Old values (`kubectl`, `docker_local`) are removed, not deprecated-in-place.
- Pod discovery: swap seeded `service → pod_name` for `service → pod_ip` (one-time `kubectl` call on master, same selector, different `jsonpath`).
- Failure handling: **Tier-2 self-heal.** Since discovery is now a cheap local `kubectl` call on master (no SSH-to-worker, no per-poll cost — it only ever ran once at seed time, and re-running it is still only on-failure), a pod-recreated (new IP) failure triggers an automatic re-seed for that service, rate-limited the same way today's Tier-2 warning is rate-limited (`TIER2_WARN_EVERY_POLLS`). This closes a gap that `docker_local`'s design explicitly accepted as v1 cost.
- Restoring RetryGuard's live view of `service_inbound.csv`: since output is written directly into master's `record_path` throughout the run (no teardown-only pull), `measure_value()` stops being blind for the whole run — a side effect of going master-only, not a change to `retryguard.py` itself.
- Testing strategy consistent with `experiments/test_envoy_retry_collector.py` (injected fetcher, no real network/subprocess in unit tests).

**Out of scope (explicit)**

- Changing `EDGES_CSV_COLUMNS` / `INBOUND_CSV_COLUMNS` names, or anything RetryGuard's `measure_value()` or `mentor_charts.py` read by column name.
- Changing `retryguard.py` itself (it already reads `service_inbound.csv` by column name; regaining a live view is a byproduct, not a code change there).
- Changing `resource_usage_collector.py` or `topfull_throttle_collector.py` — neither ever moved to the worker and neither is affected by this change.
- Re-running or backfilling `campaign_48/` / `august_38/` / any run made under `docker_local` or `kubectl` transports. As with every prior mesh-collector change, only future runs get this.
- Actually writing or modifying any `.py` file, scenario YAML, or `run_scenario.py` code. This document specifies the change; implementation is a separate task (writing-plans skill, next).
- Re-litigating the live-verified finding that `docker exec` is the tax source, or re-measuring run7–10 — already done, cited above.
- Changing `sample_interval_seconds`/`interval_samples` for RetryGuard, or Locust `user_counts`/`spawn_rate` — unrelated knobs.

---

## 2. Current behavior (baseline for comparison)

From `experiments/envoy_retry_collector.py` / `experiments/run_scenario.py` as of [2026-09-12](2026-09-12-mesh-collector-worker-local-exec-design.md):

- `exec_mode: docker_local` (current YAML default across all 16 scenario configs) runs the collector on `topfull-worker-1`. Every poll (`poll_interval_seconds`, typically 1 s), a thread pool of `max_workers` (default 4) does, per service: resolve a cached `pod_name → container_id` (via `docker ps --filter label=io.kubernetes.pod.name=… io.kubernetes.pod.namespace=default io.kubernetes.container.name=istio-proxy`, cached after first success), then `docker exec <container_id> curl -s http://localhost:15000/stats`.
- `exec_mode: kubectl` (fallback, unused by current YAMLs) does the equivalent from `topfull-master` via `kubectl exec <pod> -c istio-proxy -- curl -s http://localhost:15000/stats`, strictly sequential.
- Both transports parse the admin-port `/stats` colon format (`OUTBOUND_RE`, `INBOUND_RE`) into `service_edges.csv` (`timestamp, caller, target, total, 2xx, 4xx, 5xx, retry`) and `service_inbound.csv` (`timestamp, service, total, 2xx, 4xx, 5xx`).
- **Live gap (documented, [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md)):** the admin-port `/stats` exposes outbound `total`/`retry` but not `2xx`/`4xx`/`5xx` on this cluster's Envoy version — those three columns are always 0 in `service_edges.csv` regardless of load.
- `docker_local` writes to a worker-local directory (`/home/idozacharia/experiments/mesh_local/<log_folder>/`) and is pulled to master only at teardown (two-hop `scp`), meaning `retryguard.py`'s `measure_value()` (which reads `service_inbound.csv` from master's `record_path` mid-run) sees nothing for the entire run — an accepted v1 cost at the time.

**Cost measured (2026-09-12, S1 credit trio, [2026-09-11-slo-fail-and-mu-estimator-design.md](2026-09-11-slo-fail-and-mu-estimator-design.md) §8 addendum):**

| Slot | Arm | getcart P95 | getcart Fail |
|---|---|---|---|
| run8 | mesh only | 1370 ms | 26.7 |
| run9 | throttle only | 912 ms | 1.9 |
| run10 | both off | 900 ms | 1.5 |

Mesh tax ≈ run8 − run10: **+470 ms P95, +25.2pp Fail.** Throttle tax ≈ run9 − run10: +12 ms, +0.4pp. The mesh collector is essentially the entire remaining tax, and it reproduces even in S1 (no CPU limits at all applied), which rules out "it's only bad because a target service has a tiny CPU quota" as the sole explanation — the fork/exec cost itself, 11 times a second, is the dominant term.

---

## 3. Proposed design

### 3.1 Root cause, confirmed live (2026-09-13)

```
topfull-worker-1$ nproc
8
topfull-worker-1$ docker exec <frontend-istio-proxy> curl -s http://localhost:15000/stats  # today's transport
```

`docker exec` runs the new `curl` process **inside the target container's own cgroup/network namespace** — the same cgroup Envoy itself uses to serve real traffic. Forking+execing a process 11 times a second (pool of 4 concurrent) inside that cgroup is real, measurable CPU competition with the sidecar's own worker threads, independent of whether that container has a tight `cpu_limit` (S3/S4) or none at all (S1, where the tax still showed up).

### 3.2 Verified alternative: pilot-agent's merged-metrics port, reachable over the network

```
topfull-master$   curl -s -o /dev/null -w '%{http_code} %{time_total}s' http://<frontend_pod_ip>:15020/stats/prometheus
200 0.016s
topfull-worker-1$ curl -s http://<frontend_pod_ip>:15020/stats/prometheus | wc -l
3060
```

Port 15020 is Istio's standard Prometheus-scrape endpoint, served by `pilot-agent` (a background process in the `istio-proxy` container, separate from Envoy's request-handling worker threads) and — critically — **bound reachably over the pod network, not just loopback**. Both `topfull-master` and `topfull-worker-1` can reach it directly today, with no `kubectl`/`docker` involved, no exec, no fork inside the app/sidecar's request path. This holds for **every** Boutique pod (verified against `frontend`; the endpoint is a standard Istio sidecar feature present on all 11 injected pods).

### 3.3 Verified metric shapes (exact, from a live scrape — not assumed)

```
envoy_cluster_upstream_rq_total{cluster_name="outbound|3550||productcatalogservice.default.svc.cluster.local"} 1891218
envoy_cluster_upstream_rq_retry{cluster_name="outbound|15010||istiod.istio-system.svc.cluster.local"} 0
envoy_cluster_upstream_rq{response_code="200",cluster_name="outbound|3550||productcatalogservice.default.svc.cluster.local"} 1890768
envoy_cluster_upstream_rq{response_code_class="2xx",cluster_name="outbound|3550||productcatalogservice.default.svc.cluster.local"} 1890768

envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 485393
envoy_http_inbound_0_0_0_0_8080_downstream_rq_completed{} 483945
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="1xx"} 0
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="2xx"} 483945
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="3xx"} 0
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="4xx"} 0
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="5xx"} 0
```

Mapping to today's CSV columns:

| CSV | Column | Prometheus metric |
|---|---|---|
| `service_edges.csv` | `total` | `envoy_cluster_upstream_rq_total{cluster_name="outbound\|<port>\|\|<target>.default.svc.cluster.local"}` |
| `service_edges.csv` | `retry` | `envoy_cluster_upstream_rq_retry{cluster_name="outbound\|<port>\|\|<target>.default.svc.cluster.local"}` |
| `service_edges.csv` | `2xx`/`4xx`/`5xx` | `envoy_cluster_upstream_rq{response_code_class="2xx\|4xx\|5xx",cluster_name="outbound\|<port>\|\|<target>.default.svc.cluster.local"}` — **new, was always 0** |
| `service_inbound.csv` | `total` | `envoy_http_inbound_<listener>_downstream_rq_total{}` |
| `service_inbound.csv` | `2xx`/`4xx`/`5xx` | `envoy_http_inbound_<listener>_downstream_rq{response_code_class="2xx\|4xx\|5xx"}` |

Note the metric-name shape difference from the admin-port format: the listener identifier (`0_0_0_0_8080`) is embedded **in the metric name itself** for inbound stats (Prometheus sanitizes `.`/`:` to `_`), not carried as a label — unlike outbound, where `target` is a label value inside `cluster_name="outbound|<port>||<target>.default.svc.cluster.local"`. The parser needs two distinct regexes (one per metric-name family), same as today's `OUTBOUND_RE`/`INBOUND_RE` split, just against different text.

**Guardrail for the implementing task:** do not hardcode label order (`response_code_class` before `cluster_name` was observed consistently, but Prometheus exposition format does not guarantee label order across Envoy versions). Parse the `{...}` label block as key="value" pairs (split on `,`, then `=`) rather than anchoring a regex on a fixed sequence, the same way a real Prometheus client library would.

### 3.4 Architecture: back to master-only, no worker involvement

```
run_scenario.py (Windows)
  └─ deploy_repo_script(master, "envoy_retry_collector.py")
  └─ seed: kubectl get pods -l app=<service> -o jsonpath='{.items[0].status.podIP}'   (once, on master)
  └─ write_remote_json(master, params: {pod_ips, poll_interval_seconds, max_workers, transport: "network_prometheus"})
  └─ write_remote_script + tmux new-session -d -s envoyretry   (on master, same as pre-worker-local design)

envoy_retry_collector.py (running on master)
  └─ every poll: ThreadPoolExecutor(max_workers) → per service: GET http://<pod_ip>:15020/stats/prometheus
  └─ parse → write_edges_csv / write_inbound_csv directly into record_path (no scp, no pull step — same host as results dir)
```

This is the same three-step deploy/params/launch pattern `run_scenario.py` already uses for `resource_usage_collector.py` and `topfull_throttle_collector.py` — both already master-only, single-host, no pull step. The mesh collector rejoins that pattern instead of being the only one with worker-local/two-hop plumbing.

**Deleted from `run_scenario.py`:** `start_mesh_collector_on_worker`, `stop_worker_mesh_collector`, `pull_worker_mesh_csvs`, `WORKER_MESH_ROOT`, `MANIFEST_EXEC_MODE_DOCKER`, `mesh_exec_mode` (replaced by a simpler `envoy_collector_manifest` that just records `transport: "network_prometheus"` unconditionally — no branching, since there is only one path now).

**Deleted from `envoy_retry_collector.py`:** `EXEC_MODE_KUBECTL`, `EXEC_MODE_DOCKER_LOCAL`, `resolve_exec_mode`, `docker_ps_container_id_cmd`, `docker_exec_stats_cmd`, `discover_container_id`, `fetch_stats_text_docker`, `discover_pod_name`/`fetch_stats_text` (admin-port kubectl versions), `ServiceScrapeResult.container_id`/`evict_container` (container-ID concept doesn't exist anymore), the `--exec-mode` CLI flag.

**Deleted from all 16 scenario YAMLs:** `infra.worker_ssh_host` (no longer used by anything); `envoy_retry_collector.exec_mode: docker_local` becomes `envoy_retry_collector.transport: network_prometheus` (or the key is simply dropped if we decide a single-valued field isn't worth keeping — implementation task's call, default is to keep it for manifest provenance, matching how `paper_cpu_quotas`/`effective_cpu_quotas` record "which map a run used" even when there's currently only one map in play).

### 3.5 Discovery and Tier-2 self-heal

Seed once per run, via `kubectl get pods -n default -l app=<service> -o jsonpath='{.items[0].status.podIP}'` (master only, one call per service, exactly like today's pod-name seed — just a different `jsonpath` field). Result: `service → pod_ip` map, pushed to the collector's params JSON.

Per poll, per service: `GET http://<cached_pod_ip>:15020/stats/prometheus`, `KUBECTL_TIMEOUT_SECONDS`-equivalent timeout (reuse the same constant, rename if desired). On failure (connection refused/timeout — the pod was recreated and has a new IP):

1. Log a warning (same shape as today's Tier-2 warning), rate-limited via the existing `TIER2_WARN_EVERY_POLLS` / `should_log_tier2` mechanism.
2. **Re-seed that one service** — re-run the single `kubectl get pods -l app=<service> -o jsonpath=…podIP` call (master already has a working kubeconfig; this is not a new dependency, and it is bounded to at most once per `TIER2_WARN_EVERY_POLLS` polls per service, same rate limit as the warning, to avoid a re-seed storm if a service is genuinely down).
3. If re-seed returns a new IP, update the cache and resume scraping that service on the next poll. If it returns nothing (pod genuinely gone / scaled to 0), keep warning at the same rate and keep trying — same "never crash `poll_once`, never stop scraping other services" guarantee as today.

There is no Tier-1 concept anymore (no container ID to go stale independent of the pod) — this collapses today's two-tier failure model into one.

### 3.6 Naming

Config/manifest field renamed `exec_mode` → `transport`. Single value: `network_prometheus`. `run_manifest.json`'s `envoy_retry_collector` block records `{"transport": "network_prometheus", "exec_host": "topfull-master"}` unconditionally (no more `docker_local` vs `kubectl` distinction to record, but the field stays for the same provenance reason `paper_cpu_quotas`/`effective_cpu_quotas` stay even when only one map is in play — so a future analysis script can tell this run's mesh data apart from any pre-2026-09-13 `docker_local`/`kubectl` run by transport name, without knowing the date by heart).

---

## 4. Data contract: unchanged column names, corrected values

- `EDGES_CSV_COLUMNS` / `INBOUND_CSV_COLUMNS` — **zero changes.**
- `service_edges.csv` `2xx`/`4xx`/`5xx` columns go from **always 0** to **real values**, sourced from `envoy_cluster_upstream_rq{response_code_class="…"}`. This is a data-quality fix, not a schema change — any code reading these columns by name (none currently does, per the documented live gap) starts getting real numbers instead of zeros, for free.
- `service_inbound.csv` columns are unaffected in shape; values come from a different metric-name family but the same semantic quantities.
- RetryGuard's `measure_value()` ([2026-09-10-retryguard-mesh-measure-value-design.md](2026-09-10-retryguard-mesh-measure-value-design.md)) reads `service_inbound.csv` by column name and has no dependency on transport. It regains a **live** view mid-run (master-only, no teardown-only pull) as a side effect of this change — worth calling out to the user/mentors as an incidental fix to a previously-accepted gap, not a claim that `retryguard.py` itself changed.
- `mentor_charts.py` / `mentor_charts_data.py` — still Locust-only today; unaffected either way.
- Any run made under `docker_local` or `kubectl` transports (all of `campaign_48/`, `august_38/`, and every scratch run through 2026-09-13) is completely unaffected; no migration or backfill implied.

---

## 5. Testing strategy

Matches `experiments/test_envoy_retry_collector.py`'s existing conventions (stdlib `unittest`, injected fetcher callable, no real network/subprocess):

- **New: Prometheus label-block parser.** A small helper that turns `{key="val",key2="val2"}` into a dict, tested independently of the metric-specific regexes (covers label order not being guaranteed, extra/missing labels, empty label sets `{}`).
- **New: outbound parser tests** — fixture text containing `envoy_cluster_upstream_rq_total{...}`, `_retry{...}`, and `envoy_cluster_upstream_rq{response_code_class="2xx",...}` lines for 2–3 targets; assert `parse_edges`-equivalent returns `total`/`retry`/`2xx`/`4xx`/`5xx` correctly per target, including a target that has zero 4xx/5xx lines (must default to 0, not KeyError).
- **New: inbound parser tests** — fixture text containing `envoy_http_inbound_<listener>_downstream_rq_total{}` and `envoy_http_inbound_<listener>_downstream_rq{response_code_class="…"}` lines; assert correct `total`/class extraction; test with more than one listener id present (should not exist in practice — Boutique services expose one HTTP port each — but the parser should not silently merge two listeners if it ever happened).
- **New: HTTP fetch tests** — inject a fake fetcher (matching today's `CommandRunner` injection style but for an HTTP call, e.g. `Callable[[str], SimpleResult-like]`) returning canned Prometheus text or a simulated timeout/connection-refused; assert `None` is returned on failure without raising, mirroring today's `fetch_stats_text`/`fetch_stats_text_docker` test shapes.
- **New: seed-by-pod-IP test** — analogous to today's `TestDiscoverPodName`, asserting the seed `kubectl` command's `jsonpath` targets `.items[0].status.podIP`.
- **New: Tier-2 self-heal test** — seed a cached pod IP; make the fake fetcher fail for that IP; make the fake re-seed call return a *new* IP; assert the next poll succeeds against the new IP and the cache is updated. Also test the rate-limit: repeated failures within `TIER2_WARN_EVERY_POLLS` polls should not re-seed on every single poll.
- **Thread-pool batching / serial CSV writes** — same test shape as the [2026-09-12](2026-09-12-mesh-collector-worker-local-exec-design.md) design already established; no change needed to that pattern, just swap what the pooled task does (HTTP GET instead of docker exec).
- **`run_scenario.py` orchestration tests** — updated to assert the single master-only deploy/params/launch call shape (no worker host, no two-hop `scp`, no `mesh_exec_mode` branch), analogous to existing coverage for `resource_usage_collector`'s simpler single-host pattern.
- No test performs a real HTTP request, SSH connection, or touches the actual VMs.

**Live validation (before touching any scenario YAML default):** re-run the S1 credit-trio methodology (scratch, next free run slots, bump numbers per `AGENTS.md` §6 discipline) — network-scrape-only vs baseline-with-collectors-off — and confirm the getcart P95/Fail gap has closed to something in the same ballpark as the documented throttle-only tax (+12 ms / +0.4pp), not just "better than +470 ms/+25.2pp." Only after that passes does the implementation flip the 16 YAMLs' `transport` default and remove the old code paths for good (per your "remove, don't keep as fallback" decision).

---

## 6. Success criteria

- A run with this design produces `service_edges.csv` / `service_inbound.csv` in the same location (`record_path`, directly on master, no pull step) and column shape as today — verified by diffing schema against a `campaign_48/` run's files (values legitimately differ in that outbound class columns are no longer always 0).
- Scratch S1 trio (mirroring run7–10) shows the mesh-collector-on-vs-off getcart P95/Fail gap shrink to a magnitude comparable to the throttle collector's already-small tax, not merely "smaller than +470 ms."
- `RetryGuard.measure_value()` observes non-empty `service_inbound.csv` rows **during** a run (not just at teardown) — verifiable via `retryguard.py`'s own log, without any code change to `retryguard.py`.
- A simulated pod-recreation (Tier-2) failure self-heals within one rate-limit window (`TIER2_WARN_EVERY_POLLS` polls) without operator intervention.
- Zero code changes required in `retryguard.py` or `mentor_charts.py` to consume this design's output instead of `docker_local`'s.
- All new/updated unit tests pass under `python -m unittest experiments/test_envoy_retry_collector.py experiments/test_run_scenario.py` (or current equivalent invocation) with no real network/subprocess access.

---

## 7. Open verification items (do before implementing)

1. **Confirm port 15020 is reachable from `topfull-master` to *every* Boutique pod IP**, not just `frontend` (this spec verified `frontend` only). Different Deployments could in principle have `NetworkPolicy` or Istio `PeerAuthentication` differences — unlikely given none are configured in this project, but worth one loop over all 11 services before writing tests against assumed-uniform behavior.
2. **Confirm the exact metric-name shape for every service's inbound listener**, not just `frontend`'s `8080` — gRPC-only backends (e.g. `paymentservice`, `currencyservice`) may expose a differently-shaped inbound metric family (`envoy_*_downstream_rq_*` for gRPC can differ from HTTP's `envoy_http_inbound_*`) since Envoy's gRPC stats and HTTP stats aren't always identical metric families. If a backend's shape differs, the inbound parser needs a second pattern for it — decide during implementation, not assumed here.
3. **Confirm pod IP stability across a full run duration** (up to 900 s for S6) — i.e. that nothing in these fixed-replica, no-HPA scenario configs recreates a pod mid-run under normal operation (this is already asserted as true for the existing Tier-2 discussion; re-confirm it still holds, since this design's whole benefit only fully lands if re-seeds are rare, not routine).
4. **Confirm `redis-cart`'s behavior** — it's TCP-only (no HTTP `upstream_rq_*`/`downstream_rq_*`), so parsing its `/stats/prometheus` output should yield empty edges/inbound (same as today's behavior on the admin port) rather than an error. Verify empirically rather than assuming.

---

## Status

Design spec only (2026-09-13). No code, scenario YAML, or `run_scenario.py` changes made. Not implemented; no campaign data exists or is implied by this document. Follow-up: writing-plans skill, once this spec is reviewed and approved.
