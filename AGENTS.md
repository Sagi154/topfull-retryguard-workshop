# AGENTS.md — Context Guide for AI Agents

> **Purpose:** This file orients a new agent session on this repo: what the project is, what has been built, what state it's in *right now*, and what's left to do. Read this first, then follow the links for details. Don't duplicate this file's content elsewhere — update it as the project progresses. Domain vocabulary: [CONTEXT.md](CONTEXT.md). Architecture decisions: [docs/adr/](docs/adr/).

---

## 1. What this project is

**TAU Deepness Lab Workshop — "Project 1: Retries for Cloud Microservices."**

Goal: evaluate **RetryGuard** (a retry-storm controller we implement ourselves from its paper) on top of **TopFull** (an existing overload-control system, from KAIST) running the **Online Boutique** microservice demo app on a real Kubernetes cluster, under **Istio** service mesh, with **Locust** generating load.

Two experimental conditions, same load each time:

| Condition | Overload control | Retries |
|---|---|---|
| **Baseline** (Phase 5) | TopFull | Istio default (`attempts: 3`, RetryGuard off) |
| **Primary** (Phase 6) | TopFull | RetryGuard dynamically toggles retries per service |

We run **6 scenarios** (see §5): the eval-deck five plus Scenario 6 (forced recovery, so re-enable can be measured without changing S2's load). S1–S4 and S6 run under both conditions, ≥3 repeats each (Locust traffic is non-deterministic); S5 is RetryGuard-only and uses **S6's load**, compared against S6 baseline — not S2. Then compare goodput / P95 latency / rejection rate / retries-per-request / CPU/memory / RetryGuard toggle events. The finished August **38-run matrix** has goodput/P95/rejection but not retries or CPU/memory, and its 8 S5 runs never re-enabled. **Phase 7 close-out is a completed paper-grade 48-run campaign** (new slots, all collectors on, ×3 including S5) — see [PHASE7-RESOLVE-GAPS-1-3.md](Guides%20and%20Info/PHASE7-RESOLVE-GAPS-1-3.md). P99 was dropped as a target metric (P95 fully satisfies both source papers and the eval deck) — see [PHASE7-DATA-GAPS.md](Guides%20and%20Info/PHASE7-DATA-GAPS.md).

This is a workshop deliverable: a presentation (project plan) + eventually a written report with the above comparison.

---

## 2. Repo layout

```
Guides and Info/     ← all human-facing docs (see §3 — start here for "why")
  mentor-update/     ← mentor-facing dry-results doc + curated/gallery PNGs ([MENTOR-UPDATE.md](Guides%20and%20Info/mentor-update/MENTOR-UPDATE.md))
experiments/         ← the actual tooling: runner, scenario configs, RetryGuard + Envoy retry collectors
  configs/           ← scenario YAML files (S1–S4 baseline/RG, S5×4 intervals, S6 recovery baseline/RG). Older files stay here.
    final_configs/   ← copies of locked S1–S4 only, five variants each. New holds use these. See [final_configs/README.md](experiments/configs/final_configs/README.md)
  run_scenario.py    ← orchestrator, runs on Windows, drives everything over SSH
  retryguard.py      ← RetryGuard controller (deployed to master)
  envoy_retry_collector.py ← Gap 3: scrapes Envoy sidecar outbound retry counters (deployed to master)
  resource_usage_collector.py ← Layer 2: scrapes CPU/memory per service via kubelet stats/summary (deployed to master)
  mentor_charts.py / mentor_charts_data.py / mentor_charts_plots.py ← regenerate mentor-update PNGs from `campaign_48/` (`python experiments/mentor_charts.py`)
  virtual-services.yaml ← Istio VirtualService manifests (retries.attempts: 3 default)
  patch_metric_collector.py ← one-shot patcher already applied on master (see §6d in PHASE5 guide)
  results/           ← local results only (master still uses a flat `/home/idozacharia/experiments/results/`)
    final results/   ← **where every new hold is pulled.** Scenario, RetryGuard mode, then controller variant — the rule is in §6
    campaign_48/     ← closed Phase 7 dataset (2026-09-05 → 2026-09-06), in git, organized into 7 scenario subfolders (`S1_normal_op/` … `S6_forced_recovery/`) — see [experiments/results/campaign_48/README.md](experiments/results/campaign_48/README.md)
    august_38/       ← historical August 38-run matrix (git-tracked; do not delete; still a flat list of run folders, not reorganized)
TopFull/             ← git submodule, upstream https://github.com/kaist-ina/TopFull (read locally; also cloned separately on the VMs)
context/             ← papers/decks: RetryGuard.pdf, TopFull.pdf, Evaluating_RetryGuard_on_TopFull.{pdf,md} (current eval deck + transcription)
canvases/            ← interactive workplan canvas for Cursor (topfull-retryguard-workplan.canvas.tsx)
infra/vm-ips.env     ← names, private IPs, and machine types for the live copy — public IPs are not stored, see §7
.cursor/rules/topfull-ssh.mdc ← always-applied rule: SSH conventions for the 3 VMs
scripts/             ← md_to_pdf.py, sync-canvas-to-cursor.ps1 (presentation/canvas tooling, not experiment-critical)
```

**Submodule note:** `TopFull/` is a git submodule (`.gitmodules`). If it appears empty, run `git submodule update --init`.

---

## 3. Guides — what to read for what

All in `Guides and Info/`. Read in roughly this order depending on task:

| Doc | Read when you need to... |
|---|---|
| [PREREQUISITES.md](Guides%20and%20Info/PREREQUISITES.md) | Understand what should be true before any cloud work (mostly historical now — VMs already exist) |
| [MENTOR-COORDINATION.md](Guides%20and%20Info/MENTOR-COORDINATION.md) | Understand decisions mentors already made (GCP, Istio-based RetryGuard integration, eval strategy) |
| [WORKPLAN.md](Guides%20and%20Info/WORKPLAN.md) | See the full Phase 0–7 plan with Why/How/Done-when for each step (Phases 0–6 done; Phase 7 campaign data complete; 7a/7b eval + written report remaining) |
| [SETUP-GUIDE.md](Guides%20and%20Info/SETUP-GUIDE.md) | Get exact commands for cluster/Istio/dependency setup, if something needs to be rebuilt |
| [MANAGED-KUBERNETES.md](Guides%20and%20Info/MANAGED-KUBERNETES.md) | Understand why we used self-managed `kubeadm` K8s instead of GKE (decision already made — not adopted) |
| [CONNECT-VMS.md](Guides%20and%20Info/CONNECT-VMS.md) | **SSH into the VMs.** Canonical playbook — also mirrored in `.cursor/rules/topfull-ssh.mdc` (always-applied) |
| **[PHASE5-EXPERIMENTS-GUIDE.md](Guides%20and%20Info/PHASE5-EXPERIMENTS-GUIDE.md)** | Canonical reference for the experiment runner + scenario config system. Read before touching `experiments/` |
| **[PHASE5-PHASE6-RUNLIST.md](Guides%20and%20Info/PHASE5-PHASE6-RUNLIST.md)** | **Matrix checklist.** All 38 runs done as of 2026-08-15; all 38 folders are local and in git. The “where results live” header in that file is stale |
| [EXPERIMENT-READINESS-WORKPLAN.md](Guides%20and%20Info/EXPERIMENT-READINESS-WORKPLAN.md) | Historical smoke-validation checklist (Steps 1–8 passed 2026-08-07). Do not mix smoke folders into Phase 7 analysis |
| [METRICS-COLLECTION-GUIDE.md](Guides%20and%20Info/METRICS-COLLECTION-GUIDE.md) | What each run produces, how to pull/verify, how to load for charts |
| [TOPFULL-HOW-THEY-MEASURE.md](Guides%20and%20Info/TOPFULL-HOW-THEY-MEASURE.md) | Plain-language notes from the TopFull paper: goodput, SLO, and the charts they use to score the system |
| **[METRICS-GATHERED.md](Guides%20and%20Info/METRICS-GATHERED.md)** | **Inventory of every metric we actually collect** (Locust CSVs, Envoy retries, CPU/memory, TopFull throttle, RetryGuard log, empty/`Latency99` caveats, clocks). Start here for “what do we gather?” |
| **[METRICS-CATALOG.md](Guides%20and%20Info/METRICS-CATALOG.md)** | **Why we collect each metric** — same coverage as METRICS-GATHERED.md, organized by "vantage point in the stack" with a rationale per metric and a metric→open-question map. Read this for report-writing / justifying why a number is in the paper. |
| [TOPFULL-THROTTLE-METRICS.md](Guides%20and%20Info/TOPFULL-THROTTLE-METRICS.md) | **Implemented collector** (`topfull_throttle.csv` + `topfull_detect.csv`). On a 1 s series, a live threshold of 10000 is no cap and a live 0 is an empty read; leave both off. Hold the last usable cap for at most 6 s. The original 48-run / `august_38/` folders still lack these files. |
| [PER-SERVICE-METRICS.md](Guides%20and%20Info/PER-SERVICE-METRICS.md) | Locust is per **entry API**, not per Kubernetes service. What is already per-service (CPU, some Envoy retries) vs what Envoy inbound could add |
| **[LOCUST-API-PATHS.md](Guides%20and%20Info/LOCUST-API-PATHS.md)** | **The five Locust entry APIs** (`getproduct`, `getcart`, `postcart`, `emptycart`, `postcheckout`): the HTTP call, which Online Boutique services each one traverses, and where those paths overlap. Read before attributing a service’s load to a Locust tag. |
| [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md) | **Implemented (2026-09-08).** Full-mesh Envoy collector (`service_edges.csv` / `service_inbound.csv`) + `service_capacity.json`; no campaign data yet |
| **[PHASE7-DATA-GAPS.md](Guides%20and%20Info/PHASE7-DATA-GAPS.md)** | **Read before analysing.** August-38 audit plus campaign close-out: Gap 1/3 **closed** on `campaign_48/`; Gap 2 dropped P99 (use P95). |
| **[PHASE7-RESOLVE-GAPS-1-3.md](Guides%20and%20Info/PHASE7-RESOLVE-GAPS-1-3.md)** | **Runbook.** Paper-grade 48-run campaign — **COMPLETE** (2026-09-06). Primary analysis is `experiments/results/campaign_48/`. Do not use `run_all_scenarios.py`. |
| [Evaluating_RetryGuard_on_TopFull.md](context/Evaluating_RetryGuard_on_TopFull.md) | **Eval plan deck** (transcription of the PDF). Slides 8–9 open questions, 11–15 scenario objectives, 16 measurement layers — source of truth for what Phase 7 is supposed to answer |
| [SCENARIOS-GUIDE.md](Guides%20and%20Info/SCENARIOS-GUIDE.md) | Understand each of the 6 scenarios in detail: what it tests, load setup, manual step-by-step (pre-dates `run_scenario.py` automation, but good for *why*) |
| **[MENTOR-UPDATE.md](Guides%20and%20Info/mentor-update/MENTOR-UPDATE.md)** | **Mentor-facing dry results** (infra, Online Boutique, scenarios, per-scenario charts + observations). Pipeline / leftover caveats: [mentor-update/README.md](Guides%20and%20Info/mentor-update/README.md) |
| **[RON-NEZER-SETUP-VS-WORKSHOP.md](Guides%20and%20Info/RON-NEZER-SETUP-VS-WORKSHOP.md)** | **The 2026-09-20 audit.** Copied his VMs, not his experiment setup. `/home/user/TopFull` is Ron's 2025 recipe (load mix, detector quotas, HPA, custom images); live runs use `/home/idozacharia/TopFull` (KAIST + our patches). |
| **[RON-NEZER-BASE-MIGRATION.md](Guides%20and%20Info/RON-NEZER-BASE-MIGRATION.md)** | **Narrative of the migration onto Ron's setup as the experiment base.** Where we differed, what we changed (CPU/replica/HPA + loadgen shape), what was left out, what's still open. Specs/plans/ADRs are linked from there — start here, not in the task logs. Remaining-work checkboxes: [2026-09-21-s1-s6-loadgen-numbers-remaining-work.md](docs/superpowers/specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md). |
| [RETRYGUARD-IMPLEMENTATION.md](Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md) | Understand exactly how `experiments/retryguard.py` maps to paper Algorithm 1, its metric source, endpoint→service map, VS patch mechanics, log format |
| **[ANALYSIS-TEMPLATE.md](Guides%20and%20Info/ANALYSIS-TEMPLATE.md)** | **Write-up for a new hold or a group of holds.** Section order, (a)/(b)/(c) cell shapes, bold rules. Score with `python experiments/analysis_score.py`. The (a)/(b)/(c) definitions are [2026-09-24-s2-both-off-abc-reading.md](Guides%20and%20Info/2026-09-24-s2-both-off-abc-reading.md). `rho_estimate_report.py` is retired. |
| [NEXT-PHASES-PLAN.md](Guides%20and%20Info/NEXT-PHASES-PLAN.md) | See the presentation-track vs lab-track split and near-term suggested order |
| [PRESENTATION-GUIDE.md](Guides%20and%20Info/PRESENTATION-GUIDE.md), [PRESENTATION-ACTION-ITEMS.md](Guides%20and%20Info/PRESENTATION-ACTION-ITEMS.md), [NOTEBOOKLM-PROMPT.md](Guides%20and%20Info/NOTEBOOKLM-PROMPT.md) | Work on the slide deck / presentation track (separate from the lab track) |
| [GEMINI-PROMPT.md](GEMINI-PROMPT.md), [CANVAS-VIEWING.md](CANVAS-VIEWING.md) | Presentation-generation tooling and how to view the interactive canvas in Cursor |

### Where to find metrics

| Question | Read |
|---|---|
| What do we collect, and in which file/column? | [METRICS-GATHERED.md](Guides%20and%20Info/METRICS-GATHERED.md) (includes the derived-metrics table) |
| How do I line up metrics in time / see a run second by second? | `python experiments/run_timeline.py <run_dir>` → `timeline.png`; design in [2026-10-13-hold-clock-design.md](docs/superpowers/specs/2026-10-13-hold-clock-design.md) |
| Why do we collect each metric? | [METRICS-CATALOG.md](Guides%20and%20Info/METRICS-CATALOG.md) |
| How is a run's output produced, pulled, verified? | [METRICS-COLLECTION-GUIDE.md](Guides%20and%20Info/METRICS-COLLECTION-GUIDE.md) |
| Is a hold's TopFull cap / admitted data trustworthy? | The `Throttle data quality` table from `experiments/analysis_score.py`; rule in §6 "After every hold" |
| Per-service vs per-entry-API data, mesh files | [PER-SERVICE-METRICS.md](Guides%20and%20Info/PER-SERVICE-METRICS.md), [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md) |
| TopFull throttle caps / detector files | [TOPFULL-THROTTLE-METRICS.md](Guides%20and%20Info/TOPFULL-THROTTLE-METRICS.md) |
| How metrics are displayed and scored in a write-up | [ANALYSIS-TEMPLATE.md](Guides%20and%20Info/ANALYSIS-TEMPLATE.md), computed by `experiments/analysis_score.py` |
| Controller vs scorer rejection definitions | [2026-10-13-controller-vs-scorer-rejection.md](Guides%20and%20Info/2026-10-13-controller-vs-scorer-rejection.md) |

---

## 4. Current status (as of 2026-10-13)

### Latest

Replace these three lines after a hold. Do not append. Older text goes under Done in [STATUS.md](STATUS.md).

- **S4 relock mode matrix (2026-10-14).** Branch `s4-relock-mode-matrix` from `e26f05c`, thirty holds. S4A constrained catalog 100 m on mix 50/20/50/600/5 in `run3` and `run4`. S4A unconstrained catalog 800 m on that mix in `run1` and `run2`. S4B email 50 m on mix 175/30/70/90/5 in `run1` and `run2`. Next free slots: constrained run 5, unconstrained run 3, S4B run 3.
- **39 PASS, 5 INVALID, and 21 throttle FLAG** lines in [2026-10-13-s4-relock-mode-matrix-run-log.md](docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md), including the 2026-10-14 re-gate lines. Guides: [2026-10-13-s4a-constrained-relock-abc.md](Guides%20and%20Info/2026-10-13-s4a-constrained-relock-abc.md), [2026-10-13-s4a-unconstrained-relock-abc.md](Guides%20and%20Info/2026-10-13-s4a-unconstrained-relock-abc.md), [2026-10-13-s4b-relock-abc.md](Guides%20and%20Info/2026-10-13-s4b-relock-abc.md).
- The cluster was restored to frontend HPA 1–4, catalog HPA max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m, and the three VMs were still RUNNING. Task 9 replaces that clause after it stops them.

### Still open

- S1, S2, S3, S4A, and S4B loads and CPU tables are locked (counts and constrained rows are in §5). The [2026-09-21 methodology plan](docs/superpowers/plans/2026-09-21-s1-s6-methodology-and-calibration-implementation.md) stopped at Task 9 step 2a. S6 stays on its current YAML.
- Share [MENTOR-UPDATE.md](Guides%20and%20Info/mentor-update/MENTOR-UPDATE.md), then write the Phase 7 eval on `experiments/results/campaign_48/` once mentors say the data is enough.
- Wire `service_inbound.csv` / `service_edges.csv` into the mentor charts. Mesh files are already per-service outcomes.
- Frozen μ lives in [experiments/capacity/README.md](experiments/capacity/README.md).
- The S4 relock mode matrix is the locked S4A/S4B set under `final results/`, and the catalog-50m mode matrix and `campaign_48/` S4A/S4B are not comparable.

Read [STATUS.md](STATUS.md) before a new hold, a `run_number` bump, scoring an old folder, or deciding what is left. After a hold, append one bullet under Done there, update Next free slots, and replace Latest here.

### ⚠️ Live infra caveat (check before assuming the cluster is healthy)

The 3 VMs can be stopped/started between sessions (to save cost) and IPs are ephemeral. Last time this was checked (see §7), the VMs were `RUNNING` but `kubectl` on master returned `connection to localhost:8080 refused` — the API server hadn't come back up yet after a restart, even though `kubelet`/`docker`/`cri-docker` services were all `active`. This is most likely just "static pods still booting" — **always re-verify cluster health at the start of a session** rather than assuming it's still in the last-known-good state:

```powershell
ssh topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

If it doesn't recover within a few minutes, follow the troubleshooting table in SETUP-GUIDE.md / CONNECT-VMS.md. **Correction to that earlier diagnosis:** the actual cause turned out to be a missing `~/.kube/config` for the SSH user, not the API server booting — see the multi-user note in §7.

---

## 5. The scenarios (quick reference — full detail in SCENARIOS-GUIDE.md / PHASE5-EXPERIMENTS-GUIDE.md)

| # | Name | What changes | Duration | Config files |
|---|---|---|---|---|
| 1 | Normal Operation | Flat load, well within capacity. Locked mix **175 / 30 / 70 / 90 / 5**, `spawn_rate` 50, Paper-C1 (both-off run8) | 5 min | `final_configs/1/` |
| 2 | Sustained Overload (core) | Peak from t=0, **hold flat**. Locked mix **275 / 90 / 100 / 90 / 5**, `spawn_rate` 50, Paper-C1 (both-off run 89) | 10 min | `final_configs/2/` |
| 3 | Targeted Bottleneck | Locked mix **175 / 30 / 70 / 90 / 5** (same as S1), `spawn_rate` 50. Paper-C1 with `checkoutservice` constrained to **200m** | 10 min | `final_configs/3/` |
| 4A | Topology Position (gateway-adjacent) | Locked mix **50 / 20 / 50 / 600 / 5**, `spawn_rate` 50. Two configs: **unconstrained** (plain Paper-C1) and **constrained** (`productcatalogservice` → **100m**) | 10 min | `final_configs/4/4a_{unconstrained,constrained}/` |
| 4B | Topology Position (Checkout-mediated: Frontend → Checkout → Email) | Locked mix **175 / 30 / 70 / 90 / 5** (same as S1), `spawn_rate` 50. Paper-C1 with `emailservice` constrained to **50m** | 10 min | `final_configs/4/4b/` |
| 5 | Interval Tuning | Same load as S6; `interval_samples` = 10/20/30/60 | 15 min | `scenario_5_interval_{10,20,30,60}s.yaml` |
| 6 | Forced Recovery | Peak 5 min, then ~25% load for 10 min | 15 min | `scenario_6_recovery_{baseline,retryguard}.yaml` |

New holds for S1–S4 use [experiments/configs/final_configs/](experiments/configs/final_configs/README.md). Each scenario folder has five copies: `rg_only_burst`, `rg_only_normal`, `tf_only`, `both_burst`, `both_normal`. The files next to that folder (`scenario_1_baseline.yaml` and the rest) stay for history and are not moved. S5 and S6 are not in `final_configs/`.

Changed from paymentservice on 2026-10-09; `campaign_48/` S4B runs used paymentservice and are not comparable.

Note: Scenarios 3/4 constrain via `method: cpu_limit` with absolute `cpu_limit_millicores` ([ADR 0006](docs/adr/0006-absolute-bottleneck-cap-not-fraction.md)); no `cpu_limit_fraction`. Each S3/S4 YAML carries the full Paper-C1 table with one row constrained (S3 checkout 200m, S4A-constrained catalog 100m, S4B email 50m; S4A-unconstrained none). S3 and S4B were locked on 2026-10-13. S4A was re-locked the same day to mix **50 / 20 / 50 / 600 / 5** and constrained catalog **100m**. Earlier S3/S4 holds (50m checkout, 40m email, the 10/10/10/600/5 mix, catalog 50m) are not comparable. The two S4A variants share `scenario_name: topology_position_A` and are told apart by `log_folder` (`..._topology_position_A_constrained_run<N>` / `..._unconstrained_run<N>`). The runner reconciles K8s + Detector to paper quotas before/after each run — a leftover constrained value is healed and must not be treated as the S2 baseline. S4A holds before this re-lock, including `campaign_48/` S4A and the 2026-10-13 mode matrix at catalog 50m, are not comparable. Scenario 5's 8 August matrix runs (`august_38/`) have **no re-enable events** (they used a flat hold). Campaign S5 (`campaign_48/`, S6's load) **did** re-enable; compare against **S6 baseline**, not S2. August Scenario 2 run1–3 remain historical; campaign S2 run4–6 is the primary flat-hold dataset.

### Locked CPU table (Paper-C1)

Paper-C1 is the default CPU table for every hold. [ADR 0009](docs/adr/0009-paper-c1-default-cpu-table.md) is its only source of truth; do not copy the values elsewhere. Each scenario YAML carries the full table in `scale_constraints`. A scenario that constrains a service (S3, S4A, S4B) writes the constrained value in that service's row and leaves the rest at the table value. If a YAML disagrees with the ADR on an unconstrained row, fix the YAML. `PAPER_CPU_LIMIT_MILLICORES` in `experiments/topfull_cpu_quotas.py` mirrors the ADR, and a test fails if they differ. On the VMs, every hold resets all eleven Deployments to the table before and after the run, then aborts before Locust starts if live limits differ from table + constraints. There is no opt-out: the old `paper_cpu_reconcile` key is removed from the runner and ignored in old YAMLs.

### Locked RetryGuard parameters

Every run with RetryGuard on uses these values: `retry_metric` `edge_rpr`; `sample_interval_seconds` 1; `interval_samples` 20; `rejection_threshold` 0.2; `retries_threshold` 0.4; `climb_rpr_1_to_2` 0.16; `climb_rpr_2_to_3` 0.32; `climb_interval_seconds` 10; `reenable_rejection` 0.25; `burst_rpr` 2.0; `burst_window_seconds` 5; `burst_min_first_attempts` 20. Burst mode is the last three keys. RetryGuard normal mode omits exactly those three and keeps the other nine. Scenario 5 is the only exception (it sweeps `interval_samples`). Holds before 2026-10-12, `campaign_48/`, and `august_38/` used older values and are not comparable. Canonical table: [RETRYGUARD-IMPLEMENTATION.md](Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md). Decision: [ADR 0008](docs/adr/0008-locked-retryguard-parameters.md).

---

## 6. How to run an experiment (once cluster is confirmed healthy)

```powershell
pip install pyyaml   # once

# Before every run: clear stale /tmp runner scripts.
# /tmp has a sticky bit — if a previous run was by a different Linux user, their
# files block SCP uploads. sudo rm is a no-op when files don't exist.
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
```

**Cool-off between holds is 120 s.** The clock starts when `run_scenario.py` exits. Pulling the folder is fine during the wait. After 120 s, do the leftover-writer check below, then launch. Holds in one comparison use this same gap. Earlier holds used 300 s or 360 s; those records stay as they are. Checkout and recommendations stay up across the cool-off on every scenario. `restart_before_hold` remains an opt-in YAML key.

**After the cool-off, before `run_scenario.py`:** open [STATUS.md](STATUS.md) "Next free slots" and bump `run_number` and `log_folder`. Then stop leftover writers, and confirm the live log directory stays empty. The previous run's cleanup already stops Locust and the master processes and copies that run's folder. The runner does not repeat that stop. `clear_logs` only deletes files in the live `src/logs` directory, and a collector that is still running creates them again on its next poll. Locust is on the load VM and keeps sending until it is stopped. Do not delete `experiments/results/` or a finished `results/<log_folder>/`.

1. Stop Locust, the same way a finished run does: `ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"`
2. Stop the master processes, the same way a finished run does: mesh collector, throttle collector, CPU collector, RetryGuard, proxy, TopFull, and Ray.
   ```powershell
   ssh topfull-master "pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
   ```
3. Confirm both hosts are clear. Any output other than the `-clear` line means a process is still alive. Do not continue.
   ```powershell
   ssh topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
   ssh topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
   ```
4. Clear the live log directory: `ssh topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log"`
5. Wait two seconds and list that directory. If a `.csv` or `.log` is back, a writer is still alive. Do not start the run.
   ```powershell
   ssh topfull-master "sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
   ```

New holds that are pulled into `final results/` use a file under `experiments/configs/final_configs/`. Example, S2 with both controllers on and RetryGuard in burst mode:

```powershell
python experiments/run_scenario.py experiments/configs/final_configs/2/s2_both_burst.yaml
```

The older `experiments/configs/scenario_*.yaml` files are still valid runner inputs. They are kept for history and are not the configs for a new `final results/` hold.

The runner handles everything end-to-end, including copying `retryguard.py`, `envoy_retry_collector.py`, `resource_usage_collector.py`, and `topfull_throttle_collector.py` from this repo onto master before those processes start. It clears `src/logs` again at startup. That second clear is safe only when step 5 above showed an empty directory. On master, results stay flat at `results_base_path/<log_folder>/`.

**After every hold: check throttle data quality.** The TopFull proxy admin endpoints (`/thresholds`, `/stats`) sometimes time out and the collector then carries stale values. In the 2026-10-10 → 10-12 S2 holds, 6 of 17 were affected (4 of them in the `study6` window), one for ~70% of its run. Right after pulling, run `python experiments/analysis_score.py <run_dir>` and read its `Throttle data quality` table, or just `rg "fetch failed" "<run_dir>/topfull_throttle_collector.log"`. A hold is **FLAGGED** if that log has any `fetch failed` WARNING or any API goes over 30 s with no fresh threshold or admitted read (normal is 5 s). Then: (1) put one line in the [STATUS.md](STATUS.md) Done bullet for that hold saying it is flagged and how long it was stale; (2) never use its cap or admitted-rate numbers as measured (drop them or filter on `*_fresh==1`); (3) name it in the write-up per [ANALYSIS-TEMPLATE.md](Guides%20and%20Info/ANALYSIS-TEMPLATE.md) item 17; (4) if the flag is on a TopFull-on hold, tell the user so they can decide on a re-run, since the repeat slot is a bump of `run_number`. Goodput, P95, rejection, and retry numbers do not use that file and remain valid. Not a flag: a missing `EXIT` line in `resource_usage_collector.log` (the kill lands before it is written; `SHUTDOWN` is the reliable end marker), and an Envoy or resource log that is only `START` / `SHUTDOWN` (successful polls log nothing).

**Pull every new hold into `final results/`.** The runner's printed `scp` and `python experiments/pull_results.py <config>` already point at the path below for every config, whatever its `log_folder`. `campaign_48/` is the closed Phase 7 dataset and is never a target. TopFull-only holds go in the `normal` mode folder:

```
experiments/results/final results/<scenario>_<normal|burst>/<variant>/<log_folder>/
```

| Scenario | `<scenario>` |
|---|---|
| 1 Normal Operation | `S1_normal_operation` |
| 2 Sustained Overload | `S2_sustained_overload` |
| 3 Targeted Bottleneck | `S3_targeted_bottleneck` |
| 4A Topology Position | `S4A_topology_position` |
| 4B Topology Position | `S4B_topology_position` |
| 5 Interval Tuning | `S5_interval_tuning` |
| 6 Forced Recovery | `S6_forced_recovery` |

The last segment of `<scenario>_<normal|burst>` is the RetryGuard mode. Use `normal` when the YAML omits the three burst keys in §5. Use `burst` when the YAML sets them (`burst_rpr` **2.0**). The `log_folder` name keeps the bar. Older bar-1.5 holds share the `burst` folder. `<variant>` is the controller pair:

| RetryGuard | TopFull | `<variant>` |
|---|---|---|
| on | off | `rg_only` |
| off | on | `tf_only` |
| on | on | `both` |
| off | off | `both_off` |

Create the scenario and variant directories when they are missing. The run directory name stays equal to `log_folder`. Example: `experiments/results/final results/S2_sustained_overload_burst/both/s2_burst20_rgtf1/`.

**Before repeating a scenario:** open [STATUS.md](STATUS.md) "Next free slots", bump `run_number` and change `log_folder` in the YAML, or the new run will overwrite the folder **on master**. Never reuse August `run1–3` (S1–S4) or S5 `run1–2`.

Full config schema, `scale_constraints` methods, and troubleshooting: [PHASE5-EXPERIMENTS-GUIDE.md](Guides%20and%20Info/PHASE5-EXPERIMENTS-GUIDE.md) §5 and [experiments/README.md](experiments/README.md).

---

## 7. Infrastructure facts an agent needs

- **Project:** `project-76deda76-55f1-42d2-abb` (Yoav's 2026-10-01 disk copy; console name "My First Project") · **Zone:** `us-central1-a`. The originals in `networks-workshop` stay stopped. Do not start them. Playbook: [CONNECT-VMS.md](Guides%20and%20Info/CONNECT-VMS.md). Members: `yoavnm98@gmail.com` (Owner), `idozacharia@gmail.com` and `sagi151ps@gmail.com` (Editor). Editor can list, start, stop, and SSH.
- **VMs:** `topfull-master` (K8s control plane + Istio control plane + TopFull proxy/RL/metrics/RetryGuard host), `topfull-worker-1` (all Online Boutique pods, 2/2 with Envoy sidecar), `topfull-load` (Locust only)
- **SSH:** always use the OpenSSH host aliases (`topfull-master`, `topfull-worker-1`, `topfull-load`) — **never hardcode IPs**. Full setup/repair playbook: [CONNECT-VMS.md](Guides%20and%20Info/CONNECT-VMS.md) (also enforced as an always-applied Cursor rule). Use `-o ControlMaster=no` for non-interactive commands.
- **IPs are ephemeral** — they change every time a VM is stopped/started. Refresh `HostName` in `~/.ssh/config` after every restart:
  ```powershell
  gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
  ```
- **`infra/vm-ips.env`** records the live copy's names, reserved private IPs, and machine types (`SSH_USER=idozacharia`). It does not store public IPs. Your own `~/.ssh/config` `HostName` lines (per CONNECT-VMS.md) are the public addresses for this session.
- **Multi-user setup on `topfull-master`.** Several teammates have their own Linux accounts on master (`idozacharia`, `idoza`, `sagi1`, `sagi151ps`, `danielalfasi`, `galho`/`GalHo`, `yoavnm`, `user`). All Phase 5/6 tooling paths in the scenario YAMLs' `infra:` block live under **`idozacharia`**'s home (`/home/idozacharia/TopFull/...`, `/home/idozacharia/experiments/...`) — this is intentional and paths were **not** changed to keep configs stable across teammates. As of 2026-08-07, running `run_scenario.py` as any other user (e.g. `sagi1`) required three one-time fixes on master (already applied, run once — re-check after a VM rebuild/reimage, not after a normal stop/start):
  1. **Kubeconfig** — other users have no `~/.kube/config` by default (only whoever ran `kubeadm init`, i.e. `idozacharia`, has one). Fix: `sudo cp /home/idozacharia/.kube/config ~/.kube/config && sudo chown -R $(whoami) ~/.kube && chmod 600 ~/.kube/config`. Without this, `kubectl` fails with `connection to localhost:8080 refused` — **not** an API-server-down symptom, easy to misdiagnose as a cluster health issue.
  2. **Write access for non-owners** — `/home/idozacharia/experiments` and `/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs` were owner/group-only writable (`idozacharia`/`idoza`). `run_scenario.py` needs to create `experiments/results/<log_folder>/` and the TopFull processes need to write CSVs into `src/logs/`. Fixed with `sudo chmod o+w` on those two directories (not recursive — deliberately minimal).
  3. **`go` not on PATH for non-interactive shells** — `/usr/local/go/bin` was only added to `idozacharia`'s personal `~/.bashrc`, but `run_scenario.py` starts the proxy via a non-interactive shebang script (`tmux new-session -d ... /tmp/rg_proxy.sh`), which never sources `.bashrc` for *any* user (this would have silently broken the proxy step even for `idozacharia`). Fixed system-wide: `sudo ln -sf /usr/local/go/bin/go /usr/local/bin/go` (`/usr/local/bin` is in `/etc/environment`'s default `PATH`).

  Verified working end-to-end as `sagi1` after the fixes: `kubectl get nodes`, `go version`, write-tests on both directories, and `python3 -c "import ray, kubernetes"` inside `idozacharia`'s venv all succeed non-interactively.
- **Frontend sidecar CPU.** Patch `spec.template.metadata.annotations` on the frontend Deployment (a Deployment-object `kubectl annotate` does not roll the pods). The app container stays the paper **1150m**. Ron left both annotations unset, which injects request **100m** / limit **2000m**. If `proxyCPU` is set and `proxyCPULimit` is absent, the sidecar gets that request and **no** CPU limit. A limit of 90m or 100m throttles Envoy and collapses storefront latency (runs 14–25).
  - **Not pinned** (HPA min 1 / max 4): `sidecar.istio.io/proxyCPU=100m`. Leave `sidecar.istio.io/proxyCPULimit` unset.
  - **Pinned at 4 replicas:** `sidecar.istio.io/proxyCPU=90m` only, so the fourth pod schedules (a 100m request leaves the node about 10m over allocatable). Leave `proxyCPULimit` unset. Restore the unpinned pair when the hold ends.
- **Cost discipline:** stop the 3 VMs when not actively working: `gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb`. Don't stop them unless the user asks. Pass `--project` so a leftover `networks-workshop` gcloud config does not stop the originals.
- **Known fixes already applied on master** (don't revert): dynamic cAdvisor IP lookup in `resource_collector.py`; Locust 2.x event API in `locust_online_boutique.py`; LF line endings + venv locust path in the create scripts; env-var-with-default user counts in create scripts; try/except wrapper in `metric_collector.py`. Full list in PHASE5-EXPERIMENTS-GUIDE.md §7. **Also (2026-08-07 readiness):** `retryguard.py` disable path omits the `retries` block (Istio rejects `attempts:0`). `run_scenario.py` copies `retryguard.py`, `envoy_retry_collector.py`, and `resource_usage_collector.py` from this repo onto master at the start of each run (plain `cp`, then `sudo cp` if the dest file is owned by another user). Do not skip that by launching those scripts by hand from a stale master copy.

---

## 8. Key open questions this project is trying to answer

(from [Evaluating_RetryGuard_on_TopFull.md](context/Evaluating_RetryGuard_on_TopFull.md) slides 8–9 / MENTOR-COORDINATION.md — keep these in mind when interpreting results. Answerability after the 2026-08-20 audit is in [PHASE7-DATA-GAPS.md](Guides%20and%20Info/PHASE7-DATA-GAPS.md).)

- Does RetryGuard help at the **system level**, the **per-microservice level**, or both? (Mentors expect system-level gain may be small (~0.2%) while specific services improve a lot (~30%).) — **answerable** (goodput, P95, rejection).
- **Topology beneficiaries** — which services gain most from suppressed retries? — **answerable** (per-endpoint CSVs).
- **Chain propagation** — does relief at a bottleneck propagate upstream to callers? — **answerable**, coarse (only 5 Locust endpoints).
- **Controller interaction** — how do TopFull's RL loop (1s) and RetryGuard (locked 20 s window) interact/oscillate? — **partial** (`RPS` as proxy; `num_agent.csv` is empty). Recover→re-enable is the S6 load-drop (campaign complete), not flat S2.
- **Topology position sensitivity** — does RetryGuard help more where TopFull's entry-level signal is weaker (Checkout-mediated `emailservice` vs direct ProductCatalog)? — **answerable** (S4A vs S4B).

Changed from paymentservice on 2026-10-09; `campaign_48/` S4B runs used paymentservice and are not comparable.
- **Interval sensitivity** — does the paper's 30s default hold up when running alongside TopFull's 1s RL loop? — **answerable** on campaign S5 ×3 (`campaign_48/`, recovery load). August S5 remains a negative result (flat hold, never re-enabled).

---

## 9. Keeping this file useful

When you complete meaningful work (a scenario actually run, a bug fixed, a new phase closed), append one bullet to [STATUS.md](STATUS.md) Done, update Next free slots if a YAML moved, and replace the three Latest lines in §4. Keep this file's own content lean — link to the detailed guide instead of duplicating it.

---

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues in `Sagi154/topfull-retryguard-workshop`. See `docs/agents/issue-tracker.md`.

### Triage labels

Defaults: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` at the repo root and ADRs in `docs/adr/`. See `docs/agents/domain.md`.
