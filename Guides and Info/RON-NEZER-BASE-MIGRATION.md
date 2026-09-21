# Migrating to Ron Nezer's setup as the experiment base (2026-09-20 → 2026-09-21)

> **One-line summary:** we had copied Ron Nezer's three VMs but built our own paper-quota, 1-replica experiment configuration on top of them instead of running his recipe. We decided to make his setup the base — porting his CPU/replica/loadgen values into our own tree — while keeping all of our own metrics/RetryGuard instrumentation unchanged. The CPU/replica/HPA layer and the loadgen shape layer are **done**; the loadgen numbers and S1–S6 methodology rework are **not** (tracked separately).

This doc is the narrative summary of the migration: where we diverged from Ron, what we changed to close that gap, what we deliberately did not adopt, and what's still open. For the detailed archaeology, arithmetic, and task-by-task diffs, follow the links in each section — this doc does not repeat their content.

---

## 1. Why this happened

[RON-NEZER-SETUP-VS-WORKSHOP.md](RON-NEZER-SETUP-VS-WORKSHOP.md) (2026-09-20 audit) found that "we copied his working TopFull environment" was only true of the **hardware**: three GCP VMs, kubeadm Kubernetes cluster, Istio, Online Boutique, cAdvisor. The **experiment recipe** running on top of that hardware was our own, separately built at `/home/idozacharia/TopFull` — stock KAIST quotas, 1 replica per service, no HPA, the merged-cart Locust launcher, stock Boutique images. Ron's actual recipe (a different Detector CPU table, HPA, custom images, a different loadgen mix) was still sitting unused on disk at `/home/user/` on the same VMs, never pointed at by `run_scenario.py`.

Once this was found, the team decided (rather than just noting the gap) to make Ron's setup the **experiment base** going forward, with our instrumentation layered on top — see [ADR-0001](../docs/adr/0001-ron-setup-as-experiment-base.md).

---

## 2. Where we differed from Ron (the audit)

Full detail: [RON-NEZER-SETUP-VS-WORKSHOP.md](RON-NEZER-SETUP-VS-WORKSHOP.md).

All three TopFull checkouts on the VMs are the same upstream git commit (`kaist-ina/TopFull` `0c7af21`) — nothing was forked. The differences are all uncommitted local patches, in three separate trees:

| Tree | Where | What it is |
|---|---|---|
| KAIST upstream | This repo's `TopFull/` submodule | Clean paper scripts |
| Ron's clone | `/home/user/TopFull` | His 2025–2026 experiment setup, never used by our runner |
| Workshop clone | `/home/idozacharia/TopFull` | What `run_scenario.py` actually drove |

Concretely, four layers of divergence:

1. **Cluster manifests** — Ron had a namespace `ResourceQuota` (2600m), HPA YAMLs for `frontend`/`productcatalogservice`, and `metrics-server hostNetwork: true`. None of these were on the live cluster; only Istio's own `istiod` HPA existed.
2. **Detector CPU table + replica counts** — Ron's `overload_detection.py` had a rewritten CPU table (`checkoutservice: 4500m` vs. the paper's 1000m) and `instance_scaling.py` scaled frontend to ×8. Our tree kept the stock paper table and ran every service at ×1 replica.
3. **Boutique Deployment resources/probes/images** — Ron's `online_boutique_original_custom.yaml` had bumped CPU/memory and commented-out liveness probes; he also had custom `ronnezer/*` images (frontend, product) cached on the worker with probes stripped, though not deployed. Our tree ran stock upstream YAML and stock `qkrwogud676/...` images.
4. **Loadgen mix/weights/duration** — Ron had `GETPRODUCT=600` (vs. our 100), a `@task()` weight remix favoring checkout/getcart, a `frontend.sh` launcher that split getcart/postcart/emptycart into independent Locust swarms (vs. our merged `$CART` swarm), and no `-t` time limit on his main script. Our tree kept the paper mix, weights, and merged-swarm launcher.

**Important nuance found during the design work**, not just the original audit: "Ron's setup" turned out not to be one static, recoverable configuration — see [the migration design doc](../docs/superpowers/specs/2026-09-20-ron-nezer-base-migration-design.md) §2 for the full archaeology. His disk shows an actively, iteratively tuned environment: two different HPA files a month apart, a `ResourceQuota` he repeatedly created/edited/deleted, `frontend`/`productcatalogservice` CPU live-patched via shell functions across a huge range (100m–3000m for frontend alone), and a Detector CPU table that itself disagreed with his own final Deployment YAML on 4 of 7 tracked services (`checkoutservice`: table said 4500m, YAML said 800m). There is no single "here's what worked" note. The team explicitly decided which specific artifacts to treat as ground truth (§3 below) rather than either guessing further or blocking indefinitely on asking Ron.

