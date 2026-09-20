# Ron Nezer’s setup vs what we actually run (2026-09-20)

> **Headline:** we copied Ron Nezer’s **three VMs and Kubernetes cluster**, but we are **not** running his TopFull / Locust setup. Experiments use a separate clone under `/home/idozacharia/TopFull` (stock KAIST + our patches). His working recipe is still on disk at `/home/user/` and was never pointed at by `run_scenario.py`.

Audited 2026-09-20 by SSH to the live copies (`topfull-master`, `topfull-load`, `topfull-worker-1`) and `git diff` against `kaist-ina/TopFull` `0c7af21` (same commit as this repo’s `TopFull/` submodule).

Related: [RON-TOPFULL-ACTIVATION-QUESTION.md](RON-TOPFULL-ACTIVATION-QUESTION.md), [EMAIL-DRAFT-RON-TOPFULL-LOAD.md](EMAIL-DRAFT-RON-TOPFULL-LOAD.md), [MENTOR-UPDATE.md](mentor-update/MENTOR-UPDATE.md) §1, [2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md](../docs/superpowers/specs/2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md).

---

## 1. The finding in one paragraph

The cluster is Ron’s machines: kubeadm, Istio, Online Boutique, cAdvisor, Locust host, swap off, his old Linux account still present. The **experiment path is ours**. We cloned TopFull again as `idozacharia`, rewrote KAIST paths to GCP IPs, added Locust 2.x / collectors / RetryGuard, and kept the paper `create.sh` mix. We did **not** adopt his detector CPU table, HPA, split-cart launcher, `GETPRODUCT=600`, Locust task-weight remix, `ronnezer/*` images, or proxy Host-match change.

So: same hardware and Kubernetes leftover, different experiment setup. His “it engaged” recipe is still on disk; the campaign never used it.

---

## 2. Three trees, same git commit

All three TopFull checkouts are `0c7af21` (`Update README.md`) from `https://github.com/kaist-ina/TopFull.git`. Nothing was forked. Differences are uncommitted local patches.

| Tree | Where | What it is |
|---|---|---|
| **KAIST upstream** | This repo’s `TopFull/` submodule (clean) | Paper scripts, hardcoded `/home/topfull-master` and `10.8.0.*` |
| **Ron’s clone** | `/home/user/TopFull` on master + load | His 2025 experiment setup (see §4) |
| **Workshop clone** | `/home/idozacharia/TopFull` | What `run_scenario.py` actually drives (see §3) |

`topfull-worker-1` has no TopFull git tree. It does still cache Ron’s Docker images (`ronnezer/frontend:ab|ac`, `ronnezer/product:ab|aj`). Live Boutique does **not** use them.

Ron’s original login is the generic Ubuntu account **`user`**. Workshop accounts (`idozacharia`, `idoza`, `sagi1`, …) were added later on the copied disks.

---

## 3. Workshop clone vs KAIST (what we run)

Live experiments: `/home/idozacharia/TopFull` on master (controller/proxy) and load (Locust). Worker has no clone.

### Master — 7 source files dirty

| File | What changed vs upstream |
|---|---|
| `global_config.json` | KAIST paths/IPs (`/home/topfull-master`, `10.8.0.22/23`) → our account and GCP private IPs (`/home/idozacharia`, proxy `10.128.0.3:8090`, Locust `10.128.0.2`, frontend `10.128.0.3:30440`) |
| `deploy_rl.py`, `metric_collector.py`, `overload_detection.py`, `proxy_online_boutique.go` | Same path rewrite for `global_config.json` |
| `metric_collector.py` | Extra: per-window `try/except` so missing Locust keys print `waiting for traffic` instead of crashing (`experiments/patch_metric_collector.py`) |
| `overload_detection.py` | Extra: Detector loads `/home/idozacharia/experiments/topfull_run_quotas.json` if present (`TOPFULL_RUN_QUOTAS_OVERLAY`, inserted by `run_scenario.py`). **Paper CPU table is otherwise unchanged.** |
| `resource_collector.py` | `getcAdvisorIP()` lists whatever cAdvisor pods exist instead of assuming 5 worker IPs |
| `instance_scaling.py` | Paper `[15,2,3,1,5,1,1,1,5,1,5]` (40 pods / 5 workers) → workshop `[2,1,1,1,1,1,1,1,1,1,1]`. Live cluster is **1 replica each**. |

