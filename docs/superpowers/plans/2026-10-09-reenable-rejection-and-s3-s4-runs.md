# Re-enable Threshold Sweep and S3/S4 Test Runs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run (A) a 12-hold sweep of RetryGuard's 0→1 re-enable rejection bar on locked S2, then (B) an 18-hold test set for S3, S4A and S4B at `reenable_rejection=0.15` under three controller arms.

**Architecture:** `REENABLE_REJECTION_THRESHOLD` is a module constant in `experiments/retryguard.py` (0.10). Make it a runtime param (`retryguard.reenable_rejection` in YAML, uploaded through `/tmp/retryguard_params.json`, default 0.10 so old configs are unchanged). A generator script writes one YAML per hold from a Paper-C1 template. A hold-driver procedure (cleanup, cool-off, run, pull, verify) is applied to every hold.

**Tech Stack:** Python 3 + PyYAML, `experiments/run_scenario.py`, `experiments/pull_results.py`, PowerShell + OpenSSH aliases (`topfull-master`, `topfull-worker-1`, `topfull-load`), pytest (`experiments/test_retryguard.py`).

## Global Constraints

- **Branch:** all work in this plan starts and stays on `study-reenable-rejection-s3-s4`, created from an updated `main` (Task 0). Do not commit on `main`. Do not push unless the user asks.
- SSH only via host aliases; user `idozacharia`; GCP project `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. Never start `networks-workshop` VMs.
- **S2 lock (Set A):** counts `getproduct/postcheckout/getcart/postcart/emptycart = 275 / 90 / 100 / 90 / 5`, `spawn_rate` 50, 600 s, Paper-C1, frontend pinned at 4, `retry_metric: edge_rpr`, `retries_threshold` 0.5, `rejection_threshold` 0.20, `interval_samples` 30.
- **S1 lock (Set B counts):** `175 / 30 / 70 / 90 / 5`, `spawn_rate` 50, Paper-C1 table. S3/S4 hold duration stays 600 s.
- **Set B constraints (absolute millicores, `method: cpu_limit`, container `server`):** S3 `checkoutservice` 300m; S4A `productcatalogservice` 300m; S4B `emailservice` 40m (S4B moves from `paymentservice` to `emailservice`). All other services at Paper-C1 limits.
- **Set B `reenable_rejection` = 0.15.**
- Cool-off: **360 s** before the first hold of a session and between every pair of holds (existing convention). VMs stay up during cool-off.
- Never reuse a `log_folder`; never overwrite existing results. New folders carry a `_rejre<val>_` or `_study2_` tag.
- Controller arms: TopFull on/off is `topfull_rl.enabled`; RetryGuard on/off is `retryguard.enabled`.
- Every hold must pass the gates in Task 5 or be rerun in a new slot.

## Hold Matrix

**Set A (12 holds, S2).** `rr` ∈ {0.10, 0.15, 0.20}; arms: `rgtf0` = RG on / TF off, `rgtf1` = RG on / TF on; 2 repeats each.

**Set B (18 holds).** Scenarios {S3, S4A, S4B} × arms {`tf1rg0` TF on RG off, `tf0rg1` TF off RG on, `tf1rg1` both on} × 2 repeats.

Run order is blocked, not clustered by arm, to spread drift: repeat 1 of every cell (shuffled with a fixed seed), then repeat 2 (new shuffle). Generator fixes seeds (A: 20261009, B: 20261010) and prints the order.

## File Structure

- Modify `experiments/retryguard.py`: read `reenable_rejection` from params (default constant).
- Modify `experiments/run_scenario.py` (~L725): forward `reenable_rejection` into params JSON; print it in the plan banner.
- Modify `experiments/test_retryguard.py`: test for param plumbing.
- Create `experiments/make_study_configs.py`: generator + run-order printer.
- Create `experiments/configs/study_2026_10_09/*.yaml` (generated, committed).
- Modify `experiments/configs/scenario_4b_{baseline,retryguard}.yaml` and docs for the S4B payment→email change.
- Create `Guides and Info/2026-10-09-reenable-rejection-and-s3-s4-readout.md` after runs.

---

### Task 0: Branch from updated main

**Files:** none. This task only moves git state.

- [ ] **Step 1: Fetch and update `main`**

```powershell
git fetch origin
git checkout main
git pull origin main
```

Expected: `main` is at the same commit as `origin/main`. If `git pull` reports local commits that are not on `origin/main`, stop and ask the user before branching.

- [ ] **Step 2: Create the branch**

```powershell
git checkout -b study-reenable-rejection-s3-s4
git status -sb
```

Expected: `## study-reenable-rejection-s3-s4`. The uncommitted plan file `docs/superpowers/plans/2026-10-09-reenable-rejection-and-s3-s4-runs.md` comes along with the working tree. Do not commit it on `main`.

- [ ] **Step 3: Commit the plan on the new branch**

```powershell
git add docs/superpowers/plans/2026-10-09-reenable-rejection-and-s3-s4-runs.md
git commit -m "docs: plan re-enable rejection sweep and S3/S4 test runs"
```

Every later task commits on this branch.

---

### Task 1: Make `reenable_rejection` a configurable parameter

**Files:**
- Modify: `experiments/retryguard.py` (~L678, L736, L951; `main` near L933–1050)
- Modify: `experiments/run_scenario.py` (~L725–L735, banner ~L1349)
- Test: `experiments/test_retryguard.py`

**Interfaces:**
- Produces: params key `reenable_rejection` (float, optional, default `REENABLE_REJECTION_THRESHOLD`); YAML key `retryguard.reenable_rejection`.

- [ ] **Step 1: Confirmed locations (no further reading needed)** — `EdgeController.__init__` (`retryguard.py` ~L736) takes `reenable_rejection_threshold=REENABLE_REJECTION_THRESHOLD`. It is built only in `run_edge_rpr` (~L942): `ctrl = EdgeController(CONTROLLED_EDGES, rpr_threshold, rejection_threshold, interval, attempts_on)`, with `params` in scope. The rejection-mode `run()` path does not use the bar, and all 11 RetryGuard YAMLs run `edge_rpr`.

- [ ] **Step 2: Write the failing test** (append to `experiments/test_retryguard.py`; adapt the helper name to the one that builds the controller from params — grep `def test_` for an existing pattern):

```python
def test_reenable_rejection_param_overrides_default():
    import retryguard as rg
    assert rg.reenable_threshold_from_params({}) == rg.REENABLE_REJECTION_THRESHOLD
    assert rg.reenable_threshold_from_params({"reenable_rejection": 0.15}) == 0.15
```

- [ ] **Step 3: Run it** — `python -m pytest experiments/test_retryguard.py -k reenable_rejection_param -v`. Expected: FAIL (`reenable_threshold_from_params` missing).

- [ ] **Step 4: Implement** in `retryguard.py`, next to the constant:

```python
def reenable_threshold_from_params(params: dict) -> float:
    return float(params.get("reenable_rejection", REENABLE_REJECTION_THRESHOLD))
```

and in `run_edge_rpr` change the construction to:

```python
    ctrl = EdgeController(
        CONTROLLED_EDGES, rpr_threshold, rejection_threshold, interval, attempts_on,
        reenable_rejection_threshold=reenable_threshold_from_params(params),
    )
``` The START log line (L951) already prints `reenable_rejection=%.2f`; it now reflects the param.

- [ ] **Step 5: Forward from the runner** — in `run_scenario.py` params dict add:

```python
        "reenable_rejection":      rg_cfg.get("reenable_rejection", 0.10),
```

and in the banner (~L1350) print `rg.get('reenable_rejection', 0.10)`.

- [ ] **Step 6: Run all tests** — `python -m pytest experiments -q`. Expected: all pass (previous count 58+ plus the new one).

- [ ] **Step 7: Commit** — `git add experiments/retryguard.py experiments/run_scenario.py experiments/test_retryguard.py && git commit -m "feat: make RetryGuard 0->1 re-enable rejection bar a YAML param"`

---

### Task 2: S4B switches from paymentservice to emailservice (docs + configs)

**Files:**
- Modify: `experiments/configs/scenario_4b_baseline.yaml`, `scenario_4b_retryguard.yaml`
- Modify: `AGENTS.md` (§5 table row 4A/4B + §4 mentions), `CONTEXT.md`, `Guides and Info/SCENARIOS-GUIDE.md`, `experiments/README.md`, `experiments/results/campaign_48/README.md`, `Guides and Info/PHASE5-EXPERIMENTS-GUIDE.md`, `Guides and Info/LOCUST-API-PATHS.md` (only where it names S4B)

- [ ] **Step 1: Find every S4B reference** — `rg -n "4B|4b|Checkout-mediated|paymentservice" AGENTS.md CONTEXT.md "Guides and Info" experiments/README.md experiments/results/campaign_48/README.md docs/adr`. List which lines refer to S4B's constrained service (not payment generally).

- [ ] **Step 2: Update the two S4B YAMLs** — header comments, `description`, `scale_constraints` deployment `emailservice`, `cpu_limit_millicores: 40`, path comment `Frontend → Checkout → Email`. Do not bump `run_number` here; the study configs are generated separately.

- [ ] **Step 3: Update docs** — replace S4B's constrained service with `emailservice` (40m) at each line found in Step 1; add one sentence: "Changed from paymentservice on 2026-10-09; `campaign_48/` S4B runs used paymentservice and are not comparable." Keep the Checkout-mediated framing (email is reached only via checkout).

- [ ] **Step 4: Verify** — `rg -n "4B.*payment|payment.*4B" AGENTS.md CONTEXT.md "Guides and Info" experiments/README.md` returns only the historical-note sentences.

- [ ] **Step 5: Commit** — `git commit -am "docs: S4B constrained service is emailservice (40m)"`

---

### Task 3: Study config generator

**Files:**
- Create: `experiments/make_study_configs.py`
- Create: `experiments/test_make_study_configs.py`
- Generated: `experiments/configs/study_2026_10_09/`

**Interfaces:**
- Produces: `build_configs() -> list[dict]` each with keys `path`, `set`, `order_index`, `cfg`; CLI `python experiments/make_study_configs.py --write` writes YAMLs and prints the order table.

Template: load `experiments/configs/scenario_2_retryguard_no_topfull.yaml` (Paper-C1 table, `restart_before_hold`, edge_rpr). Per hold, deep-copy and override:

| Field | Set A | Set B |
|---|---|---|
| `scenario_id/name` | 2 / sustained_overload | 3, 4 (topology_position_A / _B) / targeted_bottleneck |
| `locust.user_counts` | 275/90/100/90/5 | 175/30/70/90/5 |
| `scale_constraints` | template unchanged | replace the entry for the target service (checkout 300, productcatalog 300, email 40) |
| `topfull_rl.enabled` | per arm | per arm |
| `retryguard.enabled` | true | per arm |
| `retryguard.reenable_rejection` | 0.10/0.15/0.20 | 0.15 |
| `condition` | `retryguard` or `baseline` | same |
| `log_folder` | `study2_s2_rr{010,015,020}_{rgtf0,rgtf1}_rep{1,2}` | `study2_{s3,s4a,s4b}_{tf1rg0,tf0rg1,tf1rg1}_rep{1,2}` |

`restart_before_hold` stays (checkout + recommendations rolled, 60 s). For S3 (checkout constrained) the rolled checkout gets the new 300m limit from `scale_constraints` — confirm order in Task 5 gate.

- [ ] **Step 1: Write failing tests** (`test_make_study_configs.py`):

```python
import make_study_configs as m

def test_counts_and_sizes():
    cfgs = m.build_configs()
    assert sum(c["set"] == "A" for c in cfgs) == 12
    assert sum(c["set"] == "B" for c in cfgs) == 18

def test_set_b_constraints_and_threshold():
    by = {c["cfg"]["log_folder"]: c["cfg"] for c in m.build_configs()}
    def limit(cfg, dep):
        return next(x["cpu_limit_millicores"] for x in cfg["scale_constraints"] if x["deployment"] == dep)
    assert limit(by["study2_s3_tf1rg1_rep1"], "checkoutservice") == 300
    assert limit(by["study2_s4a_tf1rg1_rep1"], "productcatalogservice") == 300
    assert limit(by["study2_s4b_tf1rg1_rep1"], "emailservice") == 40
    assert by["study2_s4b_tf0rg1_rep2"]["retryguard"]["reenable_rejection"] == 0.15
    assert by["study2_s4b_tf0rg1_rep2"]["topfull_rl"]["enabled"] is False
    assert by["study2_s3_tf1rg0_rep1"]["retryguard"]["enabled"] is False

def test_set_a_values():
    by = {c["cfg"]["log_folder"]: c["cfg"] for c in m.build_configs()}
    c = by["study2_s2_rr015_rgtf1_rep2"]
    assert c["retryguard"]["reenable_rejection"] == 0.15
    assert c["topfull_rl"]["enabled"] is True
    assert c["locust"]["user_counts"]["getproduct"] == 275

def test_unique_log_folders_and_blocked_order():
    cfgs = m.build_configs()
    assert len({c["cfg"]["log_folder"] for c in cfgs}) == 30
    a = sorted((c for c in cfgs if c["set"] == "A"), key=lambda c: c["order_index"])
    assert all(c["cfg"]["log_folder"].endswith("rep1") for c in a[:6])
    assert all(c["cfg"]["log_folder"].endswith("rep2") for c in a[6:])
```

- [ ] **Step 2:** `python -m pytest experiments/test_make_study_configs.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement** `make_study_configs.py` per the table: `yaml.safe_load` the template, `copy.deepcopy`, apply overrides, `random.Random(seed).shuffle` the 6 (A) / 9 (B) cells per repeat block, assign `order_index`. For `topfull_rl.enabled: true` omit the key's `false` (set `True`). When `retryguard.enabled` is false keep the retryguard block (runner ignores it) but still set the other fields. Write files as `{order_index:02d}_{set}_{log_folder}.yaml` with `yaml.safe_dump(sort_keys=False)`; header comment names the plan file.

- [ ] **Step 4:** tests pass.

- [ ] **Step 5: Validate configs** — `run_scenario.py` has **no `--dry-run`**: its CLI takes only the config path and would start a real run. Validate offline instead. Add a test in `test_make_study_configs.py` that, for every generated config, asserts the keys `run_scenario.run()` reads exist (`scenario_id`, `condition`, `duration_seconds`, `locust.user_counts`, `locust.spawn_rate`, `locust.scripts`, `scale_constraints`, `retries.{attempts_on,attempts_off,per_try_timeout_ms}`, `retryguard.{rejection_threshold,sample_interval_seconds,interval_samples}`, `log_folder`, `infra.*`). The same test asserts each config's key set equals the template's key set (no stray or missing keys), and that `retryguard.reenable_threshold_from_params` returns the config's value. Expected: pass.

- [ ] **Step 6: Write and commit** — `python experiments/make_study_configs.py --write`, then `git add experiments/make_study_configs.py experiments/test_make_study_configs.py experiments/configs/study_2026_10_09 && git commit -m "feat: study configs for re-enable sweep and S3/S4 runs"`.

---

### Task 4: Preflight (once per session)

- [ ] **Step 1: Start VMs and refresh SSH** per [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md): `gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb`, update `HostName` in `~/.ssh/config`, then `ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"` (expect `idozacharia`).

- [ ] **Step 2: Cluster health** — `ssh topfull-master "kubectl get nodes; kubectl get pods -n default"`; all nodes Ready, Boutique pods 2/2.

- [ ] **Step 3: Apply the Paper-C1 pin** (frontend 4 replicas: HPA min=max=4, sidecar `proxyCPU=90m`, `proxyCPULimit` unset, catalog HPA max 1) using the same helper as the latch series (`experiments/latch_hold_pre.ps1`; read it first and use it unchanged). Verify: `kubectl get hpa; kubectl get deploy frontend -o jsonpath='{.spec.template.metadata.annotations}'`.

- [ ] **Step 4: Confirm deployed retryguard** — runner copies `retryguard.py` at each start, so only verify the local file has Task 1 (`rg experiments/retryguard.py -n reenable_threshold_from_params`).

- [ ] **Step 5: Initial 360 s cool-off** before hold 1 (Locust fully stopped, pods settled). Use `AwaitShell`/a timed wait, not `sleep` in the shell.

---

### Task 5: Per-hold procedure (repeat for every hold in order)

Applies to all 30 holds; one hold at a time, strictly sequential. `CFG` = the generated YAML path.

- [ ] **Step 1: Clear stale remote scripts**
`ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json"`

- [ ] **Step 2: Stop leftover writers** (AGENTS.md §6 steps 1–2)
`ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"`
`ssh topfull-master "pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"`

- [ ] **Step 3: Confirm clear** — expect exactly `locust-clear` and `master-clear`:
`ssh topfull-load "pgrep -af '[l]ocust' || echo locust-clear"`
`ssh topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"`
Anything else: stop, do not run.

- [ ] **Step 4: Clear live logs, then verify empty**
`ssh topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log"`
`ssh topfull-master "sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"` → must print nothing.

- [ ] **Step 5: Pin check** — frontend `readyReplicas` 4, catalog 1, no Pending pods: `ssh topfull-master "kubectl get deploy; kubectl get pods | grep -v Running"`. Also confirm no leftover non-Paper-C1 constraint from the previous hold (the runner reconciles/restores constraints at the end of each run; with `paper_cpu_reconcile: false` verify `checkoutservice`, `productcatalogservice`, `emailservice` limits equal Paper-C1 values: 800 / 800 / 120, via `kubectl get deploy <name> -o jsonpath='{.spec.template.spec.containers[?(@.name=="server")].resources.limits.cpu}'`). If a leftover is found, restore it and add 60 s settle.

- [ ] **Step 6: Run the hold**
`python experiments/run_scenario.py <CFG>` (long-running: launch in the background and poll with `AwaitShell`; do not run two `run_scenario.py` at once).

- [ ] **Step 7: Pull and report** — `python experiments/pull_results.py <CFG>`. Folder lands in the scenario subfolder under `experiments/results/campaign_48/`.

- [ ] **Step 8: Gates** (any failure → mark hold invalid, keep folder, rerun as new `_repN` slot via generator `--extra`; do not overwrite):
  - Locust `total.csv` rows ≈ 540–575 (1043+ or <500 = fail).
  - Mesh span (first→last row of `service_inbound.csv`) 600–760 s, no >10% 2 s-gap on the controlled service's inbound series.
  - `resource_usage.csv`: frontend `replica_count` 4 on every sample; no 0-replica samples on the constrained service.
  - Constrained service limit recorded in `service_capacity.json` equals the plan value (S3 checkout 300, S4A catalog 300, S4B email 40; S2 Paper-C1).
  - TopFull arm: `topfull_throttle.csv` has live caps below 10000 at some point if TF on; all samples stay 10000 if TF off.
  - RG arm: `retryguard.log` first line contains `reenable_rejection=<expected>` and `metric=edge_rpr`; no `PATCH_FAIL` or traceback. RG-off arm: no `retryguard.log` entries.
  - Stray `mesh/Locust` collectors ended with the run (Step 3 will confirm at the next hold).

- [ ] **Step 9: Restore** — confirm the runner restored the constraint and VirtualServices (`kubectl get vs -o yaml | rg -n "attempts|timeout"` shows attempts 3, no route `timeout`); restore the pin if Task 4's helper requires it between holds.

- [ ] **Step 10: Cool-off 360 s** before the next hold (and run Step 2–3 cleanup right after it, since Steps 1–5 are per-hold). Skip the cool-off only after the final hold.

- [ ] **Step 11: Log** — append `hold N | folder | gate result | note` to `docs/superpowers/plans/2026-10-09-run-log.md` (create on first hold). Commit results every 6 holds: `git add experiments/results docs/superpowers/plans/2026-10-09-run-log.md && git commit -m "data: study2 holds N-M"`.

---

### Task 6: Execute Set A (12 holds)

- [ ] Run `python experiments/make_study_configs.py --write` prints the Set A order; follow Task 5 per hold in that order, using `study_2026_10_09/` files `*_A_*`.
- [ ] After hold 6 (end of repeat block 1), pause: check that START log lines show all three `reenable_rejection` values were exercised at least once; if not, stop and debug plumbing before continuing.
- [ ] After hold 12, run `python experiments/rho_estimate_report.py` is **not** needed; instead build the Set A table below.

Set A readout (per `rr` × arm × repeat): checkout/recommendations `ON→OFF` count, `OFF→ON` count, attempts reached after re-enable (1/2/3), time OFF, OFF-window rejection min/median, frontend→{checkout,recommendations} retry Δ, total goodput, failure fraction, P95. Source: `retryguard.log`, `service_edges.csv`, `service_inbound.csv`, Locust `total.csv`.

---

### Task 7: Between-set transition

- [ ] **Step 1:** Restore Paper-C1 state and confirm limits equal Paper-C1 (Task 5 Step 5 commands).
- [ ] **Step 2:** 360 s cool-off, then Task 5 Steps 1–5 again.
- [ ] **Step 3:** Check S3/S4 first-hold constraint takes effect: dry-read of the first Set B config's `scale_constraints`, and after the runner applies it confirm `service_capacity.json` shows the 300/300/40 value.

---

### Task 8: Execute Set B (18 holds)

- [ ] Follow Task 5 per hold in the printed Set B order (`*_B_*` files). Note S3/S4 TF-on arms use the Paper-C1 TopFull quota map reconciled by the runner; do not edit `topfull_cpu_quotas.py`.
- [ ] After hold 9 (end of repeat block 1) pause: confirm each of the 9 cells has one valid hold; rerun invalid ones in a new slot before starting block 2.
- [ ] If a hold shows no signal at the constrained service (detector overloaded ticks 0 and rejection never >0.05 on any arm), do not change the config mid-set; finish the set and flag in the readout.

Set B readout per scenario × arm: constrained service detector-overloaded share, longest rejection streak, RG toggles (`ON→OFF`/`OFF→ON`, attempts after re-enable), retry Δ into the constrained service, entry-API goodput/P95/fail for `postcheckout` and `getproduct`.

---

### Task 9: Teardown, docs, and handoff

- [ ] **Step 1:** Final Task 5 Steps 1–3 cleanup; restore Paper-C1 limits, HPAs (frontend 1–4, catalog max 2), sidecar `proxyCPU` 100m with `proxyCPULimit` unset; confirm VirtualServices at attempts 3.
- [ ] **Step 2:** Write `Guides and Info/2026-10-09-reenable-rejection-and-s3-s4-readout.md` with the Set A and Set B tables, gate failures and reruns, and any anomalies.
- [ ] **Step 3:** Update `AGENTS.md` §4 with a dated bullet (what ran, folders `study2_*`, `reenable_rejection` now a YAML param default 0.10, S4B = emailservice 40m), and note next-free slots unchanged for the original YAMLs.
- [ ] **Step 4:** Commit; then stop VMs only if the user asks: `gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb`.

---

## Time Estimate

Per hold ≈ 10 min run + ~3 min setup/pull + 6 min cool-off ≈ 19 min. Set A ≈ 3.8 h; Set B ≈ 5.7 h. Plan them as two separate sessions, with Task 7 as the session boundary (VMs may stop between sessions; if so redo Task 4).

## Self-Review

- Spec coverage: Set A (3 values × 2 arms × 2 runs = 12) ✔; Set B (3 scenarios × 3 arms × 2 = 18, 0.15, S1 counts, 300/300/40) ✔; S4B doc update ✔ (Task 2); cool-offs and cleanups ✔ (Task 5/7/9); branch from updated `main` ✔ (Task 0).
- Resolved: `run_scenario.py` has no `--dry-run` (Task 3 Step 5 uses an offline test), and the controller is built only in `run_edge_rpr` (Task 1).
