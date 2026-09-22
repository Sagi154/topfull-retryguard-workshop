# Frontend / productcatalog v2 refreeze re-runs

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **This is an experiment-ops plan, not a code feature.** Do not invent extra runs, do not start Task 9, and do not skip the final VM stop.

**Goal:** Re-run two constrained-CPU calibration holds (frontend 50m at 3× Task-8b-run4 mix, then productcatalog 50m with frontend pinned at 4 replicas) under the 8888+ v2 stats-port fix, and freeze `mu_per_millicore` only for a service whose new folder has `n_sat_ticks >= 10` and is not `low_confidence`.

**Architecture:** No new collectors or controller changes. Edit only `locust.user_counts` (and `run_number`/`log_folder` if a slot is occupied or if the optional frontend 5× retry is needed). `run_scenario.py` deploys `experiments/loadgen/online_boutique_create_v2.sh` onto `topfull-load`, starts the usual collector stack, and heals paper CPU after each run. After pull, `capacity_frozen.py freeze --force` is allowed only when the gate passes; otherwise leave the 2026-09-21-v2 freeze in place. Then restore both HPAs and stop all three VMs.

**Tech Stack:** Existing `run_scenario.py` / `pull_results.py` / `capacity_frozen.py` / `estimate_service_mu.py` over SSH; PowerShell on this Windows workstation; `kubectl` via `ssh topfull-master`.

## Global Constraints

