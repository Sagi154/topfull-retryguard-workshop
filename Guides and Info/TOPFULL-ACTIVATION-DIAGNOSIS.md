# Why TopFull never activates in most of our scenarios

TopFull + RetryGuard Workshop — TAU Deepness Lab · diagnosis written 2026-09-14

> **Status:** diagnosis complete, **no fix implemented yet**. Two fixes are proposed in §7; the
> decisions in §9 are still open. Verification run not yet performed (see §8 blocker).
>
> Related: [2026-09-13-s1-s2-baseline-metric-checkpoint.md](../docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md) §10 (the observation that started this),
> [2026-09-09-topfull-quota-k8s-sync-design.md](../docs/superpowers/specs/2026-09-09-topfull-quota-k8s-sync-design.md) (the S3/S4 half, already fixed),
> [2026-09-11-slo-fail-and-mu-estimator-design.md](../docs/superpowers/specs/2026-09-11-slo-fail-and-mu-estimator-design.md) (Locust `Fail` = SLO-miss, not 5xx),
> [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md), [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md).
> Held email asking Ron for his working load recipe: [EMAIL-DRAFT-RON-TOPFULL-LOAD.md](EMAIL-DRAFT-RON-TOPFULL-LOAD.md).

---

## 1. The issue we are facing

**In several of our scenarios we cannot get TopFull to do anything.** The proxy is in the request
path, the RL process is running, but the admission cap never drops below its `10000` sentinel and the
overload detector never marks any service as overloaded.

The symptom is confusing because the system *looks* overloaded from the client: on Scenario 2,
`getcart` P95 is ~2.2 s and Locust reports ~98% `Fail`. Yet at the same moment the mesh looks
perfectly healthy — inbound/outbound `5xx = 0` on all 11 services, HTTP effectively all 2xx, Envoy
`retry` counters flat at 0, and Layer B `overloaded = 0`.

So the questions were:

1. Why does TopFull not engage, when the client-visible latency clearly says the system is in trouble?
2. Is it a plumbing/config bug on our side, or a real property of our environment?
3. Which scenarios are affected, and does it invalidate any of the data we already collected?
4. Can we fix it by mimicking a load recipe that is known to work (hence the draft email to Ron), or
   do we need to change something structural?

**Answer, up front: TopFull can never activate in our *unconstrained* scenarios, at any load.** It is
not a plumbing bug and it cannot be fixed by raising Locust users — that is ruled out by measurement
in §5. The affected scenarios and a separate, already-fixed cause for S3/S4 are in §6.

---

## 2. The activation gate is CPU-only

From TopFull's own source (`TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py`,
main loop, one iteration every 2 s, lines ~283–286):

```python
    overloaded_services = detector.detect(0.8)
    if len(overloaded_services) == 0:
        print("No overloaded services")
        continue
```

If `detect()` returns an empty list, the loop `continue`s: no `Agent` is created, no RL action is
computed, and every API's threshold stays at the initial `10000` sentinel.

And `detect()` (in `overload_detection.py`) looks at exactly one thing:

```python
    def detect(self, alpha=0.9):
        ...
        for svc in list(resources.keys()):
            usage = resources[svc]
            quota = self.services[svc]['cpu']
            if svc == "productcatalogservice" or svc == "cartservice":
                target = 0.95
            else:
                target = alpha
            if usage > quota * target:
                result.append(svc)
```

That is: **per-service app-container CPU > `quota × α`**, with α = 0.8 as called from `deploy_rl.py`
and a hardcoded 0.95 for `productcatalogservice` / `cartservice`. Latency, failure rate, queue depth
and SLO misses cannot start TopFull. This is the whole door.

---

## 3. `num_agent.csv` is not dead data — it is the activation log

Our docs currently describe `num_agent.csv` as "empty / always zeros / never wired up / dead data —
ignore" ([METRICS-GATHERED.md](METRICS-GATHERED.md), [METRICS-CATALOG.md](METRICS-CATALOG.md) §8,
[TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md), [campaign_48/README.md](../experiments/results/campaign_48/README.md)).

**That interpretation is wrong.** `deploy_rl.py` writes one row per loop iteration, unconditionally:

```python
    with open(log_path + "num_agent.csv", "a") as f:
        w = csv.writer(f)
        w.writerow([len(current_agent)])
```

The file is faithfully reporting `len(current_agent)`. A run of all-zeros does not mean the
instrumentation is broken — it means **TopFull created no agent for the entire run**. The row count is
non-zero in every folder (100–550 rows), so the collector was working the whole time.

