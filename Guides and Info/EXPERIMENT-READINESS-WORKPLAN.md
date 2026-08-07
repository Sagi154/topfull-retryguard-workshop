# Experiment Readiness Workplan

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Scope:** This is the step *between* "Phase 5/6 tooling is built" and "we run the full battery of Phase 5/6 scenarios for real." It answers one question: **can we trust `run_scenario.py` + the 14 configs in `experiments/configs/` to produce correct, readable data before we spend VM-hours on the real multi-run experiment matrix?**
>
> This is **not** the real experiment run. Don't record these runs as Phase 5/6 results — they exist to validate the pipeline. Once every checklist item below is ✅, we move on to executing the actual scenario matrix (PHASE5-EXPERIMENTS-GUIDE.md §2, SCENARIOS-GUIDE.md).
>
> Canonical references: [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md), [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md), [experiments/README.md](../experiments/README.md), [AGENTS.md](../AGENTS.md).

---

## Why this step exists

The tooling (runner, 14 YAML configs, RetryGuard controller, VirtualServices) is built and documented as done, but as of 2026-08-07 **zero experiment runs have actually completed** — `experiments/results/` is empty both locally and on master. Separately, running as a different Linux user than the one who built the stack (`idozacharia`) just surfaced three real environment bugs (missing kubeconfig, non-writable output paths, `go` not on the non-interactive `PATH`) that would have silently broken a real run. That means **"the code is written" ≠ "the pipeline works."** This workplan closes that gap cheaply (short/cheap runs) before we commit to the full ≥3-repeats-per-scenario matrix (which is 10+ minutes × dozens of runs of VM time).

---

## Definition of Ready (exit criteria)

We are ready to start the real Phase 5/6 matrix when **all** of the following are true:

- [x] Cluster, Istio, and Online Boutique are confirmed healthy from a cold check (not assumed from a previous session).
- [x] `run_scenario.py` completes one full baseline run end-to-end with no manual intervention, and the collected CSVs contain real, sane data.
- [x] `run_scenario.py` completes one full RetryGuard run end-to-end, RetryGuard logs are produced, and Scenario 1 shows **zero** VirtualService patches (threshold calibration check).
- [x] At least one overload scenario proves RetryGuard actually toggles retries **and** that TopFull's proxy/RL loop keeps running correctly while it does — with the toggle visible both in `retryguard.log` and via `kubectl get virtualservice`.
- [x] Topology-constraint scenarios (3/4) prove the constrain → run → restore cycle leaves the cluster in its original state.
- [x] All 14 configs in `experiments/configs/` have been read end-to-end for internal consistency (no stale comments, no colliding `log_folder` names, sane `infra:` values, deployments/containers that actually exist).
- [x] We know how to pull results to a PC and can open a CSV and correctly explain every column.
- [x] The "repeat a run" mechanic (`run_number` + `log_folder` bump) has been exercised at least once and doesn't silently overwrite data.

---

## Step 1 — Cold cluster health check

Don't trust the last-known state from a previous session — VMs stop/start and IPs/health can change.

```bash
ssh topfull-master "kubectl get nodes; kubectl get pods -n default -o wide; kubectl get virtualservices -n default; kubectl get pods -n istio-system"
ssh topfull-master "curl -I http://localhost:30440"
```

**Done when:**
- Both nodes `Ready`.
- All 12 Online Boutique pods `2/2 Running` (app + Envoy sidecar).
- 10 VirtualServices present (`adservice`, `cartservice`, `checkoutservice`, `currencyservice`, `emailservice`, `frontend`, `paymentservice`, `productcatalogservice`, `recommendationservice`, `shippingservice`).
- `istiod` `Running`.
- Frontend returns HTTP 200.

---

## Step 2 — Access/environment readiness for whoever is running the experiments

If a teammate other than `idozacharia` is driving `run_scenario.py`, they need (see [AGENTS.md](../AGENTS.md) §7 for the fix already applied for `sagi1`):

- [x] `~/.kube/config` present and working (`kubectl get nodes` succeeds as that user).
- [x] Write access to `/home/idozacharia/experiments` and `/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs`.
- [x] `go` reachable in a **non-interactive** shell (`ssh host "go version"` — not just an interactive login shell): confirms the proxy launch step in `start_master_stack()` won't silently fail.
- [x] Shared venv importable: `python3 -c "import ray, kubernetes"` after `source /home/idozacharia/TopFull/venv/bin/activate`.

**Done when:** all four checks pass non-interactively for the account that will run the experiments.

---

## Step 3 — Config audit (`experiments/configs/*.yaml`)

Read all 14 files, not just the ones about to be run. Look for:

| Check | Why |
|---|---|
| No stale/contradictory comments (e.g. found: `scenario_1_baseline.yaml` claimed `user_counts` were "NOT yet applied" — false, already fixed in §6a; comment has been corrected) | Stale comments cause someone to mistrust or misconfigure a working feature |
| `log_folder` is unique per scenario **and** condition, and matches the naming convention in SCENARIOS-GUIDE.md (`baseline_topfull_no_retryguard_<scenario>_run<N>` / `run_topfull_retryguard_<scenario>_run<N>`) | Colliding folder names silently merge/overwrite results across runs |
| `infra:` block is identical and correct across all 14 files (`master_ssh_host`, `loadgen_ssh_host`, and the four `/home/idozacharia/...` paths) | One typo'd config would fail deep into a run, wasting VM time |
| `scale_constraints[].deployment` names exist as real K8s Deployments, and `container: server` matches the actual container name inside that pod | `kubectl patch`/`kubectl scale` on a wrong name fails silently or targets the wrong thing |
| `retryguard.*` params are identical across all scenarios **except** the deliberate Scenario 5 `re_enable_windows` sweep (1/2/3/6) | Confirms Scenario 5 is the only place we intentionally vary the interval |
| `duration_seconds` matches what SCENARIOS-GUIDE.md / PHASE5-EXPERIMENTS-GUIDE.md documents per scenario (300s for S1, 600s for S2–5) | Catches silent copy-paste errors between scenario files |
| `run_number: 1` in every file (none accidentally left at a stale higher number from a previous edit) | Confirms configs are in their "not yet run" state |

**Done when:** a reviewer has opened every file in `experiments/configs/` at least once since the last tooling change, and any issues found are fixed and noted here (append to the log at the bottom of this file).

---

## Step 4 — Smoke test A: Scenario 1 baseline (cheapest full pipeline run)

Run the shortest scenario (5 min) as a full pipeline dry run:

```powershell
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
```

Watch the runner's own output for each stage (it prints step-by-step); don't just wait for "Done":

- Pre-flight passes (SSH to both VMs, nodes Ready, pods Running).
- Old logs cleared.
- `tmux` sessions `proxy`, `toprl`, `metrics` all start; the runner's own check confirms `deploy_rl.py` is actually running (not just that tmux started).
- Locust processes come up on loadgen (`pgrep -c locust` > 0).
- Progress bar runs for the full 300s.
- Clean stop of Locust + master processes.
- Results collected to `/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_normal_op_run1/` on master, with a `run_manifest.json`.