- Do **not** start Task 9 (S1/S2/S6 system-load calibration). This plan is only the two (optionally three) calibration holds.
- Do **not** re-freeze frontend `0.79` from `calibration_frontend_constrained_50m_run4` (`n_sat_ticks=2`). Do **not** treat a new `n_sat_ticks < 10` run as a winner.
- `SAT_5XX_FRACTION` stays `0.05`. `SAT_TAIL_TRIM_TICKS` stays `5`. `LOW_CONFIDENCE_SAT_TICKS` stays `10`. Do not loosen any of them.
- v2 `HOST` must stay the script default `http://10.128.0.3:30440`. Do not export `HOST`. Do not revert to `10.8.0.4`.
- v2 Locust stats stdin ports must stay in `8888–8930` (`ports_v2/` files only). Do not launch legacy `online_boutique_create.sh` / `create2.sh` in the same session.
- YAML edits: `user_counts` only, plus `run_number`/`log_folder` when bumping a slot. Do not change `duration_seconds`, `spawn_rate`, `scripts`, collector blocks, or `topfull_rl` / `retryguard` (`enabled: false` both).
- Never overwrite an existing results folder on master. Re-check the slot immediately before the run.
- `cluster_shape` must stay `topfull-worker-1=e2-standard-16`. Stop the battery (restore HPAs, stop VMs) if the worker is a different SKU.
- SSH aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`). Connect as `idozacharia`. Never hardcode public IPs.
- If VMs are `TERMINATED`, start them and refresh `HostName` using CONNECT-VMS **Steps 3 and 5 only** — not key install (Step 4).
- Cool-off is **300 seconds** before the first hold if anything was recently run (or if you are unsure), and **300 seconds between every hold**. Clock starts when `run_scenario.py` exits. `pull_results.py` may run during the wait.
- Locust CSV header-only on the first hold is a **hard STOP** of this battery: restore HPAs, stop VMs, do not freeze, do not start the catalog hold.
- If catalog still does not reject, **stop and report**. Do not raise `getproduct` in a loop.
- After the last run (success or fail): restore both HPAs from `experiments/manifests/`, then **stop all three VMs**. The stop is mandatory.
- Do not commit result folders. A later docs/freeze commit is allowed only after a successful freeze; do not commit during this planning file's creation.

## File map

| File | Role |
|---|---|
| `experiments/configs/scenario_calibration_frontend_constrained_50m.yaml` | Run A (and optional 5×). Task 8b left it at `run_number: 5` / `log_folder: calibration_frontend_constrained_50m_run5`. |
| `experiments/configs/scenario_calibration_productcatalog_constrained.yaml` | Run B. Task 8b left it at `run_number: 4` / `log_folder: calibration_productcatalog_constrained_run4`. |
| `experiments/loadgen/online_boutique_create_v2.sh` | Already on 8888+ (`46dcdb8`). Do not edit unless a new port bug appears. |
| `experiments/manifests/frontend-hpa.yaml` | Restore `frontend-hpa` (`maxReplicas: 4`) at the end. |
| `experiments/manifests/productcatalogservice-hpa.yaml` | Restore `productcatalogservice-hpa` (`maxReplicas: 2`) at the end. |
| `experiments/capacity/capacity_frozen.json` | Written only by `capacity_frozen.py freeze --force` when the gate passes. |
| `experiments/capacity/README.md` | Update only for services actually re-frozen. |
| `AGENTS.md` §4 / `docs/superpowers/specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md` | Note the new slots and freeze outcome. Do not start Task 9. |

Results land under `experiments/results/campaign_48/` (calibration `scenario_id` 42/43 → `scenario_dir_name()` returns `""`).

## Port audit already done (2026-09-22) — do not re-litigate

Commit `46dcdb8` moved v2 Locust stats stdin into `8888–8898` at default worker counts. Checked every process `run_scenario.py` starts. **No collision. No v2 code change in this planning session.**

| Process | Host | Port | Collides with load `8888–8898`? |
|---|---|---|---|
| Locust `metric_collector.py` | scrapes from **master** → `global_config.json` `locust_url` `http://10.128.0.2` (load VPC IP) | `8888 + range(locust_port)` = **8888–8930** (`locust_port=43`) | **Intended.** This is why v2 moved here. |
| `envoy_retry_collector.py` | master → Boutique **pod IPs** | **15020** `/stats/prometheus` | No. Different host. |
| `resource_usage_collector.py` | master → kube-apiserver proxy | kubelet **10250** `stats/summary` on each node; `/proc/stat` on master for `__master_node__` | No. |
| `topfull_throttle_collector.py` Layer A | master | goproxy **8090** `/stats` + `/thresholds` (`proxy_url` `http://10.128.0.3:8090`) | No. Master, not load. |
| `topfull_throttle_collector.py` Layer B | master → cAdvisor pod IPs | **8080** `/api/v2.0/summary/...` | No. |
| `retryguard.py` | master | **does not bind a port** (`--params` JSON; reads `service_inbound.csv`; patches VirtualServices) | No. Off for these YAMLs anyway. |
| TopFull proxy | master | **8090** | No. |
| TopFull RL / Ray (`deploy_rl.py`) | master | Ray/GCS on master (not started: `topfull_rl.enabled: false`) | No. |
| Istio / Boutique frontend | master NodePort | **80:30440** (`kubectl get svc frontend`) | No. This is Locust `--host`, not a stats port. |
| Locust RPC | **load** | `--master-bind-port=9001` (postcheckout) and **9002** (getproduct) | No. v2 does **not** bind RPC onto 8888. |
| Locust stats HTTP | **load** | stdin `HTTPServer(('0.0.0.0', port))` — v2 **8888–8898** | The scrape target. |
| legacy `ports/` | **load** files only | 8885–89xx filenames | v2 writes **`ports_v2/` only**. Confirmed in the script (`mkdir -p ports_v2`, `< ports_v2/$port`). Live leftover `ports_v2/91xx` files from Task 8b are unused after the next deploy. |
| `DRY_PORTS=1` | — | prints the map and `exit 0` **before** `mkdir` / `tmux` / locust | Correct. Do not "fix" it. |

**Worker vs master stats (no double-count):** `locust_online_boutique.py` on `topfull-load` keeps `mapStats` process-local and increments it only from `@events.request` in that process. Locust `--master` does not run users, so master ports (8888, 8891) report zeros. `metric_collector.py` sums RPS/fail by API name across every port that answers. `0 + worker = worker`. Legacy create.sh parked masters at 8885–8887 (outside the scrape) for slot hygiene, not because summing zeros would double-count.

---

### Task 0: Preflight VMs, cluster, slots, v2 ports

**Files:**
- Read-only: `Guides and Info/CONNECT-VMS.md` Steps 3 and 5
- Read-only: both calibration YAMLs
- Do not edit SSH config unless a VM was `TERMINATED` and IPs changed