Read that way, `num_agent.csv` becomes the cheapest and most direct activation indicator we have, and
it can be evaluated retroactively on every run we have ever done:

| Dataset | Folders scanned | Runs where an agent was ever created |
|---|---|---|
| `experiments/results/campaign_48/` | 64 | **10** |
| `experiments/results/august_38/` | 38 | **8** |

Breakdown of the 10 in `campaign_48` (tick index × 2 s = elapsed seconds):

| Run | first agent | last agent | ticks with an agent |
|---|---|---|---|
| `run_topfull_retryguard_forced_recovery_run2` | 358 s | 984 s | 314 |
| `run_topfull_retryguard_forced_recovery_run3` | 448 s | 1074 s | 314 |
| `run_topfull_retryguard_interval_10s_run3` | 394 s | 1022 s | 315 |
| `run_topfull_retryguard_interval_10s_run4` | 234 s | 852 s | 310 |
| `run_topfull_retryguard_interval_20s_run3` | 344 s | 962 s | 310 |
| `run_topfull_retryguard_interval_20s_run5` | 260 s | 878 s | 310 |
| `run_topfull_retryguard_interval_60s_run3` | 188 s | 806 s | 310 |
| `baseline_topfull_no_retryguard_sustained_overload_run6` | 428 s | 428 s | **1** |
| `run_topfull_retryguard_sustained_overload_run5` | 254 s | 254 s | **1** |
| `run_topfull_retryguard_targeted_bottleneck_run6` | 506 s | 506 s | **1** |

So: **zero agents in every S1 run, every S3 / S4A / S4B run, and 20 of 24 S2 runs.** The only
sustained activations are 7 of the S5/S6 recovery runs; three more are single-tick blips.

This independently corroborates the 2026-09-13 checkpoint finding from a completely different source
(`topfull_throttle.csv`: every *fresh* Layer A scrape had `threshold = 10000`, on both S1 run20 and
S2 run17). Two unrelated signals agree that the RL admission cap never engaged.

---

## 4. Why S2 cannot fire — measured CPU vs the detector threshold

`baseline_topfull_no_retryguard_sustained_overload_run17` (600 s flat hold, 620 Locust users,
448 rps mean). `need` = `quota × α`; `short by` = `need / max CPU`.

| service | quota | α | need | max CPU | p95 CPU | max util | short by |
|---|---|---|---|---|---|---|---|
| **frontend** | 1000 | 0.80 | 800 | **737** | 698 | 0.737 | **1.09×** |
| productcatalogservice | 500 | 0.95 | 475 | 264 | 249 | 0.528 | 1.80× |
| currencyservice | 1000 | 0.80 | 800 | 328 | 264 | 0.328 | 2.44× |
| checkoutservice | 1000 | 0.80 | 800 | 317 | 267 | 0.317 | 2.52× |
| recommendationservice | 2000 | 0.80 | 1600 | 616 | 567 | 0.308 | 2.60× |
| cartservice | 1000 | 0.95 | 950 | 170 | 141 | 0.170 | 5.59× |
| adservice | 1000 | 0.80 | 800 | 169 | 77 | 0.169 | 4.73× |
| shippingservice | 1000 | 0.80 | 800 | 85 | 63 | 0.085 | 9.41× |
| emailservice | 1000 | 0.80 | 800 | 67 | 50 | 0.067 | 11.94× |
| paymentservice | 1000 | 0.80 | 800 | 41 | 31 | 0.041 | 19.51× |
| redis-cart | 1000 | 0.80 | 800 | 22 | 18 | 0.022 | 36.36× |

`frontend` is the only service anywhere near the line, and it misses by 9%.

---

## 5. Raising the load cannot fix it (ruled out by measurement)

This was the obvious first idea, and it is also what the draft email to Ron was going to ask about —
especially since TopFull's own loadgen scripts use far more users than we do
(`online_boutique_create.sh` = 620, which is what we use; `run_fig8_loadgen.sh` = 3,000;
`run_fig15_online_boutique.sh` = 23,170). But we already have the controlled comparison, because S1
runs the same cluster at exactly half our peak users:

