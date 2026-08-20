# Setup Guide: TopFull + RetryGuard (step-by-step)

This document explains **what each workplan step means**, **what to do concretely**, and **how you know it worked**. Use it together with the workplan canvas (`../canvases/topfull-retryguard-workplan.canvas.tsx`).

**Before Phase 1:** complete [PREREQUISITES.md](PREREQUISITES.md) and [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md).

**Stack:** TopFull (overload control) + RetryGuard (you implement from the paper) on Kubernetes, Online Boutique app, Locust load generator.

**Out of scope:** DAGOR, DiffTry, extra overload-control baselines (unless mentors say otherwise).

---

## Phase 0 - Preparation

### 0a. Choose cloud provider and get credits

**What this is:** You need Linux VMs in the cloud. TopFull was evaluated on Azure; Ubuntu 20.04 is required.

**What to do:**
1. Ask your mentors if the lab provides Azure/AWS/GCP credits or a shared subscription (see [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md)).
2. If you pay yourself: create an account on [Azure](https://azure.microsoft.com), [AWS](https://aws.amazon.com), or [GCP](https://cloud.google.com).
3. Budget roughly **$3-9/day** while VMs run (3 VMs, ~$1-3/hr depending on size). **Stop/deallocate VMs when not working.**

**Done when:** You can log into the cloud portal and create a virtual machine.

---

### 0b. Read TopFull and key files (on your PC)

**What this is:** Understand the repo before spending money on VMs.

**What to do:** Open `../TopFull` in this workshop repo (already cloned). Still `git clone` TopFull on the master and loadgen **VMs** later (Phase 1d).

Read these (don't run yet):
| File | Why |
|------|-----|
| `../TopFull/README.md` | Official K8s setup order |
| `../TopFull/TopFull_master/online_boutique_scripts/src/global_config.json` | All IPs and paths you will edit |
| `../TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py` | TopFull RL controller |
| `../TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go` | Entry proxy |
| `../TopFull/TopFull_master/online_boutique_scripts/deployments/online_boutique_original_custom.yaml` | App deployment |
| `../context/RetryGuard.pdf` | Sec. 4 (controller), Sec. 6.2 (~20% threshold, 30s interval) |

**Done when:** You know where config lives and that experiments run in a fixed order (proxy -> deploy_rl -> load -> metric_collector).

---

### 0c. Coordinate with mentors (RetryGuard)

**What this is:** You implement RetryGuard yourself (Algorithm 1 from `RetryGuard.pdf`). Mentors do not need to provide source code, but you must agree where retries are toggled before Phase 6.

**What to do:**
1. Complete [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md) (credits, cloud provider, integration point, report format).
2. Read RetryGuard Section 4 (controller) and Section 6.2 (~20% rejection threshold, 30s polling interval).

**Done when:** Mentor checklist is done. Integration point is confirmed: RetryGuard toggles Istio VirtualService retry policies per service on the master node (matches paper Sec. 4). No proxy-level or app-level toggle needed.

---

### 0d. Generate SSH key (on your Windows PC)

**What this is:** How you will log into Linux VMs from Windows.

**What to do:**
```powershell
ssh-keygen -t ed25519 -C "workshop-topfull"
```
Save to default location (`C:\Users\YOU\.ssh\id_ed25519`). When creating VMs, paste the **public** key (`id_ed25519.pub`) so you can SSH without passwords.

**Done when:** `ssh -i ~/.ssh/id_ed25519 user@VM_IP` works after VMs exist.

---

## Phase 1 - Provision cloud VMs

### 1a. Create 3 Ubuntu 20.04 VMs

**What this is:** A small Kubernetes cluster needs separate machines (or VMs) for control plane, workers, and load generation.

**Minimum layout:**

| VM name (example) | Role | Runs |
|-------------------|------|------|
| `topfull-master` | Master | `kubeadm` control plane, TopFull proxy, `deploy_rl.py`, `metric_collector.py` |
| `topfull-worker-1` | Worker | Online Boutique pods, cAdvisor |
| `topfull-loadgen` | Load generator | Locust scripts only |

The paper used **5 workers**; this setup uses **1 worker**.

**Specs per VM:** at least **8 vCPUs, 16 GB RAM**, **Ubuntu 20.04 LTS** (not 22.04 - TopFull README targets 20.04).

**Example: Azure Portal**
1. Create a **Resource group** (e.g. `topfull-rg`).
2. Create a **Virtual network** with one subnet (e.g. `10.0.0.0/16`).
3. For each VM: **Create virtual machine**
   - Image: **Ubuntu Server 20.04 LTS**
   - Size: **Standard_D8ds_v5** (8 vCPU, 32 GB) or similar
   - Authentication: **SSH public key** (paste your `.pub` file)
   - Networking: attach to the same VNet/subnet
   - Public IP: optional for master/loadgen if you SSH from home; workers can be private-only if master can reach them
4. Tag VMs by role so you don't confuse them.

**Example: AWS**
- Same idea: one VPC, one subnet, EC2 instances `m5.2xlarge`, Ubuntu 20.04 AMI, same security group.

**Done when:** You have 3 running VMs, all Ubuntu 20.04, all in the same network.

---

### 1b. Configure networking (firewall / security group)

**What this is:** VMs must talk to each other; you must reach the app and SSH.

**Open these ports:**

| Port | Where | Purpose |
|------|--------|---------|
| 22 | All (or bastion) | SSH |
| 6443 | Master | Kubernetes API |
| 10250 | Workers | kubelet |
| 30440 | Master (NodePort) | Online Boutique frontend |
| 8090 | Master | TopFull Go proxy |
| All traffic | Inside subnet | Pod network, node-to-node |

**Azure:** Network Security Group rules on the subnet or each NIC.  
**AWS:** Security group inbound rules.

Allow **east-west** traffic inside the VNet (worker -> master, loadgen -> master).

**Done when:** From master you can `ping WORKER_PRIVATE_IP` and from loadgen you can `ping MASTER_PRIVATE_IP`.

---

### 1c. SSH in and record IPs

**What this is:** You will paste these IPs into `global_config.json` and Locust scripts.

**What to do:**
```bash
ssh azureuser@MASTER_PUBLIC_IP   # or ubuntu@ on AWS
ip addr show                    # note private IP, e.g. 10.0.1.4
```

Create a note:
```
MASTER_PRIVATE_IP=10.0.1.4
MASTER_PUBLIC_IP=...
LOADGEN_PRIVATE_IP=10.0.1.5
WORKER1_PRIVATE_IP=...
```

**Done when:** You can SSH to every VM and private IPs are written down.

---

### 1d. Clone TopFull on master and load-gen

**What this is:** Only these two machines need the git repo (workers only run containers).

**What to do (on master AND loadgen):**
```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/kaist-ina/TopFull.git
cd TopFull
```

**Done when:** `ls TopFull/TopFull_master` exists on both machines.

---

## Phase 2 - Kubernetes cluster

Run everything in the **TopFull README** "Setting Kubernetes environment" on **each node** first, then master-only steps.

### 2a. Docker + cri-docker on ALL nodes

**Why:** Kubernetes 1.26 in this repo uses Docker via `cri-dockerd`, not containerd alone.

**On every VM (master + all workers):**
1. Disable swap: `sudo swapoff -a` (and comment out swap in `/etc/fstab` for persistence).
2. Install Docker (script from README or `curl -fsSL https://get.docker.com | sh`).
3. Install **cri-dockerd** (see TopFull README - download release, install binary, enable systemd units).
4. Set Docker cgroup driver to **systemd** (`/etc/docker/daemon.json`).
5. Load kernel modules: `br_netfilter`, sysctl for bridge iptables (README block).

**Done when:** `sudo systemctl status docker` and `cri-docker` are active; `sudo docker info | grep Cgroup` shows `systemd`.

---

### 2b. kubeadm, kubelet, kubectl 1.26 on ALL nodes

**On every node:**
```bash
# Follow TopFull README apt repo setup for Kubernetes 1.26
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
kubectl version --short
```

**Done when:** `kubeadm version` works on all nodes.

---

### 2c. Initialize cluster (master only)

**On master only:**
```bash
sudo kubeadm init \
  --pod-network-cidr=192.168.0.0/16 \
  --service-cidr=10.96.0.0/12 \
  --cri-socket=unix:///var/run/cri-dockerd.sock

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

**Done when:** `kubectl get nodes` shows the master (may be NotReady until CNI).

---

### 2d. Calico CNI (master only)

```bash
cd ~/TopFull/TopFull_master
kubectl apply -f calico.yaml
kubectl get pods -n kube-system -w
```

**Done when:** Calico pods are `Running` and master node is `Ready`.

---

### 2e. Join workers (each worker)

**On master:**
```bash
sudo kubeadm token create --print-join-command
```

**On each worker:** run the printed command and **append:**
```
--cri-socket unix:///var/run/cri-dockerd.sock
```

**Done when:** `kubectl get nodes` shows all workers `Ready`.

---

### 2f. cAdvisor (master)

```bash
cd ~/TopFull/TopFull_master/online_boutique_scripts/cadvisor
kubectl kustomize deploy/kubernetes/base | kubectl apply -f -
kubectl get pods -A | grep cadvisor
```

**Done when:** One cAdvisor pod per worker (or per node policy in manifest).

---

### 2g. Verify cluster

```bash
kubectl get nodes
kubectl get po -A -o wide
```

**Done when:** All nodes `Ready`, system pods `Running`, no CrashLoopBackOff.

---

### 2h. Install Istio service mesh (master only)

**Why:** RetryGuard controls retries by toggling Istio VirtualService retry policies per service — the decided integration point (matches paper Sec. 4). Istio injects Envoy sidecar proxies into each pod, giving mesh-level retry control over inter-service calls.

```bash
# Download Istio 1.17.8 (compatible with K8s 1.26)
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.17.8 sh -
echo 'export PATH=$PATH:$HOME/istio-1.17.8/bin' >> ~/.bashrc
source ~/.bashrc

# Install minimal profile (avoids unnecessary components)
istioctl install --set profile=minimal -y

# Enable automatic sidecar injection in the default namespace
kubectl label namespace default istio-injection=enabled

# Verify
kubectl get pods -n istio-system   # istiod should be Running
kubectl get ns default --show-labels  # should show istio-injection=enabled
```

If Istio conflicts with Calico: `kubectl get pods --all-namespaces` — no CrashLoopBackOff.

**Done when:** `istiod` is Running in `istio-system`; default namespace has `istio-injection=enabled`.

---

## Phase 3 - Dependencies

### 3a. Python on master

```bash
sudo apt-get install -y python3 python3-pip python3-venv
cd ~/TopFull
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r TopFull_master/requirements.txt
```

If some packages fail (`python-apt`, `systemd-python`), skip them - they are Ubuntu-system packages not needed on a plain venv install.

**Done when:** `python -c "import ray; import kubernetes"` works.

---

### 3b. Go 1.13.8 on master

```bash
wget https://go.dev/dl/go1.13.8.linux-amd64.tar.gz
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go1.13.8.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
echo 'export GOPATH=$HOME/TopFull/TopFull_master/go' >> ~/.bashrc
source ~/.bashrc
go version
```

**Done when:** `go version` shows 1.13.8.

---

### 3c. Locust on load-gen

```bash
sudo apt-get install -y python3-pip python3-venv
cd ~/TopFull
python3 -m venv venv
source venv/bin/activate
pip install -r TopFull_loadgen/requirements.txt
locust --version
```

**Done when:** Locust 2.8.x runs.

---

## Phase 4 - Configure and deploy Online Boutique

### 4a. Edit `global_config.json`

Path: `TopFull_master/online_boutique_scripts/src/global_config.json`

Replace example paths like `/home/master_artifact/...` with real paths, e.g. `/home/azureuser/TopFull/TopFull_master/online_boutique_scripts/src/...`

Set:
- `proxy_url`: `http://MASTER_PRIVATE_IP:8090`
- `frontend_url`: `MASTER_PRIVATE_IP:30440`
- `locust_url`: `LOADGEN_PRIVATE_IP`
- `record_path`, `checkpoint_path`, etc. to real directories under `src/logs/`

---

### 4b-4d. Other config files

See README checklist: hardcode path to `global_config.json` in four Python/Go files; set worker count in `resource_collector.py`; set master IP in Locust shell scripts and `locust_online_boutique.py` line 293.

---

### 4e-4f. Deploy and scale

**On master:**
```bash
# Confirm sidecar injection is active before deploying
kubectl get namespace default --show-labels   # must show istio-injection=enabled

cd ~/TopFull
kubectl apply -f TopFull_master/online_boutique_scripts/deployments/online_boutique_original_custom.yaml
kubectl apply -f TopFull_master/online_boutique_scripts/deployments/metric-server-latest.yaml
cd TopFull_master/online_boutique_scripts/src
source ~/TopFull/venv/bin/activate
python instance_scaling.py
kubectl get pods
```

**Done when:** All Boutique pods show `2/2` containers (app + Envoy sidecar injected by Istio). If pods show `1/1`, the sidecar was not injected — delete the deployment and re-apply, or manually inject: `istioctl kube-inject -f <yaml> | kubectl apply -f -`.

---

### 4g. Smoke test

From loadgen or your PC (if port open):
```bash
curl -I http://MASTER_IP:30440
```

**Done when:** HTTP 200 and HTML response.

---

## Phase 5 - TopFull baseline experiment

**Order matters.** Use `tmux` on each machine so processes survive disconnect.

| Order | Machine | Command |
|-------|---------|---------|
| 1 | Master | `go run proxy_online_boutique.go` in `src/proxy` |
| 2 | Master | `python deploy_rl.py` in `src` (needs proxy) |
| 3 | Loadgen | `./online_boutique_create.sh` and `create2.sh` |
| 4 | Master | `python metric_collector.py` in `src` |

**Done when:** `logs/` has CSVs with goodput/latency; save a copy as **baseline**.

---

## Phase 6 - RetryGuard

1. Implement controller (Algorithm 1): poll per-service rejection rate every ~30s from TopFull's `metric_collector.py` / `overload_detection.py` logs; if above ~20% for N consecutive intervals, disable retries; re-enable when below threshold for N intervals.
2. Integration point (decided — matches paper Sec. 4): RetryGuard runs as a Python process on the master node. It toggles retries per service by patching Istio VirtualService resources via `kubernetes.client.CustomObjectsApi`. Disabling = `retries.attempts: 0`; re-enabling = `retries.attempts: 3`.
3. Before running the experiment, create a VirtualService resource for each Online Boutique microservice with the default retry policy (`attempts: 3, retryOn: "5xx,reset,connect-failure"`). Verify manual toggle works: `kubectl patch virtualservice <svc> --type merge -p '{"spec":{"http":[{"retries":{"attempts":0}}]}}'`.
4. Run the **same** Locust scenario as Phase 5 with RetryGuard enabled. Run each scenario **multiple times** (Locust is non-deterministic); compare using averages/medians across runs.
5. Save results as **retryguard run** (separate folder from baseline, e.g. `run_topfull_retryguard`).

---

## Phase 7 - Evaluation

Compare **Phase 5 baseline** vs **Phase 6 RetryGuard** on: goodput, P95 latency, rejection %, retries/request, CPU/memory, pod replica count. Write report per mentor expectations ([MENTOR-COORDINATION.md](MENTOR-COORDINATION.md)); reference RetryGuard paper Table 1 style metrics.

---

## Quick troubleshooting

| Problem | Check |
|---------|--------|
| Nodes NotReady | Calico installed? `kubectl get pods -n kube-system` |
| Pods pending | `kubectl describe pod` -> resources? image pull? |
| `deploy_rl.py` errors | Is proxy running? Is `global_config.json` path correct? |
| Locust can't connect | `--host` IP/port, NSG allows 30440/8090, proxy running |
| No metrics CSVs | Was load running? Did `metric_collector.py` run during load? |