**Interfaces:**
- Consumes: current `gcloud` status
- Produces: three aliases working as `idozacharia`; worker is `e2-standard-16`; confirmed free slots; v2 `DRY_PORTS=1` map is 8888–8898 and does not launch locust

- [x] **Step 1: List VM status and machine types**

```powershell
gcloud compute instances list --project=networks-workshop --format="table(name,status,machineType,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: all three `topfull-*` rows. Worker must be `e2-standard-16`. Master and load are `e2-standard-8`. If the worker is not `e2-standard-16`, **stop this plan** (do not run, do not freeze).

Planning-session snapshot (2026-09-22): all three were `RUNNING`, worker `e2-standard-16`. **Re-check. Do not trust this snapshot.**

- [x] **Step 2: Start + refresh HostName only if TERMINATED**

If every VM is `RUNNING`, skip start. If any is `TERMINATED` or has an empty NAT IP:

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=networks-workshop

gcloud compute instances list --project=networks-workshop --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Then update **only** the three `Host topfull-*` `HostName` lines in `$env:USERPROFILE\.ssh\config` (CONNECT-VMS Step 5). `User` stays `idozacharia`. Do **not** run key install (Step 4).

- [x] **Step 3: Verify SSH and cluster**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "hostname; whoami"

ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get hpa -n default; kubectl get svc frontend -n default"
```

Expected: `whoami` is `idozacharia` on all three. Both nodes `Ready`. Boutique pods Running. `frontend` Service is `80:30440/TCP`. HPAs `frontend-hpa` (max 4) and `productcatalogservice-hpa` (max 2) exist before we delete them.

If `kubectl` says `connection to localhost:8080 refused` for this SSH user, it is the missing-kubeconfig case (AGENTS.md §7), not an invitation to rebuild the cluster. Fix kubeconfig, then re-check. Do not start runs until `kubectl get nodes` works.

- [x] **Step 4: Confirm slots are still free**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ls -d /home/idozacharia/experiments/results/calibration_frontend_constrained_50m_run5 /home/idozacharia/experiments/results/calibration_productcatalog_constrained_run4 2>&1"

Test-Path experiments\results\campaign_48\calibration_frontend_constrained_50m_run5
Test-Path experiments\results\campaign_48\calibration_productcatalog_constrained_run4
```

Expected: remote `ls` reports "No such file" for both, local `Test-Path` is `False`. Planning-session snapshot: both were free.

If `run5` already exists, bump the frontend YAML to the next free integer (`run6`, `calibration_frontend_constrained_50m_run6`, …) before Task 1. If `run4` already exists, bump the catalog YAML the same way. Do not overwrite.

- [x] **Step 5: Confirm v2 HOST default and DRY_PORTS (no locust)**

From the repo root, after any HostName refresh:

```powershell
scp experiments/loadgen/online_boutique_create_v2.sh topfull-load:/home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create_v2.sh

ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "grep -n 'HOST=' /home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create_v2.sh | head -5; echo '--- DRY_PORTS ---'; cd /home/idozacharia/TopFull/TopFull_loadgen && DRY_PORTS=1 bash online_boutique_create_v2.sh; echo EXIT:$?; echo '--- leftover locust ---'; pgrep -af locust || echo 'no locust'; echo '--- ports/ vs ports_v2/ ---'; ls ports | head -5; ls ports_v2 | head -20"
```

Expected stdout includes:

```
HOST="${HOST:-http://10.128.0.3:30440}"
v2 stats ports (metric_collector scrape 8888-8930):
  postcheckout master 8888 workers 8889,8890
  getproduct   master 8891 workers 8892,8893,8894,8895
  getcart 8896  postcart 8897  emptycart 8898
EXIT:0
no locust
```

`ports/` still lists the legacy 8885+ filenames (untouched). `DRY_PORTS=1` must not have created a tmux session or a locust process. If it launched locust, **stop** and fix `online_boutique_create_v2.sh` only (the `if [[ "${DRY_PORTS:-}" == "1" ]]; then exit 0; fi` block must stay **before** `mkdir` / `tmux`).

- [x] **Step 6: Clear stale /tmp runner scripts on master**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
```