---

## 3. What we changed to match his setup

### 3a. Decisions made before touching any code

Reached via an interactive grilling session, written up in [2026-09-20-ron-nezer-base-migration-design.md](../docs/superpowers/specs/2026-09-20-ron-nezer-base-migration-design.md) §1 (12 numbered decisions) and echoed in four ADRs:

- [ADR-0001](../docs/adr/0001-ron-setup-as-experiment-base.md) — Ron's setup (all four layers) is the base; port his *values* into our own tree, don't repoint the runner at `/home/user/TopFull`.
- [ADR-0002](../docs/adr/0002-k8s-limits-are-detector-cpu-source-of-truth.md) — the live Kubernetes Deployment CPU limit is the single source of truth; the Detector's belief is always synced to it, on every run, not just when a scenario deliberately constrains one service — closing exactly the kind of drift bug found in Ron's own setup (§2 above, checkout 4500m vs. 800m).
- [ADR-0003](../docs/adr/0003-fit-ron-footprint-on-16-vcpu-worker.md) — Ron's numbers don't fit our hardware (GCP quota is maxed at 32 vCPU across the three VMs, no room to grow); keep his HPA *mechanism* but cap frontend at 4 replicas (not his 20) and trim every service's CPU-per-replica ~77% from his January YAML so full scale-out fits the node's real app-container budget.
- [ADR-0004](../docs/adr/0004-loadgen-shape-not-literal-numbers.md) — adopt Ron's loadgen *shape* (independent single-tag Locust swarms), not either of his two launcher scripts' literal numbers, because neither was a settled recipe.

Source-of-truth choices, since Ron's disk had multiple conflicting snapshots (§2): the **January 2026** Boutique YAML (`checkoutservice: 800m`) was picked as the CPU source of truth over the Detector table or the ResourceQuota, because it's the most recent internally-consistent artifact and governs real pod behavior regardless of what any other table believes. These numbers are explicitly marked **provisional** pending a reply from Ron himself — see [EMAIL-DRAFT-RON-TOPFULL-LOAD.md](EMAIL-DRAFT-RON-TOPFULL-LOAD.md), updated with the exact questions this archaeology raised.

### 3b. What was actually implemented (CPU / replica / HPA layer)

Carried out via [2026-09-20-ron-nezer-base-migration-implementation.md](../docs/superpowers/plans/2026-09-20-ron-nezer-base-migration-implementation.md), subagent-driven, committed to the `ron-nezer-base-migration-plan` branch:

- **Collector safety net first**: audited `resource_usage_collector.py` and `topfull_throttle_collector.py` (already multi-pod safe) and fixed `envoy_retry_collector.py`'s single-pod-IP assumption (`discover_pod_ip` hardcoded index `[0]`) — needed before deploying a multi-replica frontend, or mesh metrics would silently under-count.
- **`experiments/topfull_cpu_quotas.py`** rewritten with the Ron-config-regime, trimmed values for all 11 services (e.g. `frontend: 1150m`, `checkoutservice: 615m`, `productcatalogservice: 1535m`) and `PAPER_CPU_REQUEST_MILLICORES` emptied out, since Ron's setup uses `request == limit` everywhere (unlike the old paper table, which halved request vs. limit for some services). This one file feeds **both** the live K8s Deployment patch and the Detector overlay automatically — see the correction below.
- **Correction found mid-implementation**: the design doc originally assumed the Detector quota-sync mechanism was still S3/S4-conditional and needed to be generalized. Reading the live `run_scenario.py` code showed `reconcile_paper_cpu_limits()` / `write_run_quotas_json()` / `ensure_detector_quota_overlay()` were **already unconditional** for every scenario — ADR-0002's mechanism already existed. The real remaining work was just replacing the *values* in `topfull_cpu_quotas.py`, not building new sync logic. Both the design doc (§5, §10) and ADR-0002 were corrected to reflect this.
- **Live Boutique Deployments** patched to the trimmed CPU numbers (all 11 services), stock images and probes left untouched.
- **`frontend-hpa.yaml`** created and applied (`minReplicas: 1, maxReplicas: 4`, 85% CPU target) — same shape as Ron's HPA, lower ceiling. `productcatalogservice` HPA deliberately **not** created (deferred, conflicts with the S4A scenario premise — see §5 below).
- **`instance_scaling.py`-equivalent replica pinning** updated so it no longer force-sets `frontend`'s replica count (which would fight the new autoscaler); the other 10 services stay pinned at ×1.
- **`proxy_online_boutique.go`** patched on the live `topfull-master` tree to drop the unnecessary Host-header match on `GET /cart` and `GET /product/*`, porting Ron's one real code diff.
- **Full smoke test** (S1 baseline scenario) run afterward to validate the whole chain end-to-end.

