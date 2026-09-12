# Throttle metrics, collector, and quota ↔ K8s sync — 8–10 Sep 2026

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Session notes for the work that produced [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md), the Layer A/B collector, and the quota↔K8s sync. Design specs: [2026-09-09-topfull-throttle-collector-design.md](../docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md), [2026-09-09-topfull-quota-k8s-sync-design.md](../docs/superpowers/specs/2026-09-09-topfull-quota-k8s-sync-design.md). Related: [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md), [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md), [METRICS-GATHERED.md](METRICS-GATHERED.md).

---

## 1. Writing TOPFULL-THROTTLE-METRICS.md (8 Sep)

`campaign_48/` and `august_38/` have Locust outcomes (`RPS` / Fail / Goodput) but **no record of TopFull’s actual throttle**. `num_agent.csv` was supposed to hold that; it is empty / almost all zeros and **cannot be backfilled**. Locust `RPS` is completed traffic *after* the proxy — not the cap the RL set.

The guide was written to answer: what decision TopFull actually makes, how it decides (paper + our stack), which **live** signals sit on `topfull-master` during a run, and how to scrape them for **future** runs only.

### What the guide established

- TopFull is an **entry-level, API-wise** controller. It only sets an admitted-rate cap (req/s) on the five Locust APIs (`getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`). It does not touch Istio retries or per-service priorities.
- RetryGuard is orthogonal: TopFull decides *how much traffic gets in*; RetryGuard decides *whether failed requests get retried once they are in*.
- Each ~1 s cycle: detect overloaded microservices → cluster APIs by shared bottlenecks → Algorithm 1 (`AdjustRate`) picks which APIs to step → PPO picks the step size in `[-0.5, 0.5]` → Go token-bucket proxy enforces the cap.

### Live signals (not in campaign CSVs)

| Signal | Source | Meaning |
|---|---|---|
| **Threshold** (the cap) | `rate_config/<api>` or `GET :8090/thresholds` | Current admitted-rate limit per Locust API — **this is the decision** |
| **Admitted RPS** | `GET :8090/stats` | What the proxy let through that second |
| **Overloaded / RL actions** | stdout of tmux `toprl` (`deploy_rl.py`) | Printed only, not a series |
| Locust CSVs | already collected | Client-visible outcome, not the cap |

SSH one-liners for a live peek (`rate_config/`, `curl :8090/stats` and `/thresholds`, `tmux capture-pane -t toprl`) live in the guide. Do not revive `num_agent.csv` — drain the two live sources instead.

Same session also produced [PER-SERVICE-METRICS.md](PER-SERVICE-METRICS.md) (Locust is entry-API, not per Kubernetes service) and [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md) (full-mesh Envoy). Those answer a *different* question (per-service retries/goodput). Throttle metrics stay per Locust API on the master proxy.

---

## 2. Layers A–D (user update, 9 Sep)

The guide was then expanded beyond the two-signal scrape. To reconstruct *why* TopFull throttled, future collection needs four layers on **one timeline**. A 1 s kubelet scrape is **not** a substitute for Layer B (different sensor, different denominator).

| Layer | Question | Prefer | Fallback |
|---|---|---|---|
| **A** | What did TopFull do? (cap + admitted) | Poll `rate_config/` + `:8090/thresholds` + `:8090/stats` | — |
| **B** | Why did the detector fire? | Log inside `Detector.detect()` | Rebuild from the same cAdvisor source as `resource_collector.py` + quota dict — **not** `resource_usage.csv` |
| **C** | Who got the action? (cluster / candidates) | Log from clusterer / `AdjustRate` | Overloaded bools + static Boutique path table |
| **D** | How hard did the RL step? | Observation + action from the infer step | Recompute features from Locust + Layer A **only if C gave the candidate set** |

Wanted story on one second: *checkout util crossed 0.8 → detector flagged checkout → cluster included `postcheckout` → RL stepped −0.2 → cap 50→40 → admitted 37 → Locust goodput fell.*

**Decision:** implement A + B only as an external collector. Real C/D need patches inside TopFull (`clustering()` / `Agent.run()`) on TopFull’s own irregular thread cadence — that would break a same-second join with the mesh collector. `tmux capture-pane` stays a manual diagnostic.

---

## 3. Throttle collector design + implementation (9 Sep)

Constraint from the user: the 1 s “cycles” must match the mesh collector’s cycles so any given second has **both** a throttle snapshot and a mesh snapshot. CPU can stay 5 s if those ticks are a subset of the 1 s grid.

Spec: [2026-09-09-topfull-throttle-collector-design.md](../docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md). Implemented on `feat/topfull-throttle-collector`.

### Alignment

`sleep_until_next_tick` / `tick_timestamp` (floor to wall-clock interval, stamp the boundary, not scrape-completion time). Duplicated into:

- new `experiments/topfull_throttle_collector.py` (1 s)
- `envoy_retry_collector.py` (mesh poll bumped to 1 s)
- `resource_usage_collector.py` (stays 5 s; `t mod 5 == 0` is a subset of the 1 s grid)

That closed the “each file’s t=0 is its first poll” drift already noted in [METRICS-GATHERED.md](METRICS-GATHERED.md).

### What the collector writes