---

### Task 1: Write Run A / Run B YAML user_counts

**Files:**
- Modify: `experiments/configs/scenario_calibration_frontend_constrained_50m.yaml` (user_counts only if `run5` is free)
- Modify: `experiments/configs/scenario_calibration_productcatalog_constrained.yaml` (user_counts only if `run4` is free)

**Interfaces:**
- Consumes: free slot names from Task 0
- Produces: Run A mix `30/15/30/15/60` at `spawn_rate: 50`, duration still `600`; Run B mix `400/10/10/10/10` at `spawn_rate: 50`, duration still `900`

Do **not** bump `run_number`/`log_folder` here unless Task 0 found the slot occupied.

- [x] **Step 1: Edit the frontend YAML `locust.user_counts` block**

Replace only this block in `experiments/configs/scenario_calibration_frontend_constrained_50m.yaml`. Leave `run_number: 5`, `log_folder: calibration_frontend_constrained_50m_run5`, `duration_seconds: 600`, `spawn_rate: 50`, `scripts: [online_boutique_create_v2.sh]`.

```yaml
  user_counts:
    getproduct:   30
    postcheckout: 15
    getcart:      30
    postcart:     15
    emptycart:    60
```

Also update the header comment so it no longer says the Ron-config ~3× of `10/5/10/5/20` is what this file will launch. One sentence is enough: `run5` is the 3× storefront mix (`30/15/30/15/60`) after the 8888 port fix.

- [x] **Step 2: Edit the catalog YAML `locust.user_counts` block**

Replace only this block in `experiments/configs/scenario_calibration_productcatalog_constrained.yaml`. Leave `run_number: 4`, `log_folder: calibration_productcatalog_constrained_run4`, `duration_seconds: 900`, `spawn_rate: 50`.

```yaml
  user_counts:
    getproduct:   400
    postcheckout: 10
    getcart:      10
    postcart:     10
    emptycart:    10
```

- [x] **Step 3: Confirm the two YAMLs still have TopFull and RetryGuard off**

```powershell
Select-String -Path experiments\configs\scenario_calibration_frontend_constrained_50m.yaml,experiments\configs\scenario_calibration_productcatalog_constrained.yaml -Pattern "enabled:|run_number:|log_folder:|getproduct:|HOST"
```

Expected: `topfull_rl.enabled: false`, `retryguard.enabled: false`, no `HOST:` key, frontend `run_number: 5`, catalog `run_number: 4` (unless Task 0 bumped them).

---

### Task 2: Cool-off, pin frontend HPA off, Run A (frontend 50m 3×)

**Files:**
- Run: `experiments/configs/scenario_calibration_frontend_constrained_50m.yaml`
- Remote: delete `frontend-hpa` only (catalog HPA stays up until Task 4)

**Interfaces:**
- Consumes: Task 1 YAML
- Produces: remote folder `/home/idozacharia/experiments/results/calibration_frontend_constrained_50m_run5` (or the bumped name)

- [x] **Step 1: 300 s cool-off**

