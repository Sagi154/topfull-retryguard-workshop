# Project 1: Retries for Cloud Microservices

TAU Deepness Lab Workshop - Evaluate **RetryGuard** (you implement from the paper) on a **TopFull** Kubernetes microservice stack (Online Boutique).

**Before VMs:** [PREREQUISITES.md](PREREQUISITES.md) and [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md). **Steps:** workplan canvas + [SETUP-GUIDE.md](SETUP-GUIDE.md).

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
| **Prerequisites** | [PREREQUISITES.md](PREREQUISITES.md) - read before Phase 1 |
| **Mentor coordination** | [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md) - ask before provisioning VMs |
| TopFull paper | https://dl.acm.org/doi/abs/10.1145/3651890.3672253 |
| TopFull repo | https://github.com/kaist-ina/TopFull/tree/main |
| RetryGuard paper | `RetryGuard.pdf` (in this folder) |
| Workplan canvas | `canvases/topfull-retryguard-workplan.canvas.tsx` in Cursor (Why / How / Done when per step) |
| Detailed setup guide | [SETUP-GUIDE.md](SETUP-GUIDE.md) (full commands, Azure examples, troubleshooting) |

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
