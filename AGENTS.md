# AGENTS.md — Context Guide for AI Agents

> **Purpose:** This file orients a new agent session on this repo: what the project is, what has been built, what state it's in *right now*, and what's left to do. Read this first, then follow the links for details. Don't duplicate this file's content elsewhere — update it as the project progresses.

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
  configs/           ← 16 scenario YAML files (S1–S4 baseline/RG, S5×4 intervals, S6 recovery baseline/RG)
  run_scenario.py    ← orchestrator, runs on Windows, drives everything over SSH
  retryguard.py      ← RetryGuard controller (deployed to master)
  envoy_retry_collector.py ← Gap 3: scrapes Envoy sidecar outbound retry counters (deployed to master)
  resource_usage_collector.py ← Layer 2: scrapes CPU/memory per service via kubelet stats/summary (deployed to master)
  mentor_charts.py / mentor_charts_data.py / mentor_charts_plots.py ← regenerate mentor-update PNGs from `campaign_48/` (`python experiments/mentor_charts.py`)
  virtual-services.yaml ← Istio VirtualService manifests (retries.attempts: 3 default)
  patch_metric_collector.py ← one-shot patcher already applied on master (see §6d in PHASE5 guide)
  results/           ← local results only (master still uses a flat `/home/idozacharia/experiments/results/`)
    campaign_48/     ← **primary Phase 7 dataset** — 48-run campaign (2026-09-05 → 2026-09-06), in git, organized into 7 scenario subfolders (`S1_normal_op/` … `S6_forced_recovery/`) — see [experiments/results/campaign_48/README.md](experiments/results/campaign_48/README.md)
    august_38/       ← historical August 38-run matrix (git-tracked; do not delete; still a flat list of run folders, not reorganized)
TopFull/             ← git submodule, upstream https://github.com/kaist-ina/TopFull (read locally; also cloned separately on the VMs)
context/             ← papers/decks: RetryGuard.pdf, TopFull.pdf, Evaluating_RetryGuard_on_TopFull.{pdf,md} (current eval deck + transcription)
canvases/            ← interactive workplan canvas for Cursor (topfull-retryguard-workplan.canvas.tsx)
infra/vm-ips.env     ← a snapshot of VM IPs/user from one teammate's session — likely STALE, see §7
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
| **[PHASE7-DATA-GAPS.md](Guides%20and%20Info/PHASE7-DATA-GAPS.md)** | **Read before analysing.** August-38 audit plus campaign close-out: Gap 1/3 **closed** on `campaign_48/`; Gap 2 dropped P99 (use P95). |
| **[PHASE7-RESOLVE-GAPS-1-3.md](Guides%20and%20Info/PHASE7-RESOLVE-GAPS-1-3.md)** | **Runbook.** Paper-grade 48-run campaign — **COMPLETE** (2026-09-06). Primary analysis is `experiments/results/campaign_48/`. Do not use `run_all_scenarios.py`. |
| [Evaluating_RetryGuard_on_TopFull.md](context/Evaluating_RetryGuard_on_TopFull.md) | **Eval plan deck** (transcription of the PDF). Slides 8–9 open questions, 11–15 scenario objectives, 16 measurement layers — source of truth for what Phase 7 is supposed to answer |
| [SCENARIOS-GUIDE.md](Guides%20and%20Info/SCENARIOS-GUIDE.md) | Understand each of the 6 scenarios in detail: what it tests, load setup, manual step-by-step (pre-dates `run_scenario.py` automation, but good for *why*) |
| **[MENTOR-UPDATE.md](Guides%20and%20Info/mentor-update/MENTOR-UPDATE.md)** | **Mentor-facing dry results** (infra, Online Boutique, scenarios, per-scenario charts + observations). Pipeline / leftover caveats: [mentor-update/README.md](Guides%20and%20Info/mentor-update/README.md) |
| [RETRYGUARD-IMPLEMENTATION.md](Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md) | Understand exactly how `experiments/retryguard.py` maps to paper Algorithm 1, its metric source, endpoint→service map, VS patch mechanics, log format |
| [NEXT-PHASES-PLAN.md](Guides%20and%20Info/NEXT-PHASES-PLAN.md) | See the presentation-track vs lab-track split and near-term suggested order |
| [PRESENTATION-GUIDE.md](Guides%20and%20Info/PRESENTATION-GUIDE.md), [PRESENTATION-ACTION-ITEMS.md](Guides%20and%20Info/PRESENTATION-ACTION-ITEMS.md), [NOTEBOOKLM-PROMPT.md](Guides%20and%20Info/NOTEBOOKLM-PROMPT.md) | Work on the slide deck / presentation track (separate from the lab track) |
| [GEMINI-PROMPT.md](GEMINI-PROMPT.md), [CANVAS-VIEWING.md](CANVAS-VIEWING.md) | Presentation-generation tooling and how to view the interactive canvas in Cursor |

