# Project 1: Retries for Cloud Microservices

TAU Deepness Lab Workshop - Evaluate **RetryGuard** (you implement from the paper) on a **TopFull** Kubernetes microservice stack (Online Boutique).

**Before VMs:** [PREREQUISITES](Guides%20and%20Info/PREREQUISITES.md) and [MENTOR-COORDINATION](Guides%20and%20Info/MENTOR-COORDINATION.md). **Steps:** [WORKPLAN](Guides%20and%20Info/WORKPLAN.md) (or interactive canvas in Cursor) + [SETUP-GUIDE](Guides%20and%20Info/SETUP-GUIDE.md). **SSH to GCP VMs:** [CONNECT-VMS](Guides%20and%20Info/CONNECT-VMS.md).

## Repo layout

| Path | Contents |
|------|----------|
| [Guides and Info/](Guides%20and%20Info/) | Setup, workplan, SSH playbook, presentation notes |
| [TopFull/](TopFull/) | Upstream TopFull clone (read locally; still clone on VMs) |
| [context/](context/) | Papers and decks (`RetryGuard.pdf`, `TopFull.pdf`, …) |
| [canvases/](canvases/) | Interactive workplan canvas |

## Viewing the workplan

Clone this repository, then use either format below.

### Markdown (any editor or GitHub)

Open [Guides and Info/WORKPLAN.md](Guides%20and%20Info/WORKPLAN.md). Same phases as the canvas (Why / How / Done when). Readable on GitHub without installing anything.

### Interactive canvas (Cursor IDE)