Task 8b's last reference hold ended ~23:30 UTC on 2026-09-21. If anything has been run since, or you are not sure the cluster is idle, wait. 300 s is required even when it looks idle — it is cheap compared to a contaminated freeze.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get hpa -n default; kubectl get deploy frontend,productcatalogservice -n default -o custom-columns=NAME:.metadata.name,CPU:.spec.template.spec.containers[0].resources.limits.cpu,REPLICAS:.status.readyReplicas"
Start-Sleep -Seconds 300
```

- [x] **Step 2: Delete frontend-hpa and wait for 1 ready replica**

```powershell
scp experiments/manifests/frontend-hpa.yaml topfull-master:/tmp/frontend-hpa.yaml
scp experiments/manifests/productcatalogservice-hpa.yaml topfull-master:/tmp/productcatalogservice-hpa.yaml

ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl delete hpa frontend-hpa -n default; kubectl scale deployment frontend --replicas=1 -n default; kubectl rollout status deployment/frontend -n default --timeout=120s; kubectl get hpa -n default; kubectl get pods -n default -l app=frontend"
```

Expected: `frontend-hpa` gone. Exactly one frontend pod Running. Leave `productcatalogservice-hpa` in place for Run A. Keep `/tmp/frontend-hpa.yaml` for the final restore. **Do not re-apply frontend-hpa until Task 6.**

- [x] **Step 3: Run the frontend hold**

```powershell
python experiments/run_scenario.py experiments/configs/scenario_calibration_frontend_constrained_50m.yaml
```

Expected: runner deploys v2, starts proxy (RL skipped), collectors, Locust. Wall time ~600 s plus setup/teardown. It must print that TopFull RL is OFF. Do not export `HOST`. Do not start a second create script.

If `run_scenario.py` exits non-zero, do **not** reuse the same `log_folder`. Restore HPAs (Task 6) and stop VMs (Task 8) unless you can classify it as a pre-Locust abort with no remote folder created.

---

### Task 3: Pull Run A and apply the hard gates

**Files:**
- Create (via pull): `experiments/results/campaign_48/calibration_frontend_constrained_50m_run5/`
- Read-only: that folder's Locust CSVs + `service_inbound.csv` + `resource_usage.csv` + `service_capacity.json`

**Interfaces:**
- Consumes: the YAML `log_folder` from Task 1
- Produces: a written PASS/FAIL for (1) Locust rows, (2) `n_sat_ticks`, (3) CPU peg. FAIL on (1) stops the battery.

- [x] **Step 1: Pull**

```powershell
python experiments/pull_results.py experiments/configs/scenario_calibration_frontend_constrained_50m.yaml
```

Expected: folder `experiments/results/campaign_48/calibration_frontend_constrained_50m_run5/` with `getcart.csv`, `service_inbound.csv`, `resource_usage.csv`, `service_capacity.json`, `rho_estimate_report.md`.

- [x] **Step 2: Locust CSV gate (hard STOP if header-only)**

This is the first live proof of the 8888 port fix.

```powershell
$run = "experiments\results\campaign_48\calibration_frontend_constrained_50m_run5"
foreach ($f in @("getcart.csv","getproduct.csv","postcart.csv","postcheckout.csv","emptycart.csv","total.csv")) {
  $lines = @(Get-Content (Join-Path $run $f) -ErrorAction Stop)
  "{0} lines={1}" -f $f, $lines.Count
  $lines | Select-Object -First 2
}
```

**PASS:** every file has a header **plus at least one data row** (typically hundreds of 1 s rows).  
**FAIL:** any of those files is header-only (1 line) or missing. **STOP the battery.** Do not start Run B. Do not start the 5×. Do not freeze. Jump to Task 6 (restore HPAs) then Task 8 (stop VMs). Record that v2 8888 deploy did not populate `metric_collector`.

- [x] **Step 3: Saturation + CPU peg gate (do not freeze yet)**

```powershell
python -c "from pathlib import Path; import sys; sys.path.insert(0,'experiments'); import capacity_frozen as cf; import estimate_service_mu as mu; p=Path(r'experiments/results/campaign_48/calibration_frontend_constrained_50m_run5'); print('n_sat', cf.count_sat_ticks(p,'frontend')); est={e.service:e for e in mu.estimate_run(p)}['frontend']; print('fail', est.inbound_failure_fraction, 'mu_sat', est.mu_sat)"
```

Also check CPU peg and the snapshot limit:

```powershell
python -c "import csv,json; from pathlib import Path; p=Path(r'experiments/results/campaign_48/calibration_frontend_constrained_50m_run5'); cap=json.loads((p/'service_capacity.json').read_text()); print('capacity', cap.get('frontend') or cap); rows=[r for r in csv.DictReader((p/'resource_usage.csv').open()) if r['service']=='frontend']; print('cpu_max_m', max(int(r['cpu_millicores']) for r in rows) if rows else 'NO_ROWS')"
```

**PASS for a later freeze:** `n_sat_ticks >= 10` (so `count_sat_ticks` ≥ 10 and the freeze `note` will be `null`, not `low_confidence`) **and** frontend CPU pegged near 50m (cpu_max around the 50m limit; mid-50s is the same peg class as run4's 56m) **and** `service_capacity.json` shows frontend `50`.  
**FAIL the freeze gate, but continue the battery:** `inbound_failure_fraction` stays `< 0.05` the whole hold, or `n_sat_ticks < 10`. Write that down. **Do not freeze. Do not silently overwrite run5.** The 5× retry is Task 5, after catalog.

Do not run `capacity_frozen.py freeze` in this task.

---

### Task 4: Cool-off, pin catalog HPA off + frontend ×4, Run B

**Files:**
- Run: `experiments/configs/scenario_calibration_productcatalog_constrained.yaml`

**Interfaces:**
- Consumes: Task 1 catalog YAML; frontend-hpa still deleted from Task 2
- Produces: remote `calibration_productcatalog_constrained_run4`

- [x] **Step 1: 300 s cool-off after Run A exits**

```powershell
Start-Sleep -Seconds 300
```

You may run Task 3's pull during this sleep if you have not already.

- [x] **Step 2: Delete catalog HPA and pin frontend at 4 replicas**

`run_scenario.py` will heal frontend CPU back to the paper table after Run A. Frontend-hpa must stay deleted so it cannot scale the pin back down.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl delete hpa productcatalogservice-hpa -n default --ignore-not-found; kubectl get hpa frontend-hpa -n default 2>&1; kubectl scale deployment frontend --replicas=4 -n default; kubectl rollout status deployment/frontend -n default --timeout=180s; kubectl get pods -n default -l app=frontend; kubectl get pods -n default -l app=productcatalogservice"
```