RL / admission / proxy **logic is unchanged** in this tree. The Go limiter, `deploy_rl.py` training loop, and Boutique YAML in the clone are still upstream.

Dead leftover: `metric_collector.py` still has a default hostname `honey3.kaist.ac.kr`. Live collection uses `locust_url` from `global_config.json`.

### Load — 3 files dirty + leftover probe script

| File | What changed vs upstream |
|---|---|
| `locust_online_boutique.py` | Locust 2.x: `events.request` instead of `request_success` / `request_failure`; proxy `10.8.0.4:8090` → `10.128.0.3:8090` |
| `online_boutique_create.sh` / `create2.sh` | `${VAR:-default}` so the runner can inject user counts; `locust` → `/home/idozacharia/TopFull/venv/bin/locust`; host `10.8.0.4:30440` → `10.128.0.3:30440` |

Spawn math is still upstream: `-r $((count / RATE))`, and `getcart`/`postcart`/`emptycart` still share one `$CART` swarm. Those are in the paper scripts too, not VM-only bugs.

Untracked leftover: `online_boutique_create_probe.sh` from the 2026-09-18 frontend-2× probe (uses `-r $RATE` directly). Shared `create.sh` was never switched to that. `run_fig8` / `run_fig15` / train-ticket scripts were **not** patched and still point at `10.8.0.4`. The runner does not use them.

Runtime extras next to TopFull (not in the KAIST tree): `venv/`, `.bak.phase4` backups, workshop collectors’ CSVs under `src/logs/`.

---

## 4. Ron’s clone vs KAIST (what he actually ran)

His notes, helpers, and second TopFull tree live under `/home/user/` (still present on all three VMs). `extra_changes.txt` records swap-off and static IPs. `part1.sh`–`part7.sh` are his kubeadm/Docker/cAdvisor/Go/pip bootstrap.

### Cluster / OS (his, not KAIST)

- Disabled swap (`/etc/fstab`) and set static IPs (`netplan`).
- Docker + cri-dockerd, kubeadm 1.26, Calico, cAdvisor, Go 1.13.8.
- Unpinned several pip packages (`tensorflow`, `protobuf`, `keras`, …) and **removed `WALinuxAgent`**.
- Namespace ResourceQuota `compute-resources.yaml`: **2600m CPU** hard cap.
- HPA YAMLs for frontend / productcatalog (`frontend-hpa.yaml` in `$HOME`; fuller `hpa.yaml` inside his TopFull `deployments/`).
- `metrics-server`: `hostNetwork: true` so `kubectl top` works.

Those HPA/quota objects are **not** on the live cluster now (only Istio’s `istiod` HPA). Live Boutique uses paper-style images (`qkrwogud676/…`, `gcr.io/google-samples/…`), 1 replica each.

### TopFull source (`/home/user/TopFull`) — behavior that is actually his

Paths/IPs are the same *class* of change we later redid for `idozacharia`, but pointed at his LAN: `/home/user/…`, proxy `192.168.0.136:8090`, Locust `192.168.0.122`.

| File | What he changed |
|---|---|
| `instance_scaling.py` | Paper `[15,2,3,…]` → **`[8,1,1,1,1,1,1,1,1,1,1]`** (8× frontend). Workshop later rewrote this again to `[2,1,…]`. |
| `overload_detection.py` | **Rewrote the paper CPU table**: frontend 1500, checkout **4500**, productcatalog 1000, ads 1500, cart 300, recs 1000 (paper was 1000/1000/500/1000/1000/2000). Workshop clone does **not** have this. |
| `resource_collector.py` | Dynamic cAdvisor IPs (1 worker, not 5 hardcoded). Also **stopped dropping CPU samples ≤ 2**. Workshop has the dynamic-IP part only. |
| `metric_collector.py` | Prints `TOTAL=` plus per-API P95. No crash-guard (that try/except is ours). |
| `proxy_online_boutique.go` | Prints `TOTAL_RPS`. **Dropped Host matching** on GET `/cart` and GET `/product/*` so those routes match regardless of `FrontendUrl`. Workshop proxy only has the path rewrite. |
| `online_boutique_original_custom.yaml` | Commented out **liveness probes**; bumped CPU/memory (request=limit) — e.g. frontend 1500m, productcatalog **2000m**, cart **2500m**, redis 700m. Workshop YAML is still upstream. |
| `deployments/hpa.yaml` | **New file**: HPA frontend + productcatalog, 1–20 replicas, 85% CPU. |