1. Install [Cursor](https://cursor.com) (free tier is enough).
2. Clone and open the project folder:
   ```bash
   git clone https://github.com/Sagi154/topfull-retryguard-workshop.git
   cd topfull-retryguard-workshop
   ```
   In Cursor: **File ? Open Folder** ? select `topfull-retryguard-workshop`.
3. Open the canvas from **Cursor’s managed canvases folder** (required for preview):
   - **Windows:** `%USERPROFILE%\.cursor\projects\c-Users-sagi1-Projects-Workshop\canvases\topfull-retryguard-workplan.canvas.tsx`
   - **macOS/Linux:** `~/.cursor/projects/<workspace-id>/canvases/topfull-retryguard-workplan.canvas.tsx`

   Use **File ? Open File** and paste that path.

   The copy at `canvases/topfull-retryguard-workplan.canvas.tsx` in this repo is for **git** (same content). Cursor’s Canvas compiler only runs on the file under `.cursor/projects/.../canvases/`. Opening only the repo copy shows errors (`Cannot find module 'cursor/canvas'`) and **no Canvas preview** — that is expected.

4. Cursor renders a **Canvas** panel (beside chat or split editor): collapsible phases, checklists, VM tables, and experiment matrix.

**Red squiggles on the repo copy?** Run once: `cd canvases && npm install` (React types for the editor). Or ignore them and use the managed path above.

**Still no Canvas?** Command Palette (`Ctrl+Shift+P`) ? search **Canvas**. Update Cursor if needed.

Use the canvas for day-to-day progress; use [WORKPLAN.md](Guides%20and%20Info/WORKPLAN.md) when sharing links or working outside Cursor. After editing, sync the managed file and the repo copy under `canvases/` before committing.

## Stack

| Component | Role |
|-----------|------|
| **TopFull** | Overload control at entry (RL rate controller + Go proxy) |
| **RetryGuard** | Dynamic retry on/off per service during miscoordination |
| **Online Boutique** | Microservice benchmark app (from TopFull repo) |
| **Locust** | Load generation |

## Resources

| Resource | Link |
|----------|------|
| **Prerequisites** | [PREREQUISITES.md](Guides%20and%20Info/PREREQUISITES.md) - read before Phase 1 |
| **Mentor coordination** | [MENTOR-COORDINATION.md](Guides%20and%20Info/MENTOR-COORDINATION.md) - ask before provisioning VMs |
| TopFull paper | https://dl.acm.org/doi/abs/10.1145/3651890.3672253 |
| TopFull (local clone) | [TopFull/](TopFull/) |
| TopFull upstream | https://github.com/kaist-ina/TopFull/tree/main |
| RetryGuard paper | [context/RetryGuard.pdf](context/RetryGuard.pdf) |
| **Workplan (markdown)** | [WORKPLAN.md](Guides%20and%20Info/WORKPLAN.md) |
| **Workplan (canvas)** | [canvases/topfull-retryguard-workplan.canvas.tsx](canvases/topfull-retryguard-workplan.canvas.tsx) |
| Detailed setup guide | [SETUP-GUIDE.md](Guides%20and%20Info/SETUP-GUIDE.md) |
| SSH playbook | [CONNECT-VMS.md](Guides%20and%20Info/CONNECT-VMS.md) |

## Architecture

```
+------------------+     +----------------------------------+
| Load Generator   |---->| Master Node                      |
| (Locust)         |     | Go proxy, RL, RetryGuard, K8s   |
+------------------+     +----------------------------------+
                                    |
              +---------------------+---------------------+
              v                     v                     v
         Worker nodes: Online Boutique pods + cAdvisor
```

## VM Requirements

| Role | Count | Min Specs | OS |
|------|-------|-----------|----|
| Master Node | 1 | 8 vCPU, 16 GB RAM | Ubuntu 20.04 |
| Worker Nodes | 2-5 | 8 vCPU, 16 GB RAM | Ubuntu 20.04 |
| Load Generator | 1 | 8 vCPU, 16 GB RAM | Ubuntu 20.04 |

## Experiments (only these two)

| Run | Overload control | Retries | When |
|-----|------------------|---------|------|
| **Baseline** | TopFull | Default (retries on) | Phase 5 |
| **Primary** | TopFull | RetryGuard | Phase 6 |

Same load scenario both times; compare metrics.

## Quick Start (after VMs are provisioned)

### 1. Clone on master + load-gen

```bash
git clone https://github.com/kaist-ina/TopFull.git
```

### 2. K8s cluster setup (all nodes)

Follow Phase 2 in the workplan canvas - Docker, cri-docker, K8s 1.26, Calico, cAdvisor, join workers.

### 3. Deploy Online Boutique (master)

```bash
kubectl apply -f TopFull/TopFull_master/online_boutique_scripts/deployments/online_boutique_original_custom.yaml
kubectl apply -f TopFull/TopFull_master/online_boutique_scripts/deployments/metric-server-latest.yaml
cd TopFull/TopFull_master/online_boutique_scripts/src
python instance_scaling.py
```

### 4. Run TopFull baseline (in order)

```bash
# Terminal 1 (master): proxy
cd TopFull/TopFull_master/online_boutique_scripts/src/proxy
go run proxy_online_boutique.go

# Terminal 2 (master): RL controller
cd TopFull/TopFull_master/online_boutique_scripts/src
python deploy_rl.py

# Load-gen node: traffic
cd TopFull/TopFull_loadgen
./online_boutique_create.sh
./online_boutique_create2.sh

# Terminal 3 (master): metrics
cd TopFull/TopFull_master/online_boutique_scripts/src
python metric_collector.py
```

### 5. Add RetryGuard and re-run

Deploy RetryGuard controller (Algorithm 1 from paper), then repeat the same load run and collect metrics again.

## Configuration Checklist

Edit before running (`TopFull_master/online_boutique_scripts/src/`):

- [ ] `global_config.json` - paths, `proxy_url`, `frontend_url`, `locust_url`
- [ ] `proxy/proxy_online_boutique.go:28` - config path
- [ ] `deploy_rl.py:13` - config path
- [ ] `metric_collector.py:9` - config path
- [ ] `overload_detection.py:10` - config path
- [ ] `resource_collector.py:456` - cAdvisor count = number of worker nodes
- [ ] `TopFull_loadgen/online_boutique_create.sh` - `--host=http://MASTER_IP:30440`
- [ ] `TopFull_loadgen/locust_online_boutique.py:293` - proxy `http://MASTER_IP:8090`

## Key Metrics

- **Goodput** (rps) - successful responses within latency SLO
- **P99 Latency** (ms)
- **Rejection Rate** (%)
- **Retries per request** - retry storm size
- **CPU / Memory** - pod resource usage
- **Pod replica count** - over-scaling from retry amplification