Expected: `frontend-hpa` still missing (if it came back, delete it again). Four frontend pods Running. One productcatalog pod. If frontend-hpa exists, delete it before the scale and re-check ready replicas = 4.

- [x] **Step 3: Run the catalog hold**

```powershell
python experiments/run_scenario.py experiments/configs/scenario_calibration_productcatalog_constrained.yaml
```

Expected: ~900 s Locust plus setup. RL off. Do not change `HOST`.

---

### Task 5: Pull Run B; optional frontend 5× only if Run A missed n_sat>=10

**Files:**
- Create (via pull): `experiments/results/campaign_48/calibration_productcatalog_constrained_run4/`
- Modify (only if Run A failed the sat gate): `experiments/configs/scenario_calibration_frontend_constrained_50m.yaml` → `run_number: 6` / `log_folder: calibration_frontend_constrained_50m_run6` and the 5× mix

**Interfaces:**
- Consumes: Run A sat-gate boolean from Task 3
- Produces: catalog PASS/FAIL write-up; optional run6 folder

- [ ] **Step 1: Pull catalog**

```powershell
python experiments/pull_results.py experiments/configs/scenario_calibration_productcatalog_constrained.yaml
```

- [ ] **Step 2: Catalog gates**

```powershell
python -c "from pathlib import Path; import sys; sys.path.insert(0,'experiments'); import capacity_frozen as cf; import estimate_service_mu as mu; p=Path(r'experiments/results/campaign_48/calibration_productcatalog_constrained_run4'); est={e.service:e for e in mu.estimate_run(p)}; print('catalog n_sat', cf.count_sat_ticks(p,'productcatalogservice'), 'fail', est['productcatalogservice'].inbound_failure_fraction, 'mu_sat', est['productcatalogservice'].mu_sat); print('frontend fail', est['frontend'].inbound_failure_fraction)"
```

Also confirm Locust `getproduct.csv` has data rows (not a STOP for the whole battery unless it is header-only *and* Run A already proved 8888 works — then it is a different bug; still do not freeze catalog from a header-only Locust run if inbound is also dead). Primary catalog success is mesh inbound, not Locust.

**PASS:** `productcatalogservice` `n_sat_ticks >= 10` **and** frontend inbound fail is far below Task 8b run3's **0.94** (healthy collateral is ~0.0x, not ~1). CPU pegged near 50m on catalog.  
**FAIL:** catalog still does not reject (`inbound_failure_fraction` stays `< 0.05` / `n_sat < 10`). **Stop raising `getproduct`.** Do not invent a 500/600-user follow-up in this plan. Record the numbers and continue to the optional 5× (if needed) then restore + stop.