| | S1 run20 (310 users) | S2 run17 (620 users) | change |
|---|---|---|---|
| total mean RPS | 408 | 448 | +10% |
| getcart P95 | 907 ms | 2198 ms | +142% |
| getcart mean Fail | 0.8 | 161.2 | ×200 |
| **frontend max CPU** | **727 m** | **737 m** | **+1.4%** |
| frontend p95 CPU | 695 m | 698 m | +0.4% |

**Doubling the users bought +10% throughput, +142% latency and +1.4% frontend CPU.** The system is
already fully saturated at ~410–450 rps, and frontend CPU is asymptotic at roughly 740 m — permanently
below the 800 m detector threshold. Adding users only lengthens queues.

Conclusion: on this cluster, in an unconstrained scenario, **no Locust load will ever make
`detect()` fire.** This is a structural ceiling, not a tuning problem, and it means mimicking Ron's
load recipe would not have solved it either.

---

## 6. Where the CPU actually goes — the sidecar tax

From ~450 storefront rps, the mesh carries (S2 run17, differenced Envoy counters over the 687 s span):

| direction | total |
|---|---|
| inbound across all 11 services | **3,852 rps** |
| outbound across all callers | **3,452 rps** |

Hot spots: `productcatalogservice` 1,822 rps inbound, `currencyservice` 639, `cartservice` 416,
`frontend` 400 inbound / 3,084 outbound. That is roughly **8.5× fan-out amplification** per user
request, i.e. on the order of 7,300 Envoy request-handlings per second spread over 11 sidecars on a
single 8-vCPU worker node — while all app containers together burn only ~2.8 cores.

And that CPU is invisible to the detector *by construction*. TopFull's `resource_collector.py`
(`getContainerId3()`) explicitly skips the sidecar:

```python
                containers = ob['status']['containerStatuses']
                for container in containers:
                    if 'proxy' in container['name']:
                        continue
                    result[pod_name].append(container['containerID'].split('/')[-1])
```

(Our own `resource_usage_collector.py` does the same via `SKIP_CONTAINER_NAMES = {"istio-proxy", "POD"}`,
which is why `resource_usage.csv` cannot answer the node-saturation question either.)

**This is the whole explanation for the confusing symptom set.** The queueing happens in Envoy and in
the node CPU scheduler, not inside the application containers. So we can simultaneously observe
P95 = 2.2 s, HTTP all-2xx, `5xx = 0`, `retry = 0`, and `overloaded = 0` — none of which is a
contradiction, and none of which TopFull's detector can see.

TopFull's source concedes the quota table is hand-calibrated and unfinished
(`overload_detection.py`, above the `cpu_quota` constant):

```python
"""
CPU quota in this experiment is fixed to 200mi.
Dynamic quota probing is not developed yet
"""
```

Their per-service table (frontend 1000 m, catalog 500 m, recommendation 2000 m, …) was tuned to the
paper's 5-worker-node deployment. On our single node those limits are unreachable, so **calibrating
the table to our cluster is the manual step TopFull left open, not a deviation from the paper.**

### 6a. S3 / S4 failed for a *different* reason, and it is already fixed

Scenarios 3/4 constrain a backend, so they should have fired easily. They did not (zero agents in all
six baseline runs). Cause: the campaign predates the quota↔K8s sync. `run_manifest.json` for
`baseline_topfull_no_retryguard_targeted_bottleneck_run5` shows the old absolute form and no quota
fields at all:

```json
  "scale_constraints": [
    { "deployment": "checkoutservice", "method": "cpu_limit", "cpu_limit": "100m", "container": "server" }
  ],
```

So K8s capped `checkoutservice` at 100 m while the Detector still believed its hardcoded 1000 m →
utilization read ≈ 0.09 → never above α. This is exactly the failure mode predicted in
[2026-09-09-topfull-quota-k8s-sync-design.md](../docs/superpowers/specs/2026-09-09-topfull-quota-k8s-sync-design.md).
**The code fix (2026-09-10) is merged — S3/S4 only need re-running**, and new runs will carry
`paper_cpu_quotas` / `effective_cpu_quotas` in the manifest.

### 6b. Consequence for `campaign_48`

The baseline-vs-RetryGuard comparison in `campaign_48/` was, for S1–S4, collected with TopFull's
admission controller effectively inert. That does not corrupt the Locust/mesh/CPU measurements, but it
does change what the comparison *means*: for those scenarios it is "Istio retries on vs RetryGuard",
not "TopFull + retries vs TopFull + RetryGuard". This needs to be stated explicitly wherever
`campaign_48` conclusions are drawn, including [MENTOR-UPDATE.md](mentor-update/MENTOR-UPDATE.md).

