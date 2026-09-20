# Migrating our TopFull/Online Boutique setup onto Ron Nezer's setup as the base (2026-09-20)

TopFull + RetryGuard Workshop — TAU Deepness Lab

> We copied Ron Nezer's three VMs and Kubernetes cluster, but built a
> separate, paper-quota-based experiment configuration on top of them
> ([RON-NEZER-SETUP-VS-WORKSHOP.md](../../../Guides%20and%20Info/RON-NEZER-SETUP-VS-WORKSHOP.md)).
> This doc proposes making **his setup the base** instead — his CPU
> table, replica counts, Deployment resources/probes, cluster manifests,
> and (later) loadgen mix — while keeping our own metrics/RetryGuard
> instrumentation layered on top, unchanged. **Nothing in this doc has
> been applied to `run_scenario.py`, `experiments/configs/`, the
> `idozacharia` TopFull tree, or the live cluster — this is a design
> proposal**, reached via an interactive grilling session (this doc is
> the write-up of that session's settled decisions plus the archaeology
> that grounds them).
>
> **The core numeric input (§4) is explicitly provisional, pending a
> reply from Ron Nezer himself** about which of several inconsistent
> on-disk artifacts (§3) reflects what was actually live when he
> observed TopFull engage. Everything else in this doc (mechanism,
> structural fixes, what stays ours) does not depend on his answer and
> can be acted on now.

