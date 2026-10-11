# S2 re-enable 0.25 and tighter climb bars

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run six locked-S2 holds that try `reenable_rejection` 0.25 (default climb, then a tighter climb) and `reenable_rejection` 0.20 with that same tighter climb, once with RetryGuard only and once with both controllers on.

**Architecture:** No controller changes. Copy one existing study YAML six times and override `reenable_rejection`, the two climb bars, `topfull_rl.enabled`, and `log_folder`. Run the six holds in order with the usual cleanup and a 360 s cool-off between them. Commit the configs and the pulled results, then push the current branch.

**Tech Stack:** Existing `experiments/run_scenario.py` and `experiments/pull_results.py`. YAML keys `retryguard.reenable_rejection`, `climb_rpr_1_to_2`, and `climb_rpr_2_to_3` are already forwarded into RetryGuard.

## Global Constraints

- Stay on branch `study-reenable-rejection-s3-s4`. Do not branch from `main`: the climb-bar YAML keys are only on this branch.
- Do not edit `experiments/retryguard.py`, `experiments/run_scenario.py`, or the locked `scenario_2_*.yaml` files. Their next-free slots stay RetryGuard-only **run22** and both-on **run30**.
- SSH only via host aliases; user `idozacharia`; project `project-76deda76-55f1-42d2-abb`; zone `us-central1-a`. Do not start `networks-workshop`.
- Locked S2 mix: `275 / 90 / 100 / 90 / 5`, `spawn_rate` 50, 600 s, Paper-C1, `retry_metric: edge_rpr`, `retries_threshold` 0.5, `rejection_threshold` 0.20, `interval_samples` 30.
- Default climb (holds 1–2) is `climb_rpr_1_to_2: 0.17` and `climb_rpr_2_to_3: 0.33`. Tighter climb (holds 3–6) is `0.10` and `0.25`.
- Cool-off is **360 s** before hold 1 and between every pair. VMs stay up. Do not stop the VMs at the end.
- One hold at a time. Never reuse a `log_folder`. A failed gate keeps its folder and is replayed once as `_r2`.

## Hold order

| # | File | `reenable_rejection` | climb 1→2 / 2→3 | Arm | `log_folder` |
| --- | --- | --- | --- | --- | --- |
| 1 | `01_rr025_rgtf0.yaml` | 0.25 | 0.17 / 0.33 | RG on, TF off | `study3_s2_rr025_rgtf0` |
| 2 | `02_rr025_rgtf1.yaml` | 0.25 | 0.17 / 0.33 | both on | `study3_s2_rr025_rgtf1` |
| 3 | `03_rr025_c1025_rgtf0.yaml` | 0.25 | 0.10 / 0.25 | RG on, TF off | `study3_s2_rr025_c1025_rgtf0` |
| 4 | `04_rr025_c1025_rgtf1.yaml` | 0.25 | 0.10 / 0.25 | both on | `study3_s2_rr025_c1025_rgtf1` |
| 5 | `05_rr020_c1025_rgtf0.yaml` | 0.20 | 0.10 / 0.25 | RG on, TF off | `study3_s2_rr020_c1025_rgtf0` |
| 6 | `06_rr020_c1025_rgtf1.yaml` | 0.20 | 0.10 / 0.25 | both on | `study3_s2_rr020_c1025_rgtf1` |

Results land in `experiments/results/campaign_48/S2_sustained_overload/<log_folder>/`.

---

### Task 1: Write the six configs

**Files:**
- Create: `experiments/configs/study_2026_10_10/01_rr025_rgtf0.yaml` through `06_rr020_c1025_rgtf1.yaml`
- Template: `experiments/configs/study_2026_10_09/01_A_study2_s2_rr015_rgtf0_rep1.yaml`

**Interfaces:**
- Consumes: the study2 YAML shape (`paper_cpu_reconcile: false`, Paper-C1 `scale_constraints`, `restart_before_hold` on checkout and recommendations).
- Produces: six configs whose `log_folder` values are the table above.

- [ ] **Step 1: Generate the files**

From the repo root, run this once. It copies the template and applies only the six overrides.

