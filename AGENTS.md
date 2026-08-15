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

We run **5 scenarios** (see §5) under both conditions, ≥3 repeats each (Locust traffic is non-deterministic), then compare goodput / P99 latency / rejection rate / retries-per-request / CPU-mem / RetryGuard toggle events.

This is a workshop deliverable: a presentation (project plan) + eventually a written report with the above comparison.

---

## 2. Repo layout

```
Guides and Info/     ← all human-facing docs (see §3 — start here for "why")
experiments/         ← the actual tooling: runner, scenario configs, RetryGuard controller
  configs/           ← 14 scenario YAML files (5 scenarios × baseline/retryguard, +4 interval variants)
  run_scenario.py    ← orchestrator, runs on Windows, drives everything over SSH
  retryguard.py      ← RetryGuard controller (deployed to master)
  virtual-services.yaml ← Istio VirtualService manifests (retries.attempts: 3 default)
  patch_metric_collector.py ← one-shot patcher already applied on master (see §6d in PHASE5 guide)
  results/           ← Phase 5/6 matrix CSVs (29 folders locally as of 2026-08-15; S1 still on Ido’s machine)
TopFull/             ← git submodule, upstream https://github.com/kaist-ina/TopFull (read locally; also cloned separately on the VMs)
context/             ← papers/decks: RetryGuard.pdf, TopFull.pdf, project-plan pptx files
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
| [WORKPLAN.md](Guides%20and%20Info/WORKPLAN.md) | See the full Phase 0–7 plan with Why/How/Done-when for each step (mostly complete — Phases 0–4 done) |
| [SETUP-GUIDE.md](Guides%20and%20Info/SETUP-GUIDE.md) | Get exact commands for cluster/Istio/dependency setup, if something needs to be rebuilt |
| [MANAGED-KUBERNETES.md](Guides%20and%20Info/MANAGED-KUBERNETES.md) | Understand why we used self-managed `kubeadm` K8s instead of GKE (decision already made — not adopted) |
| [CONNECT-VMS.md](Guides%20and%20Info/CONNECT-VMS.md) | **SSH into the VMs.** Canonical playbook — also mirrored in `.cursor/rules/topfull-ssh.mdc` (always-applied) |
| **[PHASE5-EXPERIMENTS-GUIDE.md](Guides%20and%20Info/PHASE5-EXPERIMENTS-GUIDE.md)** | Canonical reference for the experiment runner + scenario config system. Read before touching `experiments/` |
| **[PHASE5-PHASE6-RUNLIST.md](Guides%20and%20Info/PHASE5-PHASE6-RUNLIST.md)** | **Matrix checklist + where results live.** All 38 runs marked done as of 2026-08-15; start here for inventory / gaps before Phase 7 |
| [EXPERIMENT-READINESS-WORKPLAN.md](Guides%20and%20Info/EXPERIMENT-READINESS-WORKPLAN.md) | Historical smoke-validation checklist (Steps 1–8 passed 2026-08-07). Do not mix smoke folders into Phase 7 analysis |
| [METRICS-COLLECTION-GUIDE.md](Guides%20and%20Info/METRICS-COLLECTION-GUIDE.md) | **Next for Phase 7.** What each run produces, how to pull/verify, how to load for charts |
| [SCENARIOS-GUIDE.md](Guides%20and%20Info/SCENARIOS-GUIDE.md) | Understand each of the 5 scenarios in detail: what it tests, load setup, manual step-by-step (pre-dates `run_scenario.py` automation, but good for *why*) |
| [RETRYGUARD-IMPLEMENTATION.md](Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md) | Understand exactly how `experiments/retryguard.py` maps to paper Algorithm 1, its metric source, endpoint→service map, VS patch mechanics, log format |
| [NEXT-PHASES-PLAN.md](Guides%20and%20Info/NEXT-PHASES-PLAN.md) | See the presentation-track vs lab-track split and near-term suggested order |
| [PRESENTATION-GUIDE.md](Guides%20and%20Info/PRESENTATION-GUIDE.md), [PRESENTATION-ACTION-ITEMS.md](Guides%20and%20Info/PRESENTATION-ACTION-ITEMS.md), [NOTEBOOKLM-PROMPT.md](Guides%20and%20Info/NOTEBOOKLM-PROMPT.md) | Work on the slide deck / presentation track (separate from the lab track) |
| [GEMINI-PROMPT.md](GEMINI-PROMPT.md), [CANVAS-VIEWING.md](CANVAS-VIEWING.md) | Presentation-generation tooling and how to view the interactive canvas in Cursor |

---

## 4. Current status (as of 2026-08-16)

### ✅ Done

- **Phases 0–4** (accounts, VM provisioning, K8s cluster via `kubeadm`, Istio 1.17 minimal profile, dependencies, Online Boutique deployed with Envoy sidecars, `instance_scaling.py` run) — complete.
- **Experiment infrastructure** — `run_scenario.py`, `run_all_scenarios.py` (38-slot matrix), 14 YAMLs, RetryGuard, VirtualServices, metric_collector fix — complete (PHASE5-EXPERIMENTS-GUIDE.md §6).
- **Experiment readiness (smoke)** — Steps 1–8 passed 2026-08-07. Smoke data is **not** matrix data.
- **Phase 5 & 6 matrix (38 runs)** — complete as of 2026-08-15:
  - Slots 1–9 (S1 base×3, S1 RG×3, S2 base×3): run 2026-08-11 (Ido); S1 folders still on Ido’s machine.
  - Slots 10–38: resumed with `run_all_scenarios.py --yes --resume 9` on 2026-08-15 (~7h); slot 17 (S3 RG run2) re-run after a permission failure on a stale master folder.
  - Local `experiments/results/`: 29 matrix folders (S2 RG, S3, S4A/B, S5). Master also has S2 baseline×3 (not yet pulled to this laptop).
  - Batch runner bumped touched configs to next free `run_number` (typically 4 for ×3 scenarios, 3 for S5).

### ❌ Not done yet — remaining work

1. **Consolidate results for Phase 7:** copy S1×6 from Ido; optionally `scp` S2 baseline×3 from master → `experiments/results/`.
2. **Phase 7 — evaluation + report.** Time-series charts (baseline vs RetryGuard); written report on the open questions (§8). **Known gap:** per-run CPU/mem/`num_instances.csv` from `resource_collector.py` are not written into results (in-memory RL only) — wire or drop before relying on resource charts.

**Recommended order:** gather missing result folders → Phase 7 analysis per [METRICS-COLLECTION-GUIDE.md](Guides%20and%20Info/METRICS-COLLECTION-GUIDE.md).

### ⚠️ Live infra caveat (check before assuming the cluster is healthy)

The 3 VMs can be stopped/started between sessions (to save cost) and IPs are ephemeral. Last time this was checked (see §7), the VMs were `RUNNING` but `kubectl` on master returned `connection to localhost:8080 refused` — the API server hadn't come back up yet after a restart, even though `kubelet`/`docker`/`cri-docker` services were all `active`. This is most likely just "static pods still booting" — **always re-verify cluster health at the start of a session** rather than assuming it's still in the last-known-good state:

```powershell
ssh topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