---

## 4. Current status (as of 2026-09-07)

### ✅ Done

- **Phases 0–4** (accounts, VM provisioning, K8s cluster via `kubeadm`, Istio 1.17 minimal profile, dependencies, Online Boutique deployed with Envoy sidecars, `instance_scaling.py` run) — complete.
- **Experiment infrastructure** — `run_scenario.py`, `run_all_scenarios.py` (38-slot matrix), 16 YAMLs (S1–S6), RetryGuard, VirtualServices, metric_collector fix — complete (PHASE5-EXPERIMENTS-GUIDE.md §6).
- **Experiment readiness (smoke)** — Steps 1–8 passed 2026-08-07. Smoke data is **not** matrix data.
- **Phase 5 & 6 matrix (38 runs)** — complete as of 2026-08-15:
  - Slots 1–9 (S1 base×3, S1 RG×3, S2 base×3): run 2026-08-11 (Ido).
  - Slots 10–38: resumed with `run_all_scenarios.py --yes --resume 9` on 2026-08-15 (~7h); slot 17 (S3 RG run2) re-run after a permission failure on a stale master folder.
  - Batch runner bumped touched configs to next free `run_number` (typically 4 for ×3 scenarios, 3 for S5).
- **Results consolidated** — August 38 live locally under `experiments/results/august_38/` **and tracked in git** (`90c43c9` on 2026-08-20 added S1×6 and S2 baseline×3). Older “S1 on Ido’s machine / S2 baseline on master only / 29 local folders” notes are stale.
- **Results audit (2026-08-20)** — [PHASE7-DATA-GAPS.md](Guides%20and%20Info/PHASE7-DATA-GAPS.md). **30 of 38 runs are usable** (all except the 8 Scenario 5 interval runs). Three gaps found: (a) **zero `OFF→ON` events in all 23 RetryGuard runs**, so S5 has no signal and S2 never completed disable→recover→re-enable under a flat hold; (b) **`Latency99` is 0 in every row** — **resolved: P99 dropped**, report P95; (c) **no retries-per-request series** in the finished matrix — collector built, needs re-runs. Layer 2 CPU/mem was unwired in the 38-run matrix — **now instrumented** via `resource_usage_collector.py`.
- **S2 vs S6 split (2026-09-01)** — a 2026-08-20 edit had put the 900s load-drop onto S2, diverging from the deck. **S2 is again a flat 600s hold** (`run_number: 4`). The load-drop is **Scenario 6** (`scenario_6_recovery_{baseline,retryguard}.yaml`). S5 stays on S6's load and compares against **S6 baseline**, not S2. See [SCENARIOS-GUIDE.md](Guides%20and%20Info/SCENARIOS-GUIDE.md) Scenario 6.
- **Paper-grade campaign chosen (2026-09-04)** — close Gaps 1 and 3 with a **new 48-run matrix**, not a replay of the August 38 and not a 16-run collector add-on. S1, S2, S3, S4A, S4B, S6 × both arms × 3 (36) plus S5 × 4 intervals × 3 (12). All collectors on, next free `log_folder` slots. Primary Phase 7 analysis uses that campaign; the August 38 stays historical. Exact slots, gate on first S6 `OFF→ON`, and verification: [PHASE7-RESOLVE-GAPS-1-3.md](Guides%20and%20Info/PHASE7-RESOLVE-GAPS-1-3.md).
- **Eval deck transcribed** — `context/Evaluating_RetryGuard_on_TopFull.md` (from the PDF). Replaces the older project-plan pptx files.
- **Envoy retry collector (Gap 3, 2026-08-20)** — scrapes caller-side Envoy outbound retry counters via `kubectl exec` into `istio-proxy`; writes `envoy_retries_{frontend,checkoutservice}.csv`. Present in all 48 `campaign_48/` folders; **absent** from `august_38/`.
- **Resource usage collector (Layer 2)** — `experiments/resource_usage_collector.py` scrapes per-service CPU/memory via kubelet `stats/summary`; wired into `run_scenario.py`. Present in all 48 `campaign_48/` folders; **absent** from `august_38/`.
- **Pre-campaign metric verification PASSED (2026-09-04)** — S6 baseline + RetryGuard run1 with traffic. Folders: `baseline_topfull_no_retryguard_forced_recovery_run1`, `run_topfull_retryguard_forced_recovery_run1`. Confirmed: Locust 1s CSVs; Envoy `max_retry>0` on baseline frontend; `resource_usage.csv`; 3× `ON→OFF` then 3× `OFF→ON` on RetryGuard (Gap 1 signal live). See [PHASE7-RESOLVE-GAPS-1-3.md](Guides%20and%20Info/PHASE7-RESOLVE-GAPS-1-3.md) §3b.
- **Paper-grade 48-run campaign COMPLETE (2026-09-05 → 2026-09-06)** — all 48 slots local under `experiments/results/campaign_48/`: S6 run1–3 both arms; S5 intervals run3–5 (×4); S1–S4A/S4B run4–6 both arms. Every run pulled and §4-verified (Locust + Envoy + `resource_usage`; RetryGuard toggles where applicable). S6/S5 produced `OFF→ON`; flat S2/S3/S4 typically disable-only. S1 RG showed unexpected checkout `ON→OFF` on all 3 repeats. August 38 is `experiments/results/august_38/`. Primary Phase 7 analysis uses the campaign. Gaps 1 and 3 **closed** on that dataset — [PHASE7-DATA-GAPS.md](Guides%20and%20Info/PHASE7-DATA-GAPS.md).
- **Local results layout (2026-09-06)** — `experiments/results/campaign_48/` vs `experiments/results/august_38/`. Both are in git. Master still uses a flat `/home/idozacharia/experiments/results/<log_folder>/`. See [experiments/results/README.md](experiments/results/README.md).
- **Mentor update doc (2026-09-06 → 2026-09-07)** — [MENTOR-UPDATE.md](Guides%20and%20Info/mentor-update/MENTOR-UPDATE.md) is the dry Phase 7 readout (infra, Online Boutique, scenarios, per-scenario charts with factual observations, no conclusions). Charts come from `campaign_48/` via `python experiments/mentor_charts.py`: Locust comparison plots are **mean-only** (no min/max bands), downsampled to **5 s** steps, with `ON→OFF` / `OFF→ON` overlays from **every** RetryGuard repeat; every scenario section embeds the S2-style set (goodput / P95 / rejection / frontend retries-per-target / CPU / memory). Pipeline leftovers (collector clocks ≠ Locust t0; no toggle overlays on CPU/retries multi-line charts; Locust `charts_gallery/` = curated) live in [mentor-update/README.md](Guides%20and%20Info/mentor-update/README.md) — not in the mentor doc.