Related: [RON-NEZER-SETUP-VS-WORKSHOP.md](../../../Guides%20and%20Info/RON-NEZER-SETUP-VS-WORKSHOP.md),
[RON-TOPFULL-ACTIVATION-QUESTION.md](../../../Guides%20and%20Info/RON-TOPFULL-ACTIVATION-QUESTION.md),
[EMAIL-DRAFT-RON-TOPFULL-LOAD.md](../../../Guides%20and%20Info/EMAIL-DRAFT-RON-TOPFULL-LOAD.md),
[2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md](2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md)
(layer (d) below; that doc's own capacity numbers are themselves invalidated by this migration — see §8),
[2026-09-09-topfull-quota-k8s-sync-design.md](2026-09-09-topfull-quota-k8s-sync-design.md)
(the mechanism §5 generalizes),
[experiments/capacity/README.md](../../../experiments/capacity/README.md)
(frozen-μ calibration data that becomes historical once this lands — see §8),
`AGENTS.md` §4 (current status).

---

## 1. Decision summary

| # | Decision | Answer |
|---|---|---|
| 1 | Scope of "base" | **All four layers** — (a) cluster manifests, (b) Detector CPU table + replica counts, (c) Boutique Deployment resources/probes/images, (d) loadgen mix/weights/duration — count as base. Layer (d)'s specifics deferred (§8). |
| 2 | Whose tree is canonical | **Ours.** Port his *values* into `/home/idozacharia/TopFull`; do not repoint `run_scenario.py` at `/home/user/TopFull`. |
| 3 | HPA | **Adopt the mechanism**, capacity-adjusted (`maxReplicas: 4`, not his 20 — see §4). `productcatalogservice` HPA left disabled for now (conflicts with S4A — deferred, §8). |
| 4 | Capacity ceiling | GCP quota increase not available now → **scale his numbers down to fit our node** (§4). |
| 5 | Custom images | **Keep stock paper images** (`qkrwogud676/...`), not `ronnezer/*` — his images strip health probes, which is a confound for a project measuring overload/retry behavior. |
| 6 | Existing dataset | **Treat `campaign_48/` and the frozen-capacity calibration as a separate, historical "paper-config regime."** Plan a fresh campaign + recalibration once this migration lands, rather than running it in parallel as a side-track. |
| 7 | What stays ours | RetryGuard controller + its VirtualServices `retries`/`perTryTimeout` patch, `envoy_retry_collector.py`, `resource_usage_collector.py`, `topfull_throttle_collector.py`, multi-user infra fixes, Locust 2.x API compatibility, `metric_collector.py` crash-guard, dynamic cAdvisor IP lookup, all `run_scenario.py`/`pull_results.py`/`rho_*` tooling. See §6/§8. |
| 8 | Which of Ron's capacity snapshots | **The later, bigger family** — big HPA (`maxReplicas=20`) + `compute-resources.yaml` (2025-09-20), then the Detector table rewrite + `instance_scaling.py` scale-up (2025-12-05), then the final CPU-bumped Deployment YAML (2026-01-16) — not the smaller, earlier `frontend-hpa.yaml` (`maxReplicas=2`, 2025-08-14). |
| 9 | HPA vs. S4A (`productcatalogservice`) conflict | **Deferred** — part of the S1–S6 scenario-methodology rework, not solved here. |
| 10 | Extra items outside the 4 buckets | Proxy Host-match change (`proxy_online_boutique.go`) and OS/pip/`WALinuxAgent` changes: **adopted by default** (small, unambiguous, already on-disk from the VM copy for the OS ones). `metrics-server hostNetwork: true`: **investigated, not adopted** — no artifact found anywhere (§7). |
| 11 | Detector-table vs. real K8s CPU mismatch | Rebuild the Detector table to **always match live K8s limits**, structurally, via a generalized (always-on, not just S3/S4) version of the quota-sync mechanism (§5). |
| 12 | Frontend replica ceiling | **4** (via HPA `minReplicas: 1, maxReplicas: 4`), CPU-per-replica trimmed to fit (§4). |

---

## 2. Why "Ron's setup" isn't one static config — the archaeology

Before committing real engineering time to porting specific numbers, we audited what's actually on disk in `/home/user/` on `topfull-master`/`topfull-load` (his original account, still present since we inherited his VM disks). Four independent findings, in the order we found them:

### 2a. Two different HPA files, one month apart

| File | `maxReplicas` | Last modified |
|---|---|---|
| `/home/user/frontend-hpa.yaml` | 2 | 2025-08-14 |
| `.../TopFull_master/.../deployments/hpa.yaml` | 20 | 2025-09-20 |

The August file is a smaller, earlier iteration. The September one is bigger, and it's the start of a chain of increasingly-large, later-dated artifacts: `instance_scaling.py`'s `[8,1,1,...]` and the Detector's rewritten CPU table (`overload_detection.py`) are dated **2025-12-05** — about 2.5 months *after* the September HPA/quota files, not the same day — and the final CPU-bumped Deployment YAML (§3) is dated **2026-01-16**, six weeks after that. So "the September family" is really shorthand for "the September→December→January chain," all bigger than the August snapshot and all superseding it — hence decision 8 above.

### 2b. A namespace ResourceQuota that's mathematically incompatible with his own other numbers — but was actively, iteratively tuned, not abandoned

`/home/user/compute-resources.yaml` (also dated 2025-09-20):
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-resources
spec:
  hard:
    requests.cpu: "2600m"
    limits.cpu: "2600m"
```
2600m total for the *entire namespace* is incompatible with even one service at his numbers (`checkoutservice` alone was set to 4500m in the Detector table). Initially we assumed this was an abandoned early experiment. `.bash_history` shows otherwise — a long, repeated cycle:
```
vi compute-resources.yaml
kubectl create -f ./compute-resources.yaml --namespace=default
kubectl describe resourcequota compute-resources
...
kubectl delete resourcequota compute-resources -n default
vi compute-resources.yaml
kubectl apply -f ./compute-resources.yaml --namespace=default
```
repeated at least 4 times across the retained history window, **interleaved with `fcpu`/`pcpu` invocations** (§2c). He was actively probing where frontend gets throttled/rejected against a quota he kept editing — not running a fixed config.

### 2c. Frontend/productcatalog CPU wasn't a file value at all — it was live-patched via shell functions, dozens of times, across a huge range

`.bashrc` defines `fcpu()`/`pcpu()` as shell functions that `kubectl patch`/`kubectl scale` the **running** Deployments directly (plus simpler aliases `fcpureq`/`pcpureq`/`fcputil`/`pcputil` to read back current values). `.bash_history` (capped at `HISTFILESIZE=2000`, so earlier sessions may already be lost) shows frontend CPU patched to, at various points: **100, 200, 300, 350, 400, 450, 1900, 2000, 2300, 2400, 2600, 3000** millicores; productcatalog to **0, 200, 300, 600, 700**. There is no record of which value was live at any specific "this is when it worked" moment.

### 2d. The Detector's own CPU table disagrees with the real K8s Deployment YAML, for 4 of 7 tracked services

Read directly from the live files (not paraphrased):

| Service | Detector table (`overload_detection.py`, mtime 2025-12-05) | Real K8s `requests=limits` (`online_boutique_original_custom.yaml`, mtime 2026-01-16) | Match? |
|---|---|---|---|
| frontend | 1500m | 1500m | ✅ |
| adservice | 1500m | 1500m | ✅ |
| currencyservice | 1000m | 1000m | ✅ |
| recommendationservice | 1000m | 1500m | ❌ |
| productcatalogservice | 1000m | 2000m | ❌ |
| cartservice | 300m | 2500m | ❌ (8×) |
| checkoutservice | **4500m** | **800m** | ❌ (inverted, 5.6×) |

The code's own comment, directly above the Detector's hardcoded values, states the intent: *"it should match CPU quota unit in yaml files of benchmark applications"* — so this is a **drift bug relative to KAIST's own stated design**, caused by the YAML being edited six weeks after the Detector table and never synced back. This is exactly the class of bug our own quota-sync mechanism (§5) already exists to prevent for our scenarios — his setup never had an equivalent, so it accumulated this drift silently.

### 2e. No independent notes exist

Only `/home/user/TopFull/README.md` (unmodified upstream) was found under `/home/user/` — no results log, no "here's what worked" note. `.bash_history`'s 2000-line cap means we cannot see the full ~5-month exploration (Aug 2025 → Jan 2026) that produced these files.

**Conclusion:** there is no single frozen "Ron's setup" recoverable from disk. What we have is the resting state of a long, hands-on tuning process. We chose a specific, defensible, fully-traceable reading of it (§4) rather than either guessing further or blocking on his reply.

---

## 3. Source of truth for CPU numbers (provisional pending Ron)

**Decision: `online_boutique_original_custom.yaml` (the January file, `checkoutservice: 800m`) is the frozen numeric source**, not the Detector table and not the ResourceQuota. Rationale: it's the single most recent, internally self-consistent artifact (all 11 services in one file), it's what actually governs real pod behavior regardless of what any other table believes, and the code's own comment (§2d) says the Detector table is supposed to derive from it anyway.

Full per-replica values from that file (all `requests == limits`, confirmed by direct read):

| Service | CPU (request=limit) |
|---|---|
| frontend | 1500m |
| checkoutservice | 800m |
| recommendationservice | 1500m |
| productcatalogservice | 2000m |
| cartservice | 2500m |
| currencyservice | 1000m |
| shippingservice | 1000m |
| redis-cart | 700m |
| emailservice | 200m |
| paymentservice | 200m |
| adservice | 1500m |

Ron's `instance_scaling.py` snapshot: `[8,1,1,1,1,1,1,1,1,1,1]` in service order `frontend, recommendationservice, currencyservice, paymentservice, productcatalogservice, shippingservice, redis-cart, emailservice, checkoutservice, adservice, cartservice` — i.e. only `frontend` gets scaled, to ×8.

**When Ron replies:** if he confirms a different frontend/productcatalog number (from the `fcpu`/`pcpu` range in §2c) or a different quota regime, only this section's table and §4's arithmetic need to be redone — §5/§6/§7/§8 are unaffected.

---

## 4. Fitting it on our hardware

### 4a. Why we can't just use his numbers as-is

- GCP `CPUS_ALL_REGIONS` quota in `us-central1` for this project is **32**, and our three VMs (`topfull-load` e2-standard-8, `topfull-master` e2-standard-8, `topfull-worker-1` e2-standard-16) already sum to exactly 32 — **no headroom to grow any VM without a quota-increase request**, which is not currently viable (decision 4).
- `topfull-worker-1` (e2-standard-16) has **16 vCPU / 62Gi** allocatable.
- His actual numbers — `instance_scaling=[8,1,...]` (frontend ×8) against the §3 table — sum to **23,400m** just for app containers at full scale-out (frontend `8×1500m = 12,000m` + the other 10 services' `11,400m`), before counting Kubernetes/Istio overhead at all. That's already ~1.46× our node's raw 16,000m capacity. Even the reduced frontend×4 ceiling we settle on below (§4c) only brings it down to **17,400m** (`4×1500m = 6,000m` + the same `11,400m`) — still ~1.3× the real ~13,350m app budget computed next (§4b), which is why §4d's uniform trim is needed on top of the replica-count cut, not instead of it.

### 4b. Real budget on the node

| Item | CPU (millicores) |
|---|---|
| Node allocatable | 16,000 |
| − system daemons (`cadvisor` 400 + `istiod` 500 + `calico-node` 250 + `metrics-server` 100) | −1,250 |
| − istio-proxy sidecars, ~100m request × 14 pod instances (4 frontend + 10 others) | −1,400 |
| **= app-container budget** | **≈ 13,350** |

### 4c. Frontend replica ceiling: 8 → 4

Decision 12: cap frontend at **4** replicas via HPA (`minReplicas: 1, maxReplicas: 4` — replacing his `maxReplicas: 20`), not a fixed count, so we keep his *mechanism* (adaptive scale-out under CPU pressure) rather than silently hardcoding a number. `productcatalogservice` HPA stays **disabled** (fixed ×1) — deferred per decision 9.

At full scale-out (all 4 frontend replicas up), total app-container demand:
```
4 × 1500 (frontend) + 800 (checkout) + 1500 (recommendation) + 2000 (product)
+ 2500 (cart) + 1000 (currency) + 1000 (shipping) + 700 (redis) + 200 (email)
+ 200 (payment) + 1500 (ad)
= 6,000 + 11,400 = 17,400m
```

### 4d. Uniform trim to fit the budget

`13,350 / 17,400 ≈ 0.767` (~77%), applied uniformly to every service's CPU number:

| Service | Ron's YAML value | **Trimmed working value** |
|---|---|---|
| frontend (×1–4 replicas) | 1500m | **1150m** |
| checkoutservice | 800m | **615m** |
| recommendationservice | 1500m | **1150m** |
| productcatalogservice | 2000m | **1535m** |
| cartservice | 2500m | **1920m** |
| currencyservice | 1000m | **770m** |
| shippingservice | 1000m | **770m** |
| redis-cart | 700m | **540m** |
| emailservice | 200m | **155m** |
| paymentservice | 200m | **155m** |
| adservice | 1500m | **1150m** |

Sum at full scale-out (4× frontend): `4×1150 + 615+1150+1535+1920+770+770+540+155+155+1150 = 4,600 + 8,760 = 13,360m` — fits the ≈13,350m budget.

**Caveats, explicit:**
- This is a uniform haircut, not a judgment call about which service most needs to keep its real number (e.g. `checkoutservice` ends up at 615m — *below* even his own 800m, let alone the Detector table's 4500m belief). If a later scenario specifically needs `checkoutservice` to keep more headroom, this is the first place to special-case rather than re-deriving the whole trim.
- This entire table is superseded the moment Ron replies with different real numbers (§3) — only the arithmetic method (compute budget, trim proportionally) carries forward, not these specific millicore values.

---

## 5. Structural fix: permanent quota-sync, not a two-places-hardcoded table

Decision 11 generalizes what already exists for S3/S4 scenario-time constraints
([2026-09-09-topfull-quota-k8s-sync-design.md](2026-09-09-topfull-quota-k8s-sync-design.md)):
the Detector's CPU table should **always** be derived from the live K8s Deployment CPU limit for that service, for every scenario, not just when a scenario deliberately constrains one service. This makes the exact bug found in §2d (checkout 4500m-believed vs. 800m-real) structurally impossible to reintroduce, regardless of whether our numbers ever drift from Ron's again. Concretely: `run_scenario.py`'s existing `topfull_run_quotas.json` overlay mechanism stops being S3/S4-conditional and becomes unconditional — every run writes the live map, and the Detector always reads it.

---

## 6. What stays ours, unconditionally (decision 7)

None of the following depend on which TopFull "recipe" is running underneath — keep as-is:

- **RetryGuard controller** (`experiments/retryguard.py`) and its VirtualServices `retries`/`perTryTimeout` patch.
- **`envoy_retry_collector.py`** (mesh `service_edges.csv`/`service_inbound.csv`).
- **`resource_usage_collector.py`**.
- **`topfull_throttle_collector.py`** (its `quota` column now tracks the *generalized* live map from §5, not a stale hardcoded table — an improvement, not a behavior change from our side).
- **Multi-user infra fixes** on `topfull-master`: per-user `~/.kube/config` copy, `chmod o+w` on `experiments/`/`src/logs/`, the `go` → `/usr/local/bin` symlink. These are about *which Linux account* runs the tooling, entirely orthogonal to the TopFull recipe axis.
- **Locust 2.x event API** (`events.request` vs. deprecated `request_success`/`request_failure`) — a version-compatibility fix, not an experimental-design choice.
- **`metric_collector.py`'s try/except crash-guard** ("waiting for traffic" instead of crashing on an empty window).
- **Dynamic cAdvisor IP lookup** (`getcAdvisorIP()`) — already present in our tree; Ron's version does something similar independently, no conflict.
- **All analysis/orchestration tooling**: `run_scenario.py`, `pull_results.py`, `rho_estimate_report.py`, `capacity_frozen.py`/`rho_frozen_report.py` — the *tools* are reusable as-is; the *data* they've already produced (`campaign_48/`, `experiments/capacity/capacity_frozen.json`) becomes historical per decision 6 and needs a fresh run under the new regime, not a code change.

---

## 7. What this migration adopts without further decisions (decision 10)

- **Proxy Host-match change**: `proxy_online_boutique.go` in Ron's tree drops Host-header matching on `GET /cart` and `GET /product/*`. This is a real code diff that needs to be ported into our `/home/idozacharia/TopFull` clone's copy of the same file — concrete action item, not yet done.
- **OS/dependency layer** (unpinned pip packages, removed `WALinuxAgent`): already present on our VMs, since we inherited his disk images wholesale — no action needed, just don't revert them.
- **`metrics-server hostNetwork: true`**: investigated per decision 10's request — **no supporting artifact found anywhere** (no manifest file under `/home/user/` at any depth excluding vendored dirs, no `.bash_history` hits, and the live `metrics-server` Deployment today does not have it set). Unlike the ResourceQuota (§2b), which we could at least confirm was real-but-unstable, this one has zero corroboration. **Not adopted.**

---

## 8. Explicitly deferred — not decided in this doc

- **S1–S6 scenario methodology rework.** Our S3/S4 "targeted bottleneck" scenarios used `cpu_limit_fraction` as a solution shaped around our own (paper-quota) setup; that mechanism's *meaning* needs to be rebuilt against Ron's numbers (decision 3's note). Separately, `productcatalogservice`'s HPA (disabled per §4c) directly conflicts with S4A's premise that productcatalog is a fixed, non-compensating bottleneck (decision 9) — whether to re-enable HPA there and treat compensation as a finding, pick a different S4A target, or something else, is future work.
- **Loadgen layer (d) specifics** — task-weight remix (checkout 50→500, getcart 30→100, etc.), `GETPRODUCT=600`, dropped `-t 15m` cutoff, and the split-cart `frontend.sh` launcher (separate Locust swarms per tag instead of one merged `$CART` swarm) are all "adopt eventually" per decision 1, but not designed here. Note this also **invalidates the capacity numbers** in [2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md](2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md), which were calibrated against the paper-quota regime (`capacity_frozen.json`) — that doc's §4 numbers need to be redone once this migration's CPU numbers are final, not reused as-is.
- **Fresh campaign + recalibration plan** (decision 6) — once §4's numbers stop being provisional (Ron replies, or we decide to proceed on the current best-effort table regardless), the frozen-capacity calibration battery (`experiments/capacity/capacity_frozen.json`) needs to be re-run from scratch under the new regime, and a new campaign planned to replace `campaign_48/` as the primary Phase 7 dataset. Neither the calibration battery nor a new campaign has been scheduled by this doc.
- **Exact concrete file diffs** to apply §4's numbers and §4c's HPA into the live cluster/`idozacharia` tree (which YAML/manifest to edit, how `run_scenario.py` should apply the new Detector-table-sync from §5 on every run rather than just S3/S4) — this doc specifies *what* the numbers and mechanism should be, not the line-by-line patch; that's implementation, to be done as a separate follow-up once this design is confirmed.

---

## 9. What happens when Ron replies

Only §3 (source-of-truth table) and §4 (the arithmetic derived from it) are provisional. If his answer gives different real numbers (e.g. one of the `fcpu`/`pcpu` values from §2c, or a different quota regime entirely):
1. Replace §3's table with the confirmed values.
2. Rerun §4's budget/trim arithmetic (same method, same 16 vCPU / overhead / ~13,350m budget, same frontend×4 ceiling unless he indicates otherwise) against the new source numbers.
3. Everything else in this doc (§1 decisions 1–3, 5–7, 9–11, and §5's structural quota-sync generalization) is unaffected and doesn't need to be revisited.

---

## 10. Concrete implementation checklist (designed here, not yet executed)

**This is the actual to-do list for carrying out the migration this doc designs.** §3–§7 specify *what* should change; this section is *where*. None of these edits have been made — writing this spec did not touch any of them (see §11).

| # | File / target (on `/home/idozacharia/TopFull` unless noted) | Change |
|---|---|---|
| 1 | `TopFull_master/online_boutique_scripts/src/overload_detection.py` | Per §5: stop hardcoding the Detector's per-service `cpu` table. Make it read the live map `run_scenario.py` already writes (`topfull_run_quotas.json`, currently S3/S4-conditional) unconditionally, every run, for every service. |
| 2 | `experiments/run_scenario.py` | Generalize the quota-sync overlay call (§5) so it runs on every scenario, not only when `scale_constraints` is set. Add a step to apply the §4d CPU table to the live Boutique Deployments at run start (or bake it into the base manifests — see #3). |
| 3 | Live Boutique Deployments (`kubectl` manifests, or wherever they're currently applied from) | Patch `resources.requests.cpu`/`resources.limits.cpu` to the §4d trimmed values for all 11 services. **Do not** touch the images or probes fields — decision 5 keeps our stock `qkrwogud676/...` images and existing readiness/liveness probes; only the CPU numbers come from Ron's file. |
| 4 | New `frontend` HPA manifest | Create and apply per §4c: `minReplicas: 1, maxReplicas: 4`, target 85% CPU utilization (same shape as Ron's `deployments/hpa.yaml`, just a lower ceiling). `productcatalogservice` HPA: do **not** create yet (deferred, decision 9). |
| 5 | `instance_scaling.py`-equivalent logic (wherever our tree currently pins replica counts, e.g. the `[2,1,1,...]` snapshot noted in `AGENTS.md` §2) | `frontend`'s replica count becomes HPA-managed (#4), so anything that currently force-sets it to a fixed number at run start needs to stop doing that for `frontend` specifically, or it will fight the autoscaler. Other 10 services stay pinned at ×1, unchanged. |
| 6 | `proxy_online_boutique.go` | Port the Host-match drop on `GET /cart` and `GET /product/*` from Ron's copy (§7). |
| 7 | Namespace `ResourceQuota` | No manifest to create — decision 4/§2b explicitly does **not** adopt his 2600m quota. |
| 8 | OS/pip packages, `WALinuxAgent` | No action — already present from the inherited VM disk image (§7); this row exists only so it isn't mistaken for a missed step. |
| 9 | `ronnezer/*` images, `metrics-server hostNetwork` | No action — explicitly rejected (decisions 5 and 10). |

Suggested order: #1+#2 together (they're the same mechanism), then #3+#4+#5 together (capacity change is one atomic step — deploying new CPU limits without the HPA ceiling, or vice versa, risks an intermediate state that either can't schedule or silently over-provisions), then #6 independently (no dependency on the others). Validate each step against `kubectl describe node topfull-worker1` (should show ≤ the §4b budget) before moving to the next.

## 11. What this design-writing session did not do

To be clear about what *this conversation* touched vs. what #1–#6 above still require:

- Did not modify `TopFull/` (submodule), `/home/idozacharia/TopFull` on the live VMs, `run_scenario.py`, or any `experiments/configs/*.yaml` — the checklist above is **future work**, not already-applied changes.
- Did not SSH into or change anything on `topfull-master`, `topfull-worker-1`, or `topfull-load` (all commands run during this session were read-only: `kubectl get/describe`, `cat`, `find`, `grep`, `stat`, `gcloud ... list/describe`).
- Did not resolve the S3/S4 constraint-mechanism rework or the S4A/HPA conflict (§8).
- Did not touch `campaign_48/`, `august_38/`, or any `experiments/capacity/` calibration data.
- Did not decide the loadgen mix/weights/duration (layer (d) specifics) — only that they are in scope for a later pass.