If it doesn't recover within a few minutes, follow the troubleshooting table in SETUP-GUIDE.md / CONNECT-VMS.md. **Correction to that earlier diagnosis:** the actual cause turned out to be a missing `~/.kube/config` for the SSH user, not the API server booting — see the multi-user note in §7.

---

## 5. The 5 scenarios (quick reference — full detail in SCENARIOS-GUIDE.md / PHASE5-EXPERIMENTS-GUIDE.md)

| # | Name | What changes | Duration | Config files |
|---|---|---|---|---|
| 1 | Normal Operation | Flat load, well within capacity | 5 min | `scenario_1_{baseline,retryguard}.yaml` |
| 2 | Sustained Overload (core) | Ramp to ρ>1, hold | 10 min | `scenario_2_{baseline,retryguard}.yaml` |
| 3 | Targeted Bottleneck | `checkoutservice` CPU-limited to `100m` | 10 min | `scenario_3_{baseline,retryguard}.yaml` |
| 4A/4B | Topology Position | `productcatalogservice` (A) vs `paymentservice` (B) CPU-limited | 10 min | `scenario_4{a,b}_{baseline,retryguard}.yaml` |
| 5 | Re-enable Interval Tuning | RetryGuard `re_enable_windows` = 1/2/3/6 (10/20/30/60s) | 10 min | `scenario_5_interval_{10,20,30,60}s.yaml` |

Note: since all Boutique services run at **1 replica**, Scenarios 3/4 constrain via `method: cpu_limit` (kubectl patch), not replica scaling.

---

## 6. How to run an experiment (once cluster is confirmed healthy)

```powershell
pip install pyyaml   # once

# Before every run: clear stale /tmp runner scripts.
# /tmp has a sticky bit — if a previous run was by a different Linux user, their
# files block SCP uploads. sudo rm is a no-op when files don't exist.
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_locust_launch.sh"

python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
```

The runner handles everything end-to-end and writes results to `results_base_path/<log_folder>/` **on master**. Pull them down with:

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/<log_folder> experiments/results/
```

**Before repeating a scenario:** bump `run_number` and change `log_folder` in the YAML (e.g. `..._run1` → `..._run2`), or the new run will overwrite/mix with the old one.

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
- **Known fixes already applied on master** (don't revert): dynamic cAdvisor IP lookup in `resource_collector.py`; Locust 2.x event API in `locust_online_boutique.py`; LF line endings + venv locust path in the create scripts; env-var-with-default user counts in create scripts; try/except wrapper in `metric_collector.py`. Full list in PHASE5-EXPERIMENTS-GUIDE.md §7. **Also (2026-08-07 readiness):** `retryguard.py` disable path omits the `retries` block (Istio rejects `attempts:0`); keep the master copy in sync with `experiments/retryguard.py` (file may need `sudo cp` — directory is o+w but the file itself may not be).

---

## 8. Key open questions this project is trying to answer

(from MENTOR-COORDINATION.md / SCENARIOS-GUIDE.md — keep these in mind when interpreting results)

- Does RetryGuard help at the **system level**, the **per-microservice level**, or both? (Mentors expect system-level gain may be small (~0.2%) while specific services improve a lot (~30%).)
- **Topology beneficiaries** — which services gain most from suppressed retries?
- **Chain propagation** — does relief at a bottleneck propagate upstream to callers?
- **Controller interaction** — how do TopFull's RL loop (1s) and RetryGuard (30s windows) interact/oscillate?
- **Topology position sensitivity** — does RetryGuard help more where TopFull's entry-level signal is weaker (Checkout-mediated Payment vs direct ProductCatalog)?
- **Interval sensitivity** — does the paper's 30s default hold up when running alongside TopFull's faster RL loop?

---

## 9. Keeping this file useful

When you complete meaningful work (a scenario actually run, a bug fixed, a new phase closed), update §4 ("Current status") so the next agent doesn't have to re-derive it from git log and guide files. Keep this file's own content lean — link to the detailed guide instead of duplicating it.