He was running a **smaller cluster, hotter CPU limits, HPA, and a slightly different proxy match**.

### Loadgen (`/home/user/TopFull/TopFull_loadgen`)

The shared `create.sh` the workshop uses is **not** this. His copy:

- `GETPRODUCT=600` (paper/workshop default is 100).
- Float spawn rates via `awk` (`count/RATE`) instead of bash integer division.
- **Dropped `-t 15m`** on `create.sh` (runs until killed).
- Locust **task weights** rewritten: checkout 50→**500**, getcart 30→**100**, postcart 15→**1**, emptycart 15→**1**, getproduct 150→**100**. Mix is much more checkout/getcart-heavy.
- New **`frontend.sh`**: splits getcart / postcart / emptycart into **separate Locust swarms** (the merged-`$CART` problem in the 2026-09-20 loadgen design). Example counts: emptycart=100, postcheckout=50, 6-minute runs.

Workshop `idozacharia` loadgen only has Locust 2.x + GCP IPs + `${VAR:-default}`. His mix/weights/split-cart launcher were **not** carried over.

### Custom images (on the worker, not currently deployed)

Cached on `topfull-worker-1`:

- `ronnezer/frontend:ab` and `:ac`
- `ronnezer/product:ab` and `:aj`

His bashrc `setf` / `setp` pull those and **strip readiness/liveness probes**. Live frontend is still `qkrwogud676/onlineboutique_frontend:v0.0.2`. There is also a leftover `galhorowitztau/frontend:ab`.

Useful aliases still in `/home/user/.bashrc` on master: `runproxy`, `runtopfull`, `runmetric`, `runscale`, `runonline`, `runauto`, `fcpu` / `pcpu` (set frontend/productcatalog CPU), `getfull` (curl proxy `/thresholds`).

---

## 5. Inherited vs leftover

**Still in the live path (reimplemented, not his files):** 3 VMs, 1 worker, kubeadm + Istio + Boutique, dynamic cAdvisor lookup, scaled-down `instance_scaling`.

**Sitting unused in `/home/user`:** custom CPU table, proxy Host-match change, HPA, ResourceQuota, split-cart `frontend.sh`, `GETPRODUCT=600`, task-weight remix, `ronnezer/*` images.

MENTOR-UPDATE §1 (“copied his working TopFull environment, then made workshop changes”) is true for **the VMs**. It overstates how much of **his experiment config** we kept. Live 1-replica Boutique is a workshop choice, not a faithful copy of his `[8,1,1,…]` scaling.

---

## 6. Why this matters

The held “ask Ron how TopFull engaged” email assumed we were mimicking his recipe (`create.sh` defaults, 1 replica, paper CPU). We were not.

His load was heavier and shaped differently (600 getproduct users, checkout-heavy weights, independent cart swarms), frontend was 8 replicas at one point, detector quotas were far above the paper table (checkout 4500m), and he had custom images + HPA. Replaying **his** files is a separate decision from raising Locust users on **our** tree.

Do **not** silently switch `run_scenario.py` onto `/home/user/TopFull`. If the team wants to try his recipe, copy specific knobs into workshop configs and record which ones, rather than pointing the runner at his home directory.

---

## 7. How to re-read the files (if VMs are up)

```powershell
ssh topfull-master "sudo ls /home/user /home/user/TopFull"
ssh topfull-master "sudo -u user git -C /home/user/TopFull status -sb"
ssh topfull-load "sudo ls /home/user/TopFull/TopFull_loadgen/frontend.sh"
```

Workshop tree (what we run):

```powershell
ssh topfull-master "git -C /home/idozacharia/TopFull status -sb"
ssh topfull-load "git -C /home/idozacharia/TopFull status -sb"
```