- **`topfull_throttle.csv` (Layer A):** `timestamp, api, threshold, admitted_rps` — five Locust APIs.
- **`topfull_detect.csv` (Layer B fallback):** `timestamp, service, cadvisor_cpu, quota, alpha, utilization, overloaded` — reconstruct `detect()` from cAdvisor `/api/v2.0/summary` + the paper quota/α tables. Prefer-detect() patch was not done.

Wired into `run_scenario.py` (tmux session `throttle`, copy script from repo) and all 16 scenario YAMLs (`enabled: true`, 1 s). `mentor_charts.py` was left untouched. Campaign folders were not rewritten.

Hardening that followed the first wiring: `poll_once` always writes rows on scrape/write errors; leftover `throttle` tmux sessions are killed on start/stop.

---

## 4. Quota ↔ K8s sync (9–10 Sep)

S2 RetryGuard run7 showed a real mismatch: Kubernetes still had leftover **checkout 100m**, while Detector used **quota 1000**. Layer B never saw overload. Spec: [2026-09-09-topfull-quota-k8s-sync-design.md](../docs/superpowers/specs/2026-09-09-topfull-quota-k8s-sync-design.md).

Paper table is baseline; S3/S4 use **one** `cpu_limit_fraction: 0.1`; the runner keeps K8s and Detector on the same numbers. Locust user counts were not auto-adjusted.

Implemented on `feat/topfull-quota-k8s-sync` (off the throttle-collector branch), then fast-forwarded into `feat/topfull-throttle-collector` (`fa0d795`). Feature branch and worktree deleted after the local merge.

1. Paper quota module + fraction helpers + tests (`experiments/topfull_cpu_quotas.py`).
2. Runner applies `cpu_limit_fraction` (absolute `cpu_limit:` in YAML is rejected).
3. Reconcile Boutique CPU to paper **before and after** each run.
4. Write `topfull_run_quotas.json`, patch Detector, record paper vs effective in the manifest.
5. Layer B `quota_for` uses that map (never default 200).
6. S3/S4 YAMLs + docs (`experiments/README.md`, [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md), [SCENARIOS-GUIDE.md](SCENARIOS-GUIDE.md), `AGENTS.md`, [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md)).

Effective bottlenecks: S3/S4B **100m**, S4A **50m** (not comparable to `campaign_48` S4A at absolute 100m).

---

## 5. Integrate onto `main` and Layer A scrape fix (10 Sep)

- Repo default is **`main`**, not `master`.
- Updated the throttle branch with `main`, then merged throttle **into `main`**.
- Run7 Layer A (`topfull_throttle.csv`) was **all zeros**: `rate_config/` files are consume-deleted after the proxy applies them, and `global_config.json`’s `proxy_url` is the GCE Locust path (500s / timeouts), not the scrape target.
- Fix (`e5bb1a5`): read live caps from **`GET /thresholds`**, scrape **`127.0.0.1:8090`**, short timeout / bypass `HTTP_PROXY`. Files under `rate_config/` remain a fallback.
- **Correction (S2 run9):** that localhost + `ProxyHandler({})` path was wrong — `:8090` is goproxy, so admin GETs must go *through* the proxy (`ProxyHandler` → `127.0.0.1:8090`, request `proxy_url + "/stats"`). Direct loopback GETs are the run9 Layer A all-zeros failure mode.
- On **`origin/main`** at `b41decd`. Tests passed.
- **S2 run10:** via-proxy scrape worked when it answered (`threshold=10000`, non-zero `admitted_rps`), but ~87% of ticks timed out at 0.8 s and wrote zeros — sequential `/thresholds` then `/stats` also stalled Layer B.
- **2026-09-11:** parallel `/thresholds` + `/stats` + Layer B; **last-good carry** with `threshold_fresh` / `admitted_fresh` columns. Empty `rate_config/` is no longer treated as a measured cap of 0. A longer-wait background `/stats` thread is **not** implemented (next lever if `admitted_fresh==1` stays sparse).

---

## Housekeeping (not product work)

Git Changes on `main` included leftover WIP (throttle-collector plan markdown, an S2 run7 pull, a stash from the merge). Six “background terminals” were hung agent shells from a stuck PowerShell/`git` session; they were aborted. They were not holding a scenario, SSH session, or collector.

---

## Current status

| Piece | Status |
|---|---|
| [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md) | Inventory + Layers A–D + live SSH commands |
| Collector Layers A + B | Implemented, wired, on `main` / `origin/main` |
| Clock alignment (mesh + CPU) | Implemented |
| Quota ↔ K8s sync | Implemented; S3/S4 use fraction 0.1 |
| Layer A scrape (via goproxy, not direct loopback) | Fixed after run9 zeros |
| Layer A parallel + last-good + freshness flags | Implemented (2026-09-11); verify on S2 run11 |
| Background `/stats` side thread | **Not** implemented — follow-up if admitted stays sparse |
| Layers C/D | Still out of scope (would need TopFull patches) |
| `campaign_48/` / `august_38/` | Not rewritten; still no throttle/detect CSVs |
| Charts | `mentor_charts.py` does not read the new files |

The next new run is the first that should have matching K8s/Detector quotas **and** a usable Layer A series (last-good under timeout storms), joinable on the 1 s wall-clock grid with mesh + (every 5 s) CPU.