- [ ] **Step 3: Skip 5× if Run A already has n_sat>=10**

If Task 3 printed `n_sat >= 10`, skip Step 4 and go to Task 6.

- [ ] **Step 4: Frontend 5× — only when Run A missed the sat gate**

Cool-off first:

```powershell
Start-Sleep -Seconds 300
```

Confirm `calibration_frontend_constrained_50m_run6` does not exist (remote + local). Then edit **only** these three places in `experiments/configs/scenario_calibration_frontend_constrained_50m.yaml`:

```yaml
run_number: 6
```

```yaml
  user_counts:
    getproduct:   50
    postcheckout: 25
    getcart:      50
    postcart:     25
    emptycart:    100
```

```yaml
log_folder: calibration_frontend_constrained_50m_run6
```

`spawn_rate` stays `50`. `duration_seconds` stays `600`. Keep frontend-hpa deleted. Scale frontend back to 1 replica before this hold (the catalog pin must not remain):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get hpa frontend-hpa -n default 2>&1; kubectl scale deployment frontend --replicas=1 -n default; kubectl rollout status deployment/frontend -n default --timeout=120s"
python experiments/run_scenario.py experiments/configs/scenario_calibration_frontend_constrained_50m.yaml
python experiments/pull_results.py experiments/configs/scenario_calibration_frontend_constrained_50m.yaml
```

Repeat Task 3 Step 2 (Locust rows) and Step 3 (`n_sat` / CPU) against `calibration_frontend_constrained_50m_run6`. Header-only → STOP freeze, still continue to Task 6 / Task 8. `n_sat < 10` → do **not** add a 7×. One 5× retry only.

---

### Task 6: Restore both HPAs and let HPA own frontend replicas

**Files:**
- Apply: `experiments/manifests/frontend-hpa.yaml`
- Apply: `experiments/manifests/productcatalogservice-hpa.yaml`

**Interfaces:**
- Consumes: the two manifests (re-scp if `/tmp` was wiped)
- Produces: `frontend-hpa` maxReplicas 4, `productcatalogservice-hpa` maxReplicas 2; frontend not left pinned at 4 with HPA missing

Do this even if a run failed. Best-effort restore **before** Task 8's VM stop.

- [ ] **Step 1: Re-scp and apply**

```powershell
scp experiments/manifests/frontend-hpa.yaml topfull-master:/tmp/frontend-hpa.yaml
scp experiments/manifests/productcatalogservice-hpa.yaml topfull-master:/tmp/productcatalogservice-hpa.yaml

ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl apply -f /tmp/frontend-hpa.yaml; kubectl apply -f /tmp/productcatalogservice-hpa.yaml; kubectl get hpa -n default; kubectl get deploy frontend,productcatalogservice -n default"
```

Expected: both HPAs exist with `MAXPODS` 4 and 2. Do **not** leave `kubectl scale --replicas=4` as the long-term replica policy — the applied HPA owns that. Do not wait for HPA to settle before stopping VMs.

---

### Task 7: Freeze only a passing service; update the capacity README

**Files:**
- Modify (CLI only, and only on PASS): `experiments/capacity/capacity_frozen.json`
- Modify: `experiments/capacity/README.md`
- Modify: `AGENTS.md` §4 remaining-work / next-free slots
- Modify: `docs/superpowers/specs/2026-09-21-s1-s6-loadgen-numbers-remaining-work.md` (note the new folders; Task 9 stays unchecked)

**Interfaces:**
- Consumes: `count_sat_ticks` from Tasks 3 and 5
- Produces: at most two new freeze rows (frontend and/or productcatalog). Checkout `1.34` and payment `0.30` stay untouched.

- [ ] **Step 1: Decide per service — do not freeze on hope**

Freeze with `--force` **only** when all of these are true for that service's **new** folder:

1. Locust CSVs for that hold are not header-only (Run A / 5×). Catalog may freeze from inbound if Locust getproduct has rows **or** inbound is clearly live; do not freeze if inbound is empty.
2. `python -c "... count_sat_ticks ..."` ≥ 10
3. The freeze note will be `null` (`n_sat_ticks < 10` writes `low_confidence` — **do not `--force` that**).
4. You are not pointing at run4's frontend `0.79` or run3's catalog `5.35`.

If a service fails, leave its existing 2026-09-21-v2 row in `capacity_frozen.json`.

- [ ] **Step 2: Freeze commands (run only the PASS ones)**

Frontend from the passing hold (`run5` if 3× passed; `run6` if only 5× passed):

```powershell
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/calibration_frontend_constrained_50m_run5 --service frontend --force
```

Catalog:

```powershell
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/calibration_productcatalog_constrained_run4 --service productcatalogservice --force
```

Use the actual folder name if Task 0 bumped the slot. After each freeze, open `experiments/capacity/capacity_frozen.json` and confirm `n_sat_ticks`, `note: null`, `calibrated_at_cpu_limit_millicores: 50`, `cluster_shape` still `topfull-worker-1=e2-standard-16`. If `note` is low_confidence, you froze in error — stop and restore the previous JSON from git rather than inventing a third hold.

- [ ] **Step 3: Update `experiments/capacity/README.md`**

Rewrite the 2026-09-21-v2 table rows that actually changed. Keep checkout/payment rows. Say explicitly if frontend stayed `0.79` / catalog stayed `5.35`. Point YAML next-free at whatever you did **not** use (after a clean 3×+catalog with no 5×: frontend 50m **run6**, catalog constrained **run5**).

- [ ] **Step 4: Update AGENTS.md and the remaining-work tracker**

In `AGENTS.md` §4, add one bullet: these holds ran; 8888 Locust CSVs populated or not; freeze values or "left in place". Next-free YAML slots. **Task 9 is still not started.** Do not claim a full recalibration battery.

---

### Task 8: Stop all three VMs (mandatory)

**Files:** none

**Interfaces:**
- Consumes: Task 6 restore attempted
- Produces: all three instances `TERMINATED`

- [ ] **Step 1: Stop**

Do this after Task 6 even if a run failed, even if you never froze, even if Run A header-only stopped the battery.

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=networks-workshop
```