```python
from copy import deepcopy
from pathlib import Path
import yaml

src = Path("experiments/configs/study_2026_10_09/01_A_study2_s2_rr015_rgtf0_rep1.yaml")
out = Path("experiments/configs/study_2026_10_10")
out.mkdir(parents=True, exist_ok=True)
base = yaml.safe_load(src.read_text(encoding="utf-8"))

holds = [
    ("01_rr025_rgtf0.yaml", 0.25, 0.17, 0.33, False, "study3_s2_rr025_rgtf0"),
    ("02_rr025_rgtf1.yaml", 0.25, 0.17, 0.33, True, "study3_s2_rr025_rgtf1"),
    ("03_rr025_c1025_rgtf0.yaml", 0.25, 0.10, 0.25, False, "study3_s2_rr025_c1025_rgtf0"),
    ("04_rr025_c1025_rgtf1.yaml", 0.25, 0.10, 0.25, True, "study3_s2_rr025_c1025_rgtf1"),
    ("05_rr020_c1025_rgtf0.yaml", 0.20, 0.10, 0.25, False, "study3_s2_rr020_c1025_rgtf0"),
    ("06_rr020_c1025_rgtf1.yaml", 0.20, 0.10, 0.25, True, "study3_s2_rr020_c1025_rgtf1"),
]
plan = "docs/superpowers/plans/2026-10-10-s2-rr025-climb-holds.md"
for name, rr, c12, c23, tf, folder in holds:
    cfg = deepcopy(base)
    cfg["run_number"] = 1
    cfg["description"] = (
        f"Study 2026-10-10 {folder}: S2 275/90/100/90/5, "
        f"reenable_rejection={rr}, climb {c12}/{c23}, topfull_rl={tf}."
    )
    cfg["topfull_rl"]["enabled"] = tf
    cfg["retryguard"]["reenable_rejection"] = rr
    cfg["retryguard"]["climb_rpr_1_to_2"] = c12
    cfg["retryguard"]["climb_rpr_2_to_3"] = c23
    cfg["log_folder"] = folder
    text = yaml.safe_dump(cfg, sort_keys=False)
    (out / name).write_text(f"# Plan: {plan}\n" + text, encoding="utf-8")
print("wrote", len(holds))
```

- [ ] **Step 2: Check the six files**

```powershell
python -c "import yaml, pathlib; p=pathlib.Path('experiments/configs/study_2026_10_10');
[print(f.name, yaml.safe_load(f.read_text())['retryguard']['reenable_rejection'], yaml.safe_load(f.read_text())['retryguard']['climb_rpr_1_to_2'], yaml.safe_load(f.read_text())['retryguard']['climb_rpr_2_to_3'], yaml.safe_load(f.read_text())['topfull_rl']['enabled'], yaml.safe_load(f.read_text())['log_folder'], yaml.safe_load(f.read_text())['locust']['user_counts']) for f in sorted(p.glob('*.yaml'))]"
```

Expected: six lines matching the table. Every file still has `getproduct: 275`, `retry_metric: edge_rpr`, `paper_cpu_reconcile: false`, and checkout/recommendations in `restart_before_hold`. User counts and Paper-C1 millicores are unchanged from the template.

- [ ] **Step 3: Commit the configs**

```powershell
git add experiments/configs/study_2026_10_10 docs/superpowers/plans/2026-10-10-s2-rr025-climb-holds.md
git commit -m "feat: six S2 holds for reenable 0.25 and tighter climb bars"
```

---

### Task 2: Preflight, once

- [ ] **Step 1: Start the three VMs if they are stopped, then refresh SSH**

Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md).

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Update `HostName` in `~/.ssh/config` from that table, then:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
```

Expected user: `idozacharia`.

- [ ] **Step 2: Cluster health**

```powershell
ssh topfull-master "kubectl get nodes; kubectl get pods -n default"
```

All nodes Ready. Boutique pods `2/2`.

- [ ] **Step 3: Paper-C1 pin**

Frontend HPA 4/4, catalog HPA 1/1, sidecar request 90m, no sidecar CPU limit. Patch the Deployment template, not a Deployment-object annotate.

```powershell
ssh topfull-master "kubectl patch hpa frontend-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":4,\"maxReplicas\":4}}'; kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":1,\"maxReplicas\":1}}'; kubectl patch deployment frontend -n default --type merge -p '{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"90m\"}}}}}'; kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit- ; kubectl rollout status deployment/frontend -n default --timeout=180s"
```

Confirm: `kubectl get hpa frontend-hpa productcatalogservice-hpa` shows 4/4 and 1/1, and frontend's annotation is `proxyCPU=90m` with `proxyCPULimit` absent. Wait until frontend is 4 ready pods.

- [ ] **Step 4: Cool-off 360 s** before hold 1. Locust is already stopped (Task 3 Step 1, run it once now). Use a timed wait, not an unbounded shell sleep as the only check.

---

### Task 3: Run the six holds

Repeat Steps 1–8 for holds 1 through 6, in table order. `CFG` is `experiments/configs/study_2026_10_10/<file>`.

- [ ] **Step 1: Stop leftover writers**

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear.** Anything other than the two `-clear` lines means stop.

```powershell
ssh topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

- [ ] **Step 3: Clear live logs and confirm they stay empty**