### ❌ Not done yet — remaining work

> **Next session — do this first:** Share [MENTOR-UPDATE.md](Guides%20and%20Info/mentor-update/MENTOR-UPDATE.md) with mentors, then write the Phase 7 evaluation/report on **`experiments/results/campaign_48/`** once they say what's sufficient ([PHASE7-DATA-GAPS.md](Guides%20and%20Info/PHASE7-DATA-GAPS.md), [METRICS-COLLECTION-GUIDE.md](Guides%20and%20Info/METRICS-COLLECTION-GUIDE.md)). Do not overwrite `august_38/`. Chart-pipeline leftovers stay in [mentor-update/README.md](Guides%20and%20Info/mentor-update/README.md).
>
> **Do not re-run Scenario 6 until the YAMLs are bumped.** Both `experiments/configs/scenario_6_recovery_{baseline,retryguard}.yaml` still point at completed **`run3`**. Launching them as-is overwrites that folder **on master**. Bump `run_number` and `log_folder` to **run4** first. S1–S5 already sit on the next free slot (run7 / S5 run6).

Optional: stop the 3 VMs when not analysing (`gcloud compute instances stop …`) to save cost.

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
| 1 | Normal Operation | Flat load, well within capacity | 5 min | `scenario_1_{baseline,retryguard}.yaml` |
| 2 | Sustained Overload (core) | Peak from t=0, **hold flat** | 10 min | `scenario_2_{baseline,retryguard}.yaml` |
| 3 | Targeted Bottleneck | `checkoutservice` CPU-limited to `100m` | 10 min | `scenario_3_{baseline,retryguard}.yaml` |
| 4A/4B | Topology Position | `productcatalogservice` (A) vs `paymentservice` (B) CPU-limited | 10 min | `scenario_4{a,b}_{baseline,retryguard}.yaml` |
| 5 | Re-enable Interval Tuning | Same load as S6; `re_enable_windows` = 1/2/3/6 | 15 min | `scenario_5_interval_{10,20,30,60}s.yaml` |
| 6 | Forced Recovery | Peak 5 min, then ~25% load for 10 min | 15 min | `scenario_6_recovery_{baseline,retryguard}.yaml` |

