# TopFull throttle metrics — what exists, how to get it

TopFull + RetryGuard Workshop — TAU Deepness Lab

> How TopFull **decides** (paper + our stack), what **decision** it actually writes, the live **throttle signals** on `topfull-master`, what we already collect (and do not), and how to scrape a time series for future runs. **Wanted next:** layers A–D in [What it did vs why it throttled](#what-it-did-vs-why-it-throttled-wanted-for-future-runs) (cap/admitted, detector, cluster/candidates, RL state+action — each with a prefer-log vs fallback). Algorithm source: [TopFull.pdf](../context/TopFull.pdf) (KAIST, SIGCOMM ’24). Layer 1 Locust CSVs and the rest of the metric stack: [METRICS-GATHERED.md](METRICS-GATHERED.md). RetryGuard (a separate controller) is [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md). Why `num_agent.csv` is empty: [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md). Hardcoded CPU quotas TopFull believes (not K8s limits): [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](PER-SERVICE-MESH-COLLECTOR-DESIGN.md).

Nothing in `campaign_48/` or `august_38/` records TopFull’s actual throttle state. `num_agent.csv` was supposed to; it is zeros. You **cannot reconstruct** those counters from the finished runs. Locust `RPS` is only a proxy (completed traffic after the proxy, not the cap the RL set).

The live signals sit on **`topfull-master` while a run is going**. Two are real and easy; extras exist only as prints.

---

## What decision TopFull makes

TopFull is an **entry-level, API-wise overload controller**. It only ever throttles at the five external Locust APIs (`getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`), never inside individual Kubernetes microservices.

**The decision is one number per API: the current admitted-rate cap (req/s)** at the entry proxy. That is the value written to `rate_config/<api>` and served on `:8090/thresholds`. TopFull does not touch Istio retries, per-service priorities, or anything else. It only decides “how many req/s of this API are allowed through the gate right now,” recomputed every ~1 s, and differentiated per API based on which downstream bottleneck(s) that API is implicated in.

RetryGuard is orthogonal: TopFull decides *how much traffic gets in*; RetryGuard decides *whether failed requests get retried once they are in* (toggles Istio `retries.attempts` 3 ↔ 0 per K8s service).

---

## How TopFull makes that decision

Each control cycle (~1 s) runs four stages. Clustering happens first; load control then runs in parallel at each cluster.

### 1. Detect overloaded microservices

A collector watches every microservice’s resource utilization (cAdvisor) and API execution paths (Istio traces). A microservice is **overloaded** when utilization crosses a threshold (paper: CPU > 0.8).

### 2. Cluster APIs by shared bottlenecks

APIs that share an overloaded microservice on their execution path are grouped into the same cluster (transitively: if API1 and API2 share one overloaded service, and API2 and API3 share another, all three cluster together). Clusters that share no overloaded microservice are independent and can be solved in parallel. Clusters are recomputed every cycle as the overload set changes.

### 3. Adaptive API-wise load control per cluster

TopFull picks a **target** overloaded microservice (the one used by the fewest APIs — least likely to be disturbed by control elsewhere) and rate-limits the APIs that use it. When later *increasing* rates (recovering headroom), it only raises APIs that currently have **no** overloaded microservice anywhere on their path. That is the anti-starvation rule versus DAGOR / Breakwater, which throttle every API sharing a bottleneck equally and waste work on requests that get built at one service only to be rejected downstream.

Paper Algorithm 1 (`AdjustRate`):

```
if Action_RL > 0:          # rate increase
    targets = CandidateAPIs.HighestPriority
else:                      # rate decrease
    targets = CandidateAPIs.LowestPriority
for t in targets:
    t.rate ← t.rate · (1 + Action_RL)
```

Business priority (if assigned) means a decrease hits the lowest-priority API among those sharing the target, and an increase hits the highest-priority API.

### 4. RL agent chooses the step size

A lightweight PPO controller (RLlib) per cluster picks the **magnitude** of the change, not which API. One inference per cluster per second.

| Piece | What it is |
|---|---|
| **State** (2-dim) | (a) goodput / current rate-limit for the cluster’s candidate APIs; (b) worst end-to-end percentile latency among them |
| **Action** | continuous multiplicative step in `[-0.5, 0.5]` applied to `rate` (finer than DAGOR’s fixed ±0.05 / 0.01 — paper: ~5 s to converge vs DAGOR ~27 s) |
| **Reward** | `Δgoodput − ρ · max(0, latency − SLO)` |
| **Training** | Sim2real: pre-train on a synthetic DAG simulator, then specialize on the real app |
| **Enforcement** | Go token-bucket rate limiter at the entry proxy reads the new cap |

The Go proxy is what you scrape below. The RL / detector prints (tmux `toprl`) are the weaker “why did the cap move” signal.

---

## Throttle metrics in this project

These are the live signals on `topfull-master` **during a run**. None of them are captured in `campaign_48/` or `august_38/` — only scrapable live. Locust `RPS` is not a substitute for the cap.

| Signal | Source | Meaning |
|---|---|---|
| **Threshold** (the cap the RL set) | `rate_config/<api>` files, or `GET :8090/thresholds` | Current admitted-rate limit per Locust API (req/s). This **is** TopFull’s decision. |
| **Admitted RPS** | `GET :8090/stats` | What the proxy actually let through per API that second — not what Locust saw complete. |
| **Overloaded-service list / RL actions** | stdout of tmux session `toprl` (`deploy_rl.py`) | Printed only, not persisted — the messiest signal. |
| **Completed `RPS` / Fail / Goodput** (proxy) | Locust CSVs (already collected) | What came back to the client. Weak proxy for admitted load, **not** the cap itself. |

`num_agent.csv` was supposed to record the throttle state. It is empty / almost all zeros across every finished run and **cannot be backfilled**. Do not revive it — drain the two live sources above instead.

The collector plan (future runs only): poll `rate_config/*` and `:8090/stats` every 1–5 s, write `topfull_throttle.csv` (`timestamp, api, threshold, admitted_rps`), wire it in `run_scenario.py`. That will not backfill `campaign_48/` or `august_38/`. Details are in [How to keep this for analysis](#how-to-keep-this-for-analysis-future-runs-only).

**RetryGuard contrast.** RetryGuard is this project’s own controller, separate from TopFull. It makes a binary decision: toggle Istio `retries.attempts` (3 ↔ 0) per Kubernetes service from rejection-rate windows. See [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md). TopFull decides *how much traffic gets in*; RetryGuard decides *whether failed requests get retried once they are in*.

---

## What it did vs why it throttled (wanted for future runs)

`campaign_48/` only has Locust CSVs (plus our kubelet `resource_usage.csv`). That is the **outcome**, not the throttle. To reconstruct *why* TopFull may have throttled, future collection needs layers **A–D** below on one timeline. A 1 s kubelet scrape is **not** a substitute for Layer B — different sensor (kubelet vs cAdvisor) and different denominator (K8s CPU limit vs TopFull’s hardcoded quota in `overload_detection.py`).

### Layer A — what TopFull did (the table above)

| Signal | Example on a timeline | How to get it |
|---|---|---|
| **Threshold** | It cut `postcheckout` to 40 req/s. | Poll `rate_config/<api>` or `GET :8090/thresholds` every 1 s. |
| **Admitted RPS** | The proxy let 37 through (clamp binding, or Locust offered less). | `GET :8090/stats` every 1 s. |
| **`toprl` / RL action** | It applied −0.2 to that API. | Print from `deploy_rl.py`, **or** derive `(cap_t / cap_{t-1}) − 1` on APIs that moved. Derived step = applied change; equals the RL action only for APIs Algorithm 1 targeted that second. |
| **Locust CSVs** | What the client then saw (completed / Fail / Goodput). | Already collected. Outcome, **not** the reason. |

Without Layer A you cannot tell “TopFull clamped” from “the app died” or “Locust offered less.”

### Layer B — why it thought it should (detector, not our CPU CSV)

| Signal | Example on a timeline | How to get it |
|---|---|---|
| **Overloaded bool** | “I marked `checkoutservice` as overloaded.” | **Prefer:** log inside `Detector.detect()` each ~1 s. That boolean **is** the trigger. |
| **Utilization + quota** | “cAdvisor CPU / my quota was 0.91, and 0.91 > 0.8.” | Same detect() log: raw cAdvisor CPU, quota used, utilization. Fallback: scrape the **same** cAdvisor source `resource_collector.py` uses, plus dump the hardcoded quota dict (`cpu_quota = 200` and the per-service map). Then `util = cadvisor / quota`. Close guess — can still disagree on a given second (timing / filters). |
| **Raw CPU alone** | Our `resource_usage.csv` millicores | Weaker. Parallel measurement; not what the detector compared to 0.8. |

**Prefer `Detector.detect()`.** It is the boolean TopFull used. The cAdvisor + quota rebuild is second-best.

Put on one timeline you want: *checkout util crossed 0.8 → detector flagged checkout → cluster included `postcheckout` → RL stepped −0.2 → cap 50→40 → admitted 37 → Locust goodput fell.*

Layer A + B get you “checkout was hot → some cap moved.” The next two layers get **who** was in that decision and **how hard** the RL stepped. They are coupled: Layer D’s state is defined on Layer C’s candidate APIs. Do not treat Layer B as reconstructing Layer A — faster per-service CPU / Envoy / Locust still cannot produce `cap was 40` or `admitted 37`.

### Layer C — clustering / candidate set (who got the action)

Turns “checkout was hot” into “so we touched `postcheckout`, not `getproduct`.”

| Field | Meaning |
|---|---|
| `target_service` | Overloaded microservice picked this cycle (fewest APIs). |
| `overloaded_services` | The set that formed the cluster. |
| `apis_in_cluster` | Every Locust API sharing those overloaded services (transitive). |
| `candidate_apis` | APIs that use the target — what Algorithm 1 sees. |
| `targeted_apis` | Who actually got `rate · (1 + action)` (lowest priority on decrease, highest on increase; increase only if the path is clean). |

**Prefer:** log from the clusterer / `AdjustRate` in `deploy_rl.py` (same ~1 s cycle as `detect()`), one row per cluster. Do not parse `tmux capture-pane`.

```
timestamp, cluster_id, target_service, overloaded_services, apis_in_cluster, candidate_apis, targeted_apis
```

**Fallback** (no TopFull patch): rebuild clusters from Layer B’s overloaded bools plus a **static** Boutique execution-path table (`postcheckout` → checkout, cart, payment, …). Good enough on this app (paths barely branch). Can still disagree if TopFull’s path map or “API is on every possible branch” rule differs. You will not get `targeted_apis` unless Layer A also shows which caps moved.

### Layer D — RL state (why −0.2 rather than −0.05)

CPU / Layer B explains *that* it throttled. These two numbers explain *how hard*: high P95 or low goodput-over-cap → large negative step.

Paper state, per cluster, on the **candidate APIs from Layer C**:

- `goodput_over_cap` = (sum of candidate goodputs) / (sum of those APIs’ current caps)
- `p95_ms` = worst end-to-end percentile among candidates
- `action` ∈ `[-0.5, 0.5]` (what the PPO policy returned)

**Prefer:** log the observation the policy actually received, plus the action, from the RL infer step in `deploy_rl.py`:

```
timestamp, cluster_id, goodput_over_cap, p95_ms, slo_ms, action
```

**Fallback:** recompute the same two features from Locust `Goodput` + Layer A `threshold` + `Latency95`, **only if Layer C gave you the candidate set**. Also read the SLO constant from TopFull’s config — do not assume it. Miss the candidate set and you are averaging the wrong APIs. This reconstructs the **input** to the policy, not why the net emitted −0.20 vs −0.18 (that is the weights). State + action is enough for this project.

---

## What we already have vs what is missing

| Signal | Where it lives today | Status |
|---|---|---|
| Completed `RPS` / Fail / Goodput per Locust API | Locust CSVs from `metric_collector.py` | Collected. Weak **proxy** for admitted load. |
| `num_agent.csv` | Copied into every run folder | **Empty** (almost all zeros). Do not revive; scrape the sources below instead. |
| Admission **threshold** (cap) per Locust API | `rate_config/<api>` and `:8090/thresholds` | Live on master during a run. **Not** written to results. |
| **Admitted** RPS per Locust API | `:8090/stats` | Live on master during a run. **Not** written to results. |
| Overloaded-service list / RL actions | stdout of tmux `toprl` (`deploy_rl.py`) | Printed, not a CSV. |

Until a collector exists and you **re-run**, you do not have TopFull’s internal throttle history. Existing 48 runs stay “`RPS` as proxy.”

---

## 1. Admission cap per Locust API (the actual throttle)

TopFull’s RL writes one file per API under `proxy_dir` (`global_config.json` → typically `…/src/proxy/rate_config/`):

```
rate_config/getproduct
rate_config/postcheckout
rate_config/getcart
rate_config/postcart
rate_config/emptycart
```

Each file is a single number: **max req/s the proxy is allowed to admit for that API right now**. `overload_detection.apply_threshold_proxy()` does `echo <threshold> > rate_config/<name>` and then signals the Go process to reload.

During a live run:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ls -l /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/rate_config/; echo '---'; for f in /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/rate_config/*; do echo \"\$(basename \$f)=\$(cat \$f)\"; done"
```

---

## 2. Admitted RPS from the proxy itself

`overload_detection.current_rps()` already GETs:

```
http://<master>:8090/stats
```

Format is the same `name=value/` text as Locust. This is **how much the proxy let through** that second, per Locust API — not Locust’s completed `RPS`.

During a live run (proxy must be up):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "curl -sS http://127.0.0.1:8090/stats; echo; curl -sS http://127.0.0.1:8090/thresholds"
```

`/thresholds` is the HTTP twin of the `rate_config/` files (used in TopFull’s Train-Ticket recorder). `/stats` is admitted throughput.

---

## How the three RPS-like numbers relate

Together with Locust CSVs you already have:

| Signal | Source | Meaning |
|---|---|---|
| **threshold** | `rate_config/<api>` or `:8090/thresholds` | Cap the RL set (req/s) |
| **admitted_rps** | `:8090/stats` | What the proxy actually forwarded |
| **completed_rps / Fail / Goodput** | Locust CSVs (already collected) | What came back to the client |
| **throttle tightness** (derived) | `admitted / threshold` or `completed vs threshold` | How hard TopFull is clamping |

That last derived column is the missing “controller interaction” series.

Locust APIs here are the same five entry actions (`getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`) — not Kubernetes microservice names. See [METRICS-GATHERED.md](METRICS-GATHERED.md).

---

## 3. Overloaded-service list and RL actions (weaker)

`Detector.detect()` / `set_priority()` / `apply()` run inside `deploy_rl.py` every ~1 s. They print overloaded services and leftover actions to **stdout of tmux session `toprl`**. Nothing writes that to a CSV.

Live peek (messy, not a metric series):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "tmux capture-pane -t toprl -p"
```

---

## How to keep this for analysis (future runs only)

**Design (Layers A + B only, not yet implemented):** [2026-09-09-topfull-throttle-collector-design.md](../docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md) — a new `topfull_throttle_collector.py` that polls `rate_config/*` + `:8090/stats` (Layer A) and reconstructs the detector's overload bool from cAdvisor CPU + the hardcoded quota table (Layer B fallback), on the **same wall-clock 1s grid** as the per-service mesh collector, so any second has both a throttle snapshot and a mesh snapshot. Layers C/D (clustering, RL action) are explicitly out of scope there — see the design doc for why.

Same pattern as `resource_usage_collector.py` / `envoy_retry_collector.py`. Collect the layers in [What it did vs why it throttled](#what-it-did-vs-why-it-throttled-wanted-for-future-runs). A = what changed at the gate; B = why the detector fired; C = who was in the cluster; D = how hard the RL stepped. C and D can live in one file.

**Layer A — proxy / cap (required):**

1. New script on master, poll every 1 s (match the RL cycle; 5 s loses steps).
2. Read `rate_config/*` **and** `GET :8090/stats` (and `/thresholds` if you want a cross-check).
3. Write e.g. `topfull_throttle.csv`:

```
timestamp, api, threshold, admitted_rps
```

Derived later: `action ≈ (threshold_t / threshold_{t-1}) − 1` on APIs that moved; `tightness = admitted_rps / threshold`.

**Layer B — detector (required for “why”):**

4. **Prefer** a line from `Detector.detect()` every cycle, e.g. `topfull_detect.csv`:

```
timestamp, service, cadvisor_cpu, quota, utilization, overloaded
```

5. **Fallback** if you will not patch the detector: scrape the same cAdvisor path `resource_collector.py` uses, and snapshot the hardcoded quota dict from `overload_detection.py`. Do **not** use our kubelet `resource_usage.csv` as Layer B.

**Layers C + D — cluster and RL state (who + how hard):**

6. **Prefer** one row per cluster per cycle from `deploy_rl.py` after `detect()` → cluster → infer → `apply()`, e.g. `topfull_rl.csv`:

```
timestamp, cluster_id, target_service, overloaded_services,
apis_in_cluster, candidate_apis, targeted_apis,
goodput_over_cap, p95_ms, slo_ms, action
```

7. **Fallback** if you will not patch the RL loop: Layer C = overloaded bools (Layer B) + static Boutique path table; `targeted_apis` from Layer A caps that moved. Layer D = Locust `Goodput` / Layer A `threshold` / `Latency95` aggregated over those candidates, plus the SLO from TopFull’s config. Layer D’s fallback **requires** Layer C (or you average the wrong APIs).

8. Wire A–D in `run_scenario.py` (tmux session, copy from repo, YAML `enabled: true`). `collect_results()` already copies everything under `src/logs/`.

This only helps **future** runs — it will not backfill `campaign_48/` or `august_38/`.