Pull results and inspect:

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_normal_op_run1 experiments/results/
```

Open the CSVs (`getproduct.csv`, `postcheckout.csv`, `getcart.csv`, `postcart.csv`, `emptycart.csv`). Each row is one 1-second sample with columns:

```
RPS, Fail, Goodput, Latency95, Latency99
```
(`Goodput = RPS - Fail`; written by `metric_collector.py::record_online_boutique()`.)

**Done when:**
- CSVs are non-empty, `RPS` is consistently > 0 for the run's duration (proves Locust traffic was actually flowing and being measured).
- `Fail` stays low/near-zero throughout (this is the "normal operation" sanity scenario — high failures here would mean something is mis-tuned before we even get to overload scenarios).
- `run_manifest.json` correctly reflects the config that was used.

---

## Step 5 — Smoke test B: Scenario 1 with RetryGuard (threshold calibration check)

```powershell
python experiments/run_scenario.py experiments/configs/scenario_1_retryguard.yaml
```

This is the paper-mandated sanity check: RetryGuard must be a no-op under healthy load.

**Done when:**
- `retryguard.log` (in the collected results) exists and contains `OBSERVE` lines for the services in `ENDPOINT_SERVICE_MAP` (`cartservice`, `checkoutservice`, `productcatalogservice`).
- **Zero** `ON→OFF` / `OFF→ON` toggle lines.
- Goodput/latency/rejection CSVs are statistically similar to Step 4's baseline run (same load, so numbers should be close).

If RetryGuard fires here, **stop** — do not proceed to overload scenarios until the threshold/metric wiring is understood and fixed (see RETRYGUARD-IMPLEMENTATION.md).

---

## Step 6 — Smoke test C: prove RetryGuard actually toggles (Scenario 3, one baseline + one RetryGuard run)

Scenario 3 (Targeted Bottleneck, `checkoutservice` CPU-capped to `100m`) is the cheapest scenario that should reliably trigger RetryGuard, since the constraint is deterministic (not dependent on ramping Locust just right like Scenario 2).

```powershell
python experiments/run_scenario.py experiments/configs/scenario_3_baseline.yaml
# inspect, then:
python experiments/run_scenario.py experiments/configs/scenario_3_retryguard.yaml
```

While the RetryGuard run is in progress, optionally tail the controller live:
```bash
ssh topfull-master "tmux attach -t retryguard"   # Ctrl+B, D to detach without killing it
```

**Done when:**
- Baseline run: `checkoutservice`/`postcheckout` rejection rate visibly elevated in the CSVs (proves the CPU constraint actually created overload).
- RetryGuard run: `retryguard.log` shows at least one `checkoutservice ON→OFF` and later `OFF→ON` pair with real timestamps.
- Cross-check the toggle actually happened at the mesh level: `kubectl get virtualservice checkoutservice -o jsonpath='{.spec.http[0].retries}'` reflects `attempts: 0` while disabled (check during the run) and `attempts: 3` after re-enable.
- After both runs finish, confirm the CPU-limit constraint was fully restored: `kubectl get deployment checkoutservice -o jsonpath='{.spec.template.spec.containers[0].resources}'` shows no lingering `100m` limit.

---

## Step 7 — Repeat-run mechanics check

Pick any config already run above, bump `run_number: 1` → `2` and `log_folder` suffix `_run1` → `_run2`, and run it again.

**Done when:** both `_run1` and `_run2` folders exist independently on master (and after pulling, locally) with no data loss/overwrite, confirming the manual bump convention documented in PHASE5-EXPERIMENTS-GUIDE.md §5 ("Repeating runs") is safe to rely on for the real multi-run matrix.

*(Optional improvement, not blocking: consider a small wrapper script that auto-increments `run_number`/`log_folder` instead of manual editing, to remove a class of human error before running dozens of repeats. Defer unless manual editing proves error-prone in practice.)*

---

## Step 8 — Data usability sanity check

Before trusting this pipeline for the real experiment, confirm we can actually answer the project's questions from the data it produces:

- [x] From a Scenario 3 RetryGuard run's CSVs + `retryguard.log`, manually reconstruct one disable→recover→re-enable cycle by timestamp (goodput dip → RetryGuard fires → goodput recovers). This proves Layer 1 (API metrics) and Layer 3 (controller log) can be cross-referenced, which every scenario's analysis in Phase 7 depends on.
- [x] Confirm `resource_collector.py`'s output (CPU/mem/`num_instances.csv` via cAdvisor) is also being written during these runs — it's "always collected" per PHASE5-EXPERIMENTS-GUIDE.md §4 but isn't explicitly started/stopped by `run_scenario.py` today; verify it's actually running (check current process/cron/tmux state on master) or note as a gap to fix before Phase 7.

**Done when:** both checks pass, or gaps are explicitly logged in the run log below for follow-up before Phase 7.

---

## Run log (fill in as steps are executed)

| Date | Step | Config | Result | Notes / issues found |
|---|---|---|---|---|
| 2026-08-07 | 1 | — | PASS | Nodes Ready; 12 Boutique pods 2/2; 10 VS; istiod Running; frontend HTTP 200. |
| 2026-08-07 | 2 | — | PASS | As `sagi1`: kubectl/go/write/venv all OK non-interactively. |
| 2026-08-07 | 3 | all 14 configs | PASS (1 fix) | Values consistent. Fixed stale S5 `interval_10s` comment (`1×30s=10s` → `=30s` per PHASE5 table). Folder labels 10/20/30/60s are historical; effective waits are 30/60/90/180s. |
| 2026-08-07 | 4 | `scenario_1_baseline` run1 | PASS (after runner fix) | First attempt failed: `pgrep -la deploy_rl.py` doesn't match `python3 deploy_rl.py`. Fixed to `pgrep -fa`. Also hardened `pkill -f` patterns (self-match footgun). CSVs: 273 rows, Fail=0, total goodput≈390. |
| 2026-08-07 | 5 | `scenario_1_retryguard` run1 | PASS | 30 OBSERVE lines; zero toggles; total goodput within 0.1% of baseline. |
| 2026-08-07 | 6 | `scenario_3_{baseline,retryguard}` run1 | PASS (after 2 fixes) | (1) `cpu_limit` patch failed: request 500m > limit 100m — runner now sets requests=limits and restores full original resources. Baseline postcheckout rej≈97%. (2) RetryGuard `attempts:0` rejected by Istio webhook — disable now omits `retries` block. Live ON→OFF at 13:50:00Z; VS had no retries; `deploy_rl` stayed up. OFF→ON did not fire under sustained 100m overload (rej stayed ~99%); algorithmic OFF→ON + VS restore proven post-run. Runner now restores all VS retries at end of RetryGuard runs. |
| 2026-08-07 | 7 | `scenario_1_baseline` run2 | PASS | `_run1` and `_run2` coexist on master and locally; manifests match; no overwrite. Smoke-used configs bumped so real matrix starts at next free run#. |
| 2026-08-07 | 8 | S3 RetryGuard results | PASS w/ gap | Layer1↔Layer3 cross-ref works (ON→OFF aligns with ~100% postcheckout Fail/Goodput≈0). **Gap:** `resource_collector.py` is imported by `overload_detection` for in-memory RL signals only — not producing per-run CPU/mem/`num_instances.csv` in results; no cron/tmux process. Fix before Phase 7 if those charts are required. CSV rows also lack absolute timestamps (index≈seconds from collector start). |

---

## After this workplan is complete

Move to executing the real matrix: [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md) §2 (five scenarios) and §5 (usage), ≥3 repeats per scenario/condition (≥2 for Scenario 5 intervals), per [SCENARIOS-GUIDE.md](SCENARIOS-GUIDE.md). Update [AGENTS.md](../AGENTS.md) §4 as real runs complete.

**Smoke configs next run# (do not reuse smoke folders):**
- `scenario_1_baseline` → run3
- `scenario_1_retryguard` → run2
- `scenario_3_baseline` → run2
- `scenario_3_retryguard` → run2
- All other configs still at run1