### 3c. What was actually implemented (loadgen shape layer)

Ron's loadgen turned out to have the same "not one settled recipe" problem as his CPU numbers — two different launcher families (`online_boutique_create.sh`, merged-cart; `frontend.sh`, split-cart) interleaved with ad-hoc capacity probes in his `.bash_history`, right up to the end of the visible history. Grilled and designed in [2026-09-21-loadgen-shape-ron-migration-design.md](../docs/superpowers/specs/2026-09-21-loadgen-shape-ron-migration-design.md), and defined precisely in [CONTEXT.md](../CONTEXT.md)'s Loadgen section (**loadgen shape** vs. **loadgen numbers** vs. **task-weight remix** — kept as three separate concepts on purpose).

Decision: adopt the **shape** both scripts partially agree on — one independent Locust swarm per tag, so `@task()` weights never arbitrate between tags — not either script's literal numbers (ADR-0004). Implemented via [2026-09-21-loadgen-shape-ron-migration-implementation.md](../docs/superpowers/plans/2026-09-21-loadgen-shape-ron-migration-implementation.md):

- `experiments/run_scenario.py`'s `_launch_locust()` now dual-exports `EMPTYCART` alongside the legacy `CART`, so `experiments/loadgen/online_boutique_create_v2.sh` (independent per-tag swarms; spawn math aligned to Ron's float `count / RATE` on 2026-09-22) can read it correctly while old scenario YAMLs keep working unchanged.
- `experiments/patch_locust_task_weights.py` — a one-shot, idempotent patcher for the deployed `locust_online_boutique.py` on `topfull-load`, applying Ron's `@task()` weight remix (postcheckout 50→500, getcart 30→100, postcart 15→1, emptycart 15→1, getproduct 150→100) for fidelity, even though it is currently **inert** — no scenario merges tags into one swarm under the adopted shape.
- `_deploy_local_loadgen_scripts()` added to `run_scenario.py` so any repo-tracked loadgen script (like `online_boutique_create_v2.sh`) is auto-redeployed to `topfull-load` before every Locust launch, the same "never trust a stale remote copy" treatment already given to master's collectors.
- Live-verified on `topfull-load`: patcher runs and is idempotent, weights land correctly, `online_boutique_create_v2.sh` launches five independent tmux/Locust sessions correctly, legacy scripts remain unaffected.
- `create2.sh`'s low-continuous-trickle pattern was deliberately **dropped**, not ported — it belongs only to the merged-cart launcher family we didn't adopt, and Ron's own more-exercised `frontend.sh` has no equivalent step.

---

## 4. What was decided to be left out

Explicit non-adoptions, all recorded in the design doc §5/§7/§10 and ADR-0003/ADR-0004:

- **`ronnezer/*` custom images** (frontend, product) — they strip health probes, which would confound a project specifically measuring overload/retry behavior. Stock paper images (`qkrwogud676/...`) stay.
- **The 2600m namespace `ResourceQuota`** — mathematically incompatible with Ron's own other numbers even in his own history (§2 above); not adopted at any layer.
- **`metrics-server hostNetwork: true`** — investigated per an explicit request to check; no supporting artifact found anywhere (no manifest, no `.bash_history` hit, current live Deployment doesn't have it). Not adopted.
- **Ron's literal frontend replica ceiling (×20 via HPA, or ×8 via the earlier `instance_scaling.py` snapshot)** — capped at ×4 instead, because the GCP compute quota (32 vCPU across all three VMs, already fully used) leaves no room to grow the worker node.
- **`productcatalogservice` HPA** — Ron had this enabled; left disabled here because it directly conflicts with Scenario 4A's premise that productcatalog is a fixed, non-compensating bottleneck. Deferred to the S1–S6 methodology rework (§5 below), not rejected outright.
- **Either loadgen launcher script's literal numbers** (`frontend.sh`'s 100/50/100/100/100 @ RATE=50, or `create.sh`'s 600/20/100/100/300 @ RATE=90) — neither is treated as ground truth; only the shape was adopted (§3c).
- **`create2.sh`'s trickle-load pattern** — no replacement added under the new shape.

---

## 5. What's still open

Two categories:

1. **Waiting on an external answer.** All of §3b's CPU/replica numbers are explicitly provisional pending Ron Nezer's reply to [EMAIL-DRAFT-RON-TOPFULL-LOAD.md](EMAIL-DRAFT-RON-TOPFULL-LOAD.md) about which of his several inconsistent on-disk snapshots (§2) was actually live when he observed TopFull engage. If he confirms different real numbers, only the source-of-truth table and the trim arithmetic need to be redone (design doc §9) — the mechanism, ADRs, and everything in §3c are unaffected.
2. **Deferred by explicit team decision, not by design.** The S1–S6 scenario methodology rework, real loadgen numbers (per-tag user counts/spawn rate), rewiring all 16 scenario YAMLs onto the new launcher, and a fresh campaign to replace `campaign_48/` — none of this depends on Ron's reply; it's just sequenced after the mechanism work. Tracked with checkboxes in [2026-09-21-s1-s6-loadgen-numbers-remaining-work.md](../docs/superpowers/specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md). **Methodology + calibration decisions made 2026-09-21** (not yet implemented): [2026-09-21-s1-s6-methodology-and-calibration-design.md](../docs/superpowers/specs/2026-09-21-s1-s6-methodology-and-calibration-design.md) — S3/S4A/S4B switch to an absolute `cpu_limit_millicores: 50` bottleneck cap ([ADR-0006](../docs/adr/0006-absolute-bottleneck-cap-not-fraction.md)), productcatalog HPA gets enabled (`maxReplicas: 2`, accepted node-overcommit risk with frontend's own HPA — [ADR-0005](../docs/adr/0005-productcatalog-hpa-max-replicas-2.md), **flag this risk here once implemented**), and a 5-run recalibration battery replaces the pre-migration `capacity_frozen.json` values before any of S3/S4A/S4B's real load numbers are set.

`campaign_48/` (the 48-run August/September campaign) and the frozen-capacity μ-calibration (`experiments/capacity/capacity_frozen.json`) are now historical — collected under the old "paper-config regime" — per decision 6 in the design doc. They remain in git for reference but are not the dataset for any future report; a new campaign has to be planned and run once the open items above land.

---

## 6. What stayed ours, unconditionally

None of the following depend on which TopFull "recipe" runs underneath — kept as-is throughout the whole migration (design doc §6):

- The RetryGuard controller (`experiments/retryguard.py`) and its VirtualServices `retries`/`perTryTimeout` patch.
- `envoy_retry_collector.py` (mesh `service_edges.csv`/`service_inbound.csv`), `resource_usage_collector.py`, `topfull_throttle_collector.py`.
- Multi-user infra fixes on `topfull-master` (per-user `~/.kube/config`, directory write permissions, the `go` PATH symlink) — about which Linux account runs the tooling, orthogonal to the recipe.
- Locust 2.x event-API compatibility, `metric_collector.py`'s crash-guard, the dynamic cAdvisor IP lookup.
- All analysis/orchestration tooling (`run_scenario.py`, `pull_results.py`, `rho_estimate_report.py`, `capacity_frozen.py`/`rho_frozen_report.py`) — the tools are reusable; only the data they've already produced becomes historical.

---

## 7. Reference index

| Doc | What it covers |
|---|---|
| [RON-NEZER-SETUP-VS-WORKSHOP.md](RON-NEZER-SETUP-VS-WORKSHOP.md) | The original 2026-09-20 audit: exactly what differs, file-by-file, between KAIST upstream / Ron's clone / our clone |
| [2026-09-20-ron-nezer-base-migration-design.md](../docs/superpowers/specs/2026-09-20-ron-nezer-base-migration-design.md) | Full design: 12 decisions, the archaeology behind §2's "not one static config" finding, CPU budget arithmetic, implementation checklist |
| [2026-09-20-ron-nezer-base-migration-implementation.md](../docs/superpowers/plans/2026-09-20-ron-nezer-base-migration-implementation.md) | Task-by-task implementation plan for the CPU/replica/HPA layer |
| [2026-09-21-loadgen-shape-ron-migration-design.md](../docs/superpowers/specs/2026-09-21-loadgen-shape-ron-migration-design.md) | Loadgen shape design: why neither launcher script is a settled recipe, what shape/weights/vehicle were adopted |
| [2026-09-21-loadgen-shape-ron-migration-implementation.md](../docs/superpowers/plans/2026-09-21-loadgen-shape-ron-migration-implementation.md) | Task-by-task implementation plan for the loadgen shape layer |
| [2026-09-21-s1-s6-loadgen-numbers-remaining-work.md](../docs/superpowers/specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md) | Checkbox tracker for what's still open (§5 above) |
| [ADR-0001](../docs/adr/0001-ron-setup-as-experiment-base.md) – [ADR-0004](../docs/adr/0004-loadgen-shape-not-literal-numbers.md) | The four durable decisions, in ADR form |
| [CONTEXT.md](../CONTEXT.md) | Shared vocabulary: paper-config regime vs. Ron-config regime, loadgen shape vs. loadgen numbers vs. task-weight remix, etc. |
| [EMAIL-DRAFT-RON-TOPFULL-LOAD.md](EMAIL-DRAFT-RON-TOPFULL-LOAD.md) | The exact questions sent to Ron about which of his conflicting snapshots was live |
| `AGENTS.md` §4 | Running log of "current status" bullets as each piece of this migration landed |