Note: since all Boutique services run at **1 replica**, Scenarios 3/4 constrain via `method: cpu_limit` (kubectl patch), not replica scaling. Scenario 5's 8 August matrix runs (`august_38/`) have **no re-enable events** (they used a flat hold). Campaign S5 (`campaign_48/`, S6's load) **did** re-enable; compare against **S6 baseline**, not S2. August Scenario 2 run1–3 remain historical; campaign S2 run4–6 is the primary flat-hold dataset.

---

## 6. How to run an experiment (once cluster is confirmed healthy)

```powershell
pip install pyyaml   # once

# Before every run: clear stale /tmp runner scripts.
# /tmp has a sticky bit — if a previous run was by a different Linux user, their
# files block SCP uploads. sudo rm is a no-op when files don't exist.
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_locust_launch.sh"

python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
```

The runner handles everything end-to-end, including copying `retryguard.py`, `envoy_retry_collector.py`, and `resource_usage_collector.py` from this repo onto master before those processes start. Results go to `results_base_path/<log_folder>/` **on master**. The runner's printed `scp` command already routes to the correct `campaign_48/<scenario_subfolder>/` (e.g. `S2_sustained_overload/`) based on the scenario — see [experiments/results/campaign_48/README.md](experiments/results/campaign_48/README.md).

**Before repeating a scenario:** bump `run_number` and change `log_folder` in the YAML, or the new run will overwrite the folder **on master**. Completed campaign slots are run4–6 (S1–S4), run3–5 (S5), run1–3 (S6). S1–S5 YAMLs already point at the next free slot (run7 / S5 run6); **S6 YAMLs still point at completed run3 — bump to run4 before any extra S6 run.** Never reuse August `run1–3` (S1–S4) or S5 `run1–2`.

Full config schema, `scale_constraints` methods, and troubleshooting: [PHASE5-EXPERIMENTS-GUIDE.md](Guides%20and%20Info/PHASE5-EXPERIMENTS-GUIDE.md) §5 and [experiments/README.md](experiments/README.md).

---

## 7. Infrastructure facts an agent needs

- **Project:** `networks-workshop` · **Zone:** `us-central1-a`
- **VMs:** `topfull-master` (K8s control plane + Istio control plane + TopFull proxy/RL/metrics/RetryGuard host), `topfull-worker-1` (all Online Boutique pods, 2/2 with Envoy sidecar), `topfull-load` (Locust only)
- **SSH:** always use the OpenSSH host aliases (`topfull-master`, `topfull-worker-1`, `topfull-load`) — **never hardcode IPs**. Full setup/repair playbook: [CONNECT-VMS.md](Guides%20and%20Info/CONNECT-VMS.md) (also enforced as an always-applied Cursor rule). Use `-o ControlMaster=no` for non-interactive commands.
- **IPs are ephemeral** — they change every time a VM is stopped/started. Refresh `HostName` in `~/.ssh/config` after every restart:
  ```powershell
  gcloud compute instances list --project=networks-workshop --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
  ```
