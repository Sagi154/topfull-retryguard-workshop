# TopFull throttle collector — design

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Design for a new collector that records TopFull's own admission/throttle state (Layer A: cap + admitted RPS; Layer B: overload-detector reconstruction) on the **same wall-clock 1s grid** as the per-service mesh collector ([PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md)), so any given second has both a throttle snapshot and a per-service mesh snapshot. Extends [TOPFULL-THROTTLE-METRICS.md](../../../Guides%20and%20Info/TOPFULL-THROTTLE-METRICS.md) (inventory of live sources, Layers A–D) into an implementable spec for Layers A and B only. Implemented (2026-09-09). No campaign folder has this data yet.

---

## 1. Purpose and scope

This collector answers one eval question: how TopFull's ~1s RL admission loop and RetryGuard's 30s toggle windows interact. Locust `RPS` (already collected) is only completed traffic *after* the proxy — a weak proxy for what TopFull actually admitted. `num_agent.csv` is empty and will not be revived.

Per Locust API (`getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`):

| Column | Source | Meaning |
|---|---|---|
| `threshold` | `rate_config/<api>` on master | Cap the RL set that second |
| `admitted_rps` | `GET http://127.0.0.1:8090/stats` | What the proxy actually forwarded |

Per tracked microservice (reconstructed, not scraped from TopFull's own internal state):

| Column | Source | Meaning |
|---|---|---|
| `cadvisor_cpu` | same cAdvisor source `resource_collector.py` polls | CPU usage TopFull's detector would see |
| `overloaded` | derived: `cadvisor_cpu > quota * alpha` | Reconstructed overload bool |

**Decision already made:** Layers C (clustering) and D (RL state/action) are **out of scope**. Getting the *real* `target_service`/`candidate_apis`/RL `action` values requires patching TopFull's own `Detector.clustering()` / `Agent.run()`, and those calls happen on TopFull's own irregular per-thread cadence (a 2s main loop plus one ~1s thread per active cluster-agent, not phase-aligned to wall-clock seconds or to each other) — that would break the same-second-join guarantee this design exists to provide. Layers A and B stay 100% external polling, on our own clock, so every row is exactly joinable.

Explicitly out of scope:

- Mesh / per-Kubernetes-service Envoy metrics (already designed separately — [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md))
- Layers C/D (clustering, RL action) — see decision above
- `tmux capture-pane -t toprl` (stdout, not a series; stays a manual live diagnostic)
- `/thresholds` as a primary cap source — same value as `rate_config/`, used only as a cross-check if files are unreadable
- Chart pipeline / mentor plots (`mentor_charts.py` stays untouched, same as the mesh collector plan)
- Backfill of `campaign_48/` or `august_38/` — future runs only

---

## 2. Alignment mechanism (shared with mesh + resource_usage collectors)

**Problem today:** `envoy_retry_collector.py` and `resource_usage_collector.py` both timestamp "now" at loop-iteration start and then `time.sleep(interval)`. Two collectors started a few seconds apart drift apart forever — this is the exact clock-alignment caveat already logged in `METRICS-GATHERED.md` ("Charts set t=0 at that file's first poll").

**Fix:** a small helper, duplicated into each collector script (matches the existing no-shared-module convention — every collector is self-contained stdlib):

```python
def sleep_until_next_tick(interval_seconds: int) -> None:
    now = time.time()
    next_tick = (int(now // interval_seconds) + 1) * interval_seconds
    time.sleep(max(0.0, next_tick - now))

def tick_timestamp(interval_seconds: int) -> str:
    now = time.time()
    aligned = int(now // interval_seconds) * interval_seconds
    return datetime.fromtimestamp(aligned, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

Main loop becomes: `sleep_until_next_tick(interval)` → scrape → write rows stamped with `tick_timestamp(interval)` (the boundary it woke for, not completion time) → repeat.

- New `topfull_throttle_collector.py` and the mesh collector both use `interval=1` → same wall-clock second, same timestamp string, directly joinable.
- `resource_usage_collector.py` keeps `interval=5`; its ticks (`t mod 5 == 0`) are a strict subset of the 1s grid, so its rows' timestamps also exactly match rows in the 1s files.
- Scrape latency (kubectl exec, curl) no longer causes drift — a slow scrape eats into the next interval, never compounds.
- **Retrofit task:** apply the same two helpers to `envoy_retry_collector.py` and `resource_usage_collector.py` (replace their `utc_now()` + trailing `time.sleep(interval)`; CSV schemas/columns unchanged).

---

## 3. Throttle collector schema

New script: `experiments/topfull_throttle_collector.py` — same shape/conventions as `envoy_retry_collector.py` (stdlib only, injected `run_cmd`, `argparse --params`, SIGTERM handling, `unittest` tests).

### `topfull_throttle.csv` (Layer A, 1s tick)

One row per `(timestamp, api)` for the 5 Locust APIs:

```
timestamp, api, threshold, admitted_rps
```

- `threshold` ← `cat rate_config/<api>` under `proxy_dir` (`global_config.json`)
- `admitted_rps` ← parsed from `GET :8090/stats` (same `name=value/` text format `metric_collector.py` already parses for Locust)
- Derived later, not stored: `action ≈ (threshold_t/threshold_{t-1}) − 1`; `tightness = admitted_rps/threshold`

### `topfull_detect.csv` (Layer B fallback, 1s tick)

One row per `(timestamp, service)` for the services with an explicit quota override in `Detector.__init__` (`cartservice`, `currencyservice`, `frontend`, `adservice`, `productcatalogservice`, `checkoutservice`, `recommendationservice`; default quota `200` for any others tracked):

```
timestamp, service, cadvisor_cpu, quota, alpha, utilization, overloaded
```

- `cadvisor_cpu` ← same source `resource_collector.py` polls (**verify exact scrape command/format on master before coding** — see §5, our local `TopFull/` submodule mirror is missing this file)
- `quota` ← hardcoded static table: `cartservice: 1000, currencyservice: 1000, frontend: 1000, adservice: 1000, productcatalogservice: 500, checkoutservice: 1000, recommendationservice: 2000`, default `200`
- `alpha` ← `0.95` for `productcatalogservice`/`cartservice`, else `0.8` — this reconstructs only the **main-loop** `detect(0.8)` check; real calls from `apply()`/`apply_v2()` also use `0.9`, and this column makes explicit which check we approximate rather than silently guessing
- `utilization` ← `cadvisor_cpu / quota`
- `overloaded` ← `utilization > alpha`

Both files land in the run's `record_path` alongside existing CSVs, on the 1s tick grid from §2, joinable with `service_edges.csv` / `service_inbound.csv` / `resource_usage.csv` on `timestamp`.

---

## 4. Wiring into `run_scenario.py`

New YAML block, same shape as `envoy_retry_collector` / `resource_usage_collector`:

```yaml
topfull_throttle_collector:
  enabled: true
  poll_interval_seconds: 1
```

New function, mirroring `start_envoy_retry_collector` / `start_resource_usage_collector`:

```python
def start_topfull_throttle_collector(cfg: dict):
    ttc_cfg = cfg.get("topfull_throttle_collector", {})
    if not ttc_cfg.get("enabled", False):
        return
    banner("Starting TopFull throttle collector")
    master = cfg["infra"]["master_ssh_host"]
    venv = cfg["infra"]["venv_activate"]
    script = cfg["infra"].get(
        "topfull_throttle_collector_script",
        "/home/idozacharia/experiments/topfull_throttle_collector.py",
    )
    deploy_repo_script(master, "topfull_throttle_collector.py", script)
    params = {"poll_interval_seconds": int(ttc_cfg.get("poll_interval_seconds", 1))}
    write_remote_json(master, "/tmp/topfull_throttle_params.json", params)
    start_script = (
        f"#!/bin/bash\nsource {venv}\n"
        f"python3 {script} --params /tmp/topfull_throttle_params.json\n"
    )
    write_remote_script(master, "/tmp/rg_topfull_throttle.sh", start_script)
    ssh(master, "tmux new-session -d -s throttle /tmp/rg_topfull_throttle.sh")
    step("Started: TopFull throttle collector (tmux session: throttle)")
```

- Called alongside `start_envoy_retry_collector(cfg)` / `start_resource_usage_collector(cfg)` in the main loop. Both existing scripts already write into `src/logs/`, which `collect_results()` copies wholesale — no new copy step needed.
- `run_manifest.json` gains `"topfull_throttle_collector": cfg.get("topfull_throttle_collector", {})`, same pattern as the other two collectors.
- No teardown/restore needed — read-only against the proxy files/HTTP endpoint, never mutates the cluster or proxy.
- All 16 scenario YAMLs get the new block (`enabled: true`, `poll_interval_seconds: 1`) alongside the existing collector blocks.
- Add `/tmp/rg_topfull_throttle.sh` to the stale-script cleanup list in `AGENTS.md` §6.

---

## 5. Testing and open verification items

- `experiments/test_topfull_throttle_collector.py` (unittest, matches `test_envoy_retry_collector.py`): pure-function tests for the `:8090/stats`-style text parser, `read_rate_config` (file → int, injected `run_cmd`/path reader), the shared `sleep_until_next_tick` / `tick_timestamp` helpers (deterministic given a mocked `time.time()`), and CSV row writers.
- Retrofit `sleep_until_next_tick` / `tick_timestamp` into `envoy_retry_collector.py` and `resource_usage_collector.py`; add/update their tests for the new helpers.
- **Pre-implementation verification on `topfull-master`** (blocking, do before coding Layer B): read the real `resource_collector.py` (not present in our local `TopFull/` submodule mirror — likely stale/incomplete relative to master) to confirm its exact cAdvisor scrape command and output format, so `topfull_detect.csv`'s `cadvisor_cpu` column matches what the detector actually sees.

---

## Status

Implemented (2026-09-09). No campaign folder has this data yet.