---

## 7. Proposed fixes (not implemented)

Two independent problems, two fixes.

### 7a. TopFull activation — calibrate the Detector quota to real capacity

Frontend's achievable ceiling on this cluster is ~740 m max / ~695 m p95. Setting its quota to ~750 m
puts `α × quota = 600 m` below the sustained value, so `detect()` fires steadily, `clustering()` picks
up all five storefront APIs (they all traverse `frontend`), and we get a single agent throttling the
entry — which is exactly Scenario 2's intent.

The `cpu_limit_fraction` / `topfull_run_quotas.json` machinery already does quota changes and records
them in the manifest. **Caveat:** today it moves the *K8s CPU limit* and the *Detector quota*
together, so lowering the quota would also lower real capacity. To make the detector see reality
*without* changing capacity, the two need decoupling — a small change to
[`experiments/topfull_cpu_quotas.py`](../experiments/topfull_cpu_quotas.py) plus a YAML field
(e.g. `detector_quota_fraction` alongside `cpu_limit_fraction`).

Rejected alternatives:

- **More Locust users** — ruled out by §5.
- **Lower α** (e.g. 0.65, which would fire on today's 695 m p95) — requires editing the hardcoded
  `detect(0.8)` / `detect(0.9)` calls in `deploy_rl.py` and `overload_detection.py`. It changes the
  controller rather than its mis-calibrated model of the environment. Defensible as a fallback, since
  TopFull already hardcodes 0.95 for two services, but less honest than fixing the quota.

### 7b. RetryGuard signal — retries are structurally impossible right now

`experiments/virtual-services.yaml` sets `attempts: 3` with `retryOn: "5xx,reset,connect-failure"` and
**no `perTryTimeout`**. Our overload produces *slow successes*, not 5xx, so no retry condition is ever
met — which is the real reason Envoy `retry` is 0, and why RetryGuard's `Δ5xx/Δtotal` never moves.

Adding a `perTryTimeout` well under the 1 s SLO (~500 ms) makes a slow upstream call a retriable read
timeout under Envoy's `5xx` policy, producing genuine retry amplification. This is also the more
realistic retry-storm mechanism: real storms come from client timeouts during prolonged
miscoordination, which is precisely RetryGuard's stated target, not from clean 5xx responses.

Without 7b, RetryGuard stays inert no matter what we do to TopFull.

---

## 8. Blocker for verification

None of the above has been tested on the cluster. The machine this diagnosis was written on has no
`gcloud`, no configured `~/.ssh` host aliases for `topfull-master` / `topfull-worker-1` /
`topfull-load`, and no local Python — so a verification run has to be set up first per
[CONNECT-VMS.md](CONNECT-VMS.md), or run from another machine.

Suggested verification once access exists: one S2 baseline run with 7a applied, checking
`num_agent.csv` max > 0 and `topfull_throttle.csv` fresh `threshold < 10000`. Remember to bump
`run_number` / `log_folder` first (S2 baseline YAML is currently at **run18**).

**Worth adding regardless:** a post-run gate on `num_agent.csv` max > 0 for any scenario that is
*supposed* to overload, so we never again complete a campaign in which TopFull was silently idle.

---

## 9. Open decisions

1. Implement 7a and 7b, or only one of them?
2. Correct the `num_agent.csv` description across the guides now (§3), or record it only in a dated
   spec until a re-run confirms the fix?
3. Set up SSH/gcloud on this machine for verification, or prepare the changes only?
4. Does S2 keep the `frontend` quota calibration (global entry overload, but no retry storm because
   backends stay healthy), or should the constraint move to a hot backend such as
   `productcatalogservice` (1,822 rps inbound, α already 0.95) so that both TopFull *and* RetryGuard
   have something to do in the same scenario?
5. Does the §6b caveat go into [MENTOR-UPDATE.md](mentor-update/MENTOR-UPDATE.md) before it is shared?

---

## 10. How the numbers here were produced

All figures come from files already in the repo — no new runs. CPU/α table from
`topfull_detect.csv` (`cadvisor_cpu`, `quota`, `alpha` columns) of the named run folders; Locust rows
from the per-endpoint CSVs skipping the first 30 rows (Locust spawn ramp); mesh rates by differencing
first vs last cumulative `service_inbound.csv` / `service_edges.csv` rows per service over the file
span; activation counts by reading `num_agent.csv` in every folder under both results trees.