- **`infra/vm-ips.env`** is a static snapshot (from a teammate, `SSH_USER=idozacharia`) — treat it as historical reference only, not a live source of truth. Your own `~/.ssh/config` (per CONNECT-VMS.md, discovered per-machine) is authoritative for your session.
- **Multi-user setup on `topfull-master`.** Several teammates have their own Linux accounts on master (`idozacharia`, `idoza`, `sagi1`, `sagi151ps`, `danielalfasi`, `galho`/`GalHo`, `yoavnm`, `user`). All Phase 5/6 tooling paths in the scenario YAMLs' `infra:` block live under **`idozacharia`**'s home (`/home/idozacharia/TopFull/...`, `/home/idozacharia/experiments/...`) — this is intentional and paths were **not** changed to keep configs stable across teammates. As of 2026-08-07, running `run_scenario.py` as any other user (e.g. `sagi1`) required three one-time fixes on master (already applied, run once — re-check after a VM rebuild/reimage, not after a normal stop/start):
  1. **Kubeconfig** — other users have no `~/.kube/config` by default (only whoever ran `kubeadm init`, i.e. `idozacharia`, has one). Fix: `sudo cp /home/idozacharia/.kube/config ~/.kube/config && sudo chown -R $(whoami) ~/.kube && chmod 600 ~/.kube/config`. Without this, `kubectl` fails with `connection to localhost:8080 refused` — **not** an API-server-down symptom, easy to misdiagnose as a cluster health issue.
  2. **Write access for non-owners** — `/home/idozacharia/experiments` and `/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs` were owner/group-only writable (`idozacharia`/`idoza`). `run_scenario.py` needs to create `experiments/results/<log_folder>/` and the TopFull processes need to write CSVs into `src/logs/`. Fixed with `sudo chmod o+w` on those two directories (not recursive — deliberately minimal).
  3. **`go` not on PATH for non-interactive shells** — `/usr/local/go/bin` was only added to `idozacharia`'s personal `~/.bashrc`, but `run_scenario.py` starts the proxy via a non-interactive shebang script (`tmux new-session -d ... /tmp/rg_proxy.sh`), which never sources `.bashrc` for *any* user (this would have silently broken the proxy step even for `idozacharia`). Fixed system-wide: `sudo ln -sf /usr/local/go/bin/go /usr/local/bin/go` (`/usr/local/bin` is in `/etc/environment`'s default `PATH`).

  Verified working end-to-end as `sagi1` after the fixes: `kubectl get nodes`, `go version`, write-tests on both directories, and `python3 -c "import ray, kubernetes"` inside `idozacharia`'s venv all succeed non-interactively.
- **Cost discipline:** stop the 3 VMs when not actively working: `gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a`. Don't stop them unless the user asks.
- **Known fixes already applied on master** (don't revert): dynamic cAdvisor IP lookup in `resource_collector.py`; Locust 2.x event API in `locust_online_boutique.py`; LF line endings + venv locust path in the create scripts; env-var-with-default user counts in create scripts; try/except wrapper in `metric_collector.py`. Full list in PHASE5-EXPERIMENTS-GUIDE.md §7. **Also (2026-08-07 readiness):** `retryguard.py` disable path omits the `retries` block (Istio rejects `attempts:0`). `run_scenario.py` copies `retryguard.py`, `envoy_retry_collector.py`, and `resource_usage_collector.py` from this repo onto master at the start of each run (plain `cp`, then `sudo cp` if the dest file is owned by another user). Do not skip that by launching those scripts by hand from a stale master copy.

---

## 8. Key open questions this project is trying to answer

(from [Evaluating_RetryGuard_on_TopFull.md](context/Evaluating_RetryGuard_on_TopFull.md) slides 8–9 / MENTOR-COORDINATION.md — keep these in mind when interpreting results. Answerability after the 2026-08-20 audit is in [PHASE7-DATA-GAPS.md](Guides%20and%20Info/PHASE7-DATA-GAPS.md).)

- Does RetryGuard help at the **system level**, the **per-microservice level**, or both? (Mentors expect system-level gain may be small (~0.2%) while specific services improve a lot (~30%).) — **answerable** (goodput, P95, rejection).
- **Topology beneficiaries** — which services gain most from suppressed retries? — **answerable** (per-endpoint CSVs).
- **Chain propagation** — does relief at a bottleneck propagate upstream to callers? — **answerable**, coarse (only 5 Locust endpoints).
- **Controller interaction** — how do TopFull's RL loop (1s) and RetryGuard (30s windows) interact/oscillate? — **partial** (`RPS` as proxy; `num_agent.csv` is empty). Recover→re-enable is the S6 load-drop (campaign complete), not flat S2.
- **Topology position sensitivity** — does RetryGuard help more where TopFull's entry-level signal is weaker (Checkout-mediated Payment vs direct ProductCatalog)? — **answerable** (S4A vs S4B).
- **Interval sensitivity** — does the paper's 30s default hold up when running alongside TopFull's 1s RL loop? — **answerable** on campaign S5 ×3 (`campaign_48/`, recovery load). August S5 remains a negative result (flat hold, never re-enabled).

---

## 9. Keeping this file useful

When you complete meaningful work (a scenario actually run, a bug fixed, a new phase closed), update §4 ("Current status") so the next agent doesn't have to re-derive it from git log and guide files. Keep this file's own content lean — link to the detailed guide instead of duplicating it.