```powershell
ssh topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

The `ls` must print nothing. If a file reappears, a writer is still alive.

- [ ] **Step 4: Run**

```powershell
python experiments/run_scenario.py experiments/configs/study_2026_10_10/<file>
```

One process only. A 600 s hold plus setup is about 15 minutes. Do not start the next hold until this process exits.

- [ ] **Step 5: Pull**

```powershell
python experiments/pull_results.py experiments/configs/study_2026_10_10/<file>
```

- [ ] **Step 6: Gates.** Keep the folder either way.

Pass when all of these are true:

- `total.csv` has about 540–580 data rows.
- `retryguard.log` START line contains `metric=edge_rpr`, `reenable_rejection=` equal to this hold's bar (`0.25` or `0.20`), and `climb_rpr_1_to_2` / `climb_rpr_2_to_3` equal to this hold's climb (`0.17`/`0.33` or `0.10`/`0.25`). No `PATCH_FAIL` and no traceback.
- `resource_usage.csv`: frontend `replica_count` is 4 on every sample.
- TF off: live `topfull_throttle.csv` thresholds stay at the 10000 passthrough. TF on: some live cap is below 10000.
- VirtualServices are back to `attempts: 3` with no route `timeout`.

A failure is logged, the folder is kept, and the hold is replayed **once** by copying the YAML to a sibling `*_r2.yaml` with `log_folder` suffixed `_r2`. Do not overwrite the failed folder. Do not replay a second time.

- [ ] **Step 7: Cool-off 360 s**, then Steps 1–3 again, before the next hold. Skip the cool-off after hold 6.

- [ ] **Step 8: Append one line** to `docs/superpowers/plans/2026-10-10-s2-rr025-climb-run-log.md`:

`hold N | log_folder | PASS or INVALID | locust rows | START reenable and climb values | note`

---

### Task 4: Restore, commit, push

- [ ] **Step 1: Final cleanup** — Task 3 Steps 1–2, so Locust and the master writers are stopped.

- [ ] **Step 2: Restore the unpinned pair**

Frontend HPA min 1 / max 4, catalog HPA max 2, sidecar request 100m, `proxyCPULimit` unset.

```powershell
ssh topfull-master "kubectl patch hpa frontend-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":1,\"maxReplicas\":4}}'; kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":1,\"maxReplicas\":2}}'; kubectl patch deployment frontend -n default --type merge -p '{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"100m\"}}}}}'; kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit-"
```

Confirm with `kubectl get hpa frontend-hpa productcatalogservice-hpa` and the frontend annotation. Leave the VMs running.

- [ ] **Step 3: One status bullet in `AGENTS.md` §4**

Date 2026-10-10. Name the six `study3_s2_*` folders, the three settings (0.25 at 0.17/0.33, 0.25 at 0.10/0.25, 0.20 at 0.10/0.25), one RG-only and one both-on each, and that locked YAML slots were not bumped. Point at the run log.

- [ ] **Step 4: Commit everything left**

```powershell
git status -sb
git add experiments/results/campaign_48/S2_sustained_overload/study3_s2_rr025_rgtf0 experiments/results/campaign_48/S2_sustained_overload/study3_s2_rr025_rgtf1 experiments/results/campaign_48/S2_sustained_overload/study3_s2_rr025_c1025_rgtf0 experiments/results/campaign_48/S2_sustained_overload/study3_s2_rr025_c1025_rgtf1 experiments/results/campaign_48/S2_sustained_overload/study3_s2_rr020_c1025_rgtf0 experiments/results/campaign_48/S2_sustained_overload/study3_s2_rr020_c1025_rgtf1 docs/superpowers/plans/2026-10-10-s2-rr025-climb-run-log.md AGENTS.md
```

If a replay folder `study3_s2_*_r2` exists, add that folder too. If `git status` shows a secret (`.env`, a key, `credentials.json`), unstage it and stop.

```powershell
git commit -m "data: six S2 holds for reenable 0.25 and tighter climb bars"
git status -sb
```

Skip the commit if the tree is already clean.

- [ ] **Step 5: Push**

```powershell
git push -u origin study-reenable-rejection-s3-s4
git status -sb
```

Expected: the branch matches `origin/study-reenable-rejection-s3-s4` and the working tree is clean.

## Time

About 15 minutes of run and pull plus 6 minutes of cool-off per hold. Six holds are about 2 hours.

## Self-review

- Six holds, in the requested order: 0.25 default climb, 0.25 with climb 0.10/0.25, 0.20 with climb 0.10/0.25; each once RG-only and once both-on.
- Cool-off 360 s and the writer/log cleanup sit before every hold.
- Locked scenario YAML slots are not bumped.
- Final step commits and pushes. VMs stay up because this request did not ask to stop them.
