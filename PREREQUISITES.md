# Prerequisites - Before Starting the Workplan

Complete this checklist **before** provisioning cloud VMs (Phase 1).  
**Stack:** TopFull (overload control) + **RetryGuard** (you implement from the paper) on Kubernetes.

Related docs: [README.md](README.md) | [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md) | [SETUP-GUIDE.md](SETUP-GUIDE.md) | workplan canvas (`canvases/topfull-retryguard-workplan.canvas.tsx`)

---

## Quick "am I ready?" checklist

- [ ] TopFull repo cloned and architecture understood
- [ ] `global_config.json` and experiment run order understood
- [ ] RetryGuard paper: Algorithm 1 + K8s evaluation settings read
- [ ] Mentors: see [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md)
- [ ] SSH key created
- [ ] `SETUP-GUIDE.md` skimmed for Phases 0-2

When all are checked, start **Phase 0** in the workplan canvas, then **Phase 1** (provision VMs).

---

## 1. On your Windows PC (do this first - $0)

| Prerequisite | Why |
|--------------|-----|
| **Git** | Clone TopFull |
| **SSH client** | Built into Windows 10/11 (`ssh`, `ssh-keygen`) |
| **Text editor / IDE** | Edit configs (e.g. Cursor) |
| **WSL2** (optional) | Not required; cluster runs on Linux VMs. Handy for `git` and reading code locally |

### Clone and read (do not run on cloud yet)

```powershell
git clone https://github.com/kaist-ina/TopFull.git
```

| File | What you learn |
|------|----------------|
| `TopFull/README.md` | Official Kubernetes install order |
| `TopFull_master/online_boutique_scripts/src/global_config.json` | Every IP and path you will change |
| `TopFull_master/online_boutique_scripts/src/deploy_rl.py` | TopFull RL controller entry point |
| `TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go` | Entry proxy / rate limiting |
| `TopFull_master/online_boutique_scripts/deployments/online_boutique_original_custom.yaml` | What gets deployed to Kubernetes |
| `RetryGuard.pdf` (Workshop folder) | Sec. 4 (controller), Sec. 6.2 (K8s experiment: threshold, interval) |

**Done when:** You can explain: *loadgen -> master proxy -> Online Boutique pods -> TopFull adjusts rates -> metrics in `logs/`*, and where RetryGuard will sit (toggle retries when rejection stays high).

---

## 2. Mentors (before Phase 1)

See **[MENTOR-COORDINATION.md](MENTOR-COORDINATION.md)** - short checklist and a message template you can send.


---

## 3. Skills (workshop expectations)

You do not need to be an expert, but you should be comfortable learning:

| Area | Used for |
|------|----------|
| **Linux CLI** | SSH, `apt`, editing files, `tmux` on VMs |
| **Kubernetes basics** | `kubectl get pods`, `apply`, `logs` |
| **Python** | RetryGuard controller; running TopFull scripts |
| **Go (light)** | Only if you integrate retries via the TopFull proxy (`go run` on master) |
| **Metrics / analysis** | Reading CSVs in `logs/`, tables or plots for the report |

If Kubernetes is new, budget extra time in Phases 2-4; see [SETUP-GUIDE.md](SETUP-GUIDE.md).

---

## 4. Accounts and access (before Phase 1)

| Item | Required? |
|------|-----------|
| Cloud account (Azure / AWS / GCP) - create VMs, network, firewall | **Yes** |
| SSH key pair (`ssh-keygen -t ed25519`) | **Yes** |
| Payment method or lab credits | **Yes** |
| GitHub (public clone) | **Yes** |
| Local GPU | **No** |
| Kubernetes on Windows | **No** - cluster is on **Ubuntu 20.04** VMs |

---

## 5. Hardware and environment

| Item | Notes |
|------|--------|
| **Your PC** | SSH, git, edit configs, implement RetryGuard, write report |
| **Cloud VMs** | Created in Phase 1 - plan **at least 4**: 1 master, 2 workers, 1 load generator |

---

## 6. Software versions (install on VMs during the workplan)

| Component | Target |
|-----------|--------|
| OS on all VMs | Ubuntu **20.04** LTS |
| Kubernetes | **1.26** (TopFull README) |
| Container runtime | Docker + **cri-dockerd** |
| Go (master only) | **1.13.8** |
| Python | 3.x + venv; `TopFull_master/requirements.txt`, `TopFull_loadgen/requirements.txt` |
| Locust (loadgen) | **2.8.6** |

---

## 7. RetryGuard-specific (you implement it)

Before **Phase 6**, you should already have:

| Prerequisite | Detail |
|--------------|--------|
| Paper read | Algorithm 1; Sec. 4.3 (rejections, delays, retry volume) |
| Baseline experiment done | Phase 5 complete - TopFull + load + `metric_collector` working |
| Metrics source | Per-API rejection rates from TopFull's built-in collectors (`metric_collector.py`, `overload_detection.py`) |
| Integration design | How "retries OFF" is enforced in your stack |
| Python on master | Same venv as TopFull scripts |

### Implementation outline (from paper)

1. Poll rejection rate on a fixed interval (e.g. 30 seconds).
2. If above threshold (e.g. **20%**) for N consecutive intervals -> **disable** retries.
3. If below threshold for N intervals -> **re-enable** retries.
4. Re-run the **same** Locust scenario as the Phase 5 baseline and compare metrics.

---

## 8. Recommended order before Phase 1

```
1. Read RetryGuard.pdf + skim TopFull repo (global_config, deploy_rl, proxy, deployment YAML)
2. Coordinate with mentors ([MENTOR-COORDINATION.md](MENTOR-COORDINATION.md))
3. Generate SSH key
4. Skim SETUP-GUIDE.md Phases 0-2
5. Then create VMs (Phase 1)
```

---

## 9. What you do not need beforehand

- A running Kubernetes cluster on your laptop
- RetryGuard source code from the lab
- All Python dependencies installed on Windows
- Five worker nodes (two workers is fine to start)
- DAGOR or any second overload-control system
- DiffTry (out of scope for this project)

---

## 10. Two experiments only (reminder)

| Run | Overload control | Retries | When |
|-----|------------------|---------|------|
| **Baseline** | TopFull | Default (retries on) | Phase 5 |
| **Primary** | TopFull | RetryGuard | Phase 6 |

Same load scenario both times; only the retry policy changes.