- [ ] **Step 2: Confirm**

```powershell
gcloud compute instances list --project=networks-workshop --format="table(name,status)"
```

Expected: all three `TERMINATED` (or `STOPPING` that becomes `TERMINATED`). Do not start Task 9. Do not leave the VMs running "for later."

---

## Execution order (do not reorder)

1. Task 0 preflight  
2. Task 1 YAML user_counts  
3. Task 2 cool-off + frontend-hpa off + Run A 3×  
4. Task 3 pull + Locust/sat gates (header-only → Task 6 then Task 8)  
5. Task 4 cool-off + catalog HPA off + frontend ×4 + Run B  
6. Task 5 pull catalog; 5× only if Run A missed `n_sat>=10`  
7. Task 6 restore both HPAs  
8. Task 7 freeze + docs (PASS only)  
9. Task 8 stop VMs  

## Self-review

| Requirement | Task |
|---|---|
| Check VM status; start+HostName only if TERMINATED (Steps 3+5, not key install) | Task 0 |
| 300 s before first hold and between holds | Tasks 2, 4, 5 |
| Frontend 3× `30/15/30/15/60`, spawn 50, 600 s, TF+RG off, HPA deleted | Tasks 1–2 |
| Use run5 if free; bump if occupied | Task 0 + Task 1 |
| Locust CSV header-only → STOP, no freeze | Task 3 |
| Catalog `getproduct 400`, HPA off, frontend pinned at 4, no getproduct loop | Tasks 4–5 |
| 5× `50/25/50/25/100` only after catalog, only if 3× missed n_sat>=10 | Task 5 |
| Freeze `--force` only n_sat>=10 and not low_confidence; else keep old freeze | Task 7 |
| Restore HPAs from `experiments/manifests/` | Task 6 |
| Stop all three VMs after last run | Task 8 |
| v2 HOST `http://10.128.0.3:30440`, stats 8888+ | Task 0 + Global Constraints |
| No Task 9 | Global Constraints |
