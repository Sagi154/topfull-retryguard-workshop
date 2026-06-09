# Project 1: TopFull + RetryGuard on Cloud VMs

TAU Deepness Lab Workshop — Retries for Cloud Microservices

> **How to use this workplan:** Before Phase 1, complete [PREREQUISITES.md](PREREQUISITES.md) and [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md). Each phase below has **Why**, **How**, and **Done when**. For Azure steps, full commands, and troubleshooting, use [SETUP-GUIDE.md](SETUP-GUIDE.md). Out of scope: DAGOR, DiffTry, extra overload baselines unless mentors say otherwise.
>
> **Interactive version:** [canvases/topfull-retryguard-workplan.canvas.tsx](canvases/topfull-retryguard-workplan.canvas.tsx) in Cursor (see [README — Viewing the workplan](README.md#viewing-the-workplan)).

| Cloud VMs | Timeline | Phases | Est. cloud cost |
|-----------|----------|--------|-----------------|
| 4–7 | ~8 days | 7 (0–7) | $5–15/day |

---

## VM architecture

| Role | Count | Min specs | Purpose |
|------|-------|-----------|---------|
| Master Node | 1 | 8+ vCPU, 16 GB RAM | K8s control plane, Istio control plane, TopFull proxy, RL, metrics |
| Worker Nodes | 2–5 | 8+ vCPU, 16 GB RAM | Online Boutique pods, cAdvisor |
| Load Generator | 1 | 8+ vCPU, 16 GB RAM | Locust traffic only |

---

## Configuration reference

| File (line) | What to change | Notes |
|-------------|----------------|-------|
| `global_config.json` | All paths, IPs, ports | First file to edit |
| `proxy_online_boutique.go:28` | Config path | Absolute path to `global_config.json` |
| `deploy_rl.py:13` | Config path | Absolute path to `global_config.json` |
| `metric_collector.py:9` | Config path | Absolute path to `global_config.json` |
| `overload_detection.py:10` | Config path | Absolute path to `global_config.json` |
| `resource_collector.py:456` | cAdvisor pod count | Must match # of worker nodes |
| `online_boutique_create.sh` | `--host=http://IP:30440` | Master node IP |
| `locust_online_boutique.py:293` | Proxy address | `http://MASTER_IP:8090` |

---

## Phase-by-phase workplan

Before Phase 1: [PREREQUISITES.md](PREREQUISITES.md) and [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md). Commands and troubleshooting: [SETUP-GUIDE.md](SETUP-GUIDE.md).

---

### Phase 0 — Preparation & Accounts (Day 1)

#### 0a. Choose cloud provider and get credits

**Why:** TopFull runs on real Linux VMs in the cloud. You cannot run this stack on Windows alone.

**How:**

1. Ask mentors if the lab provides Azure/AWS/GCP credits or a shared subscription ([MENTOR-COORDINATION.md](MENTOR-COORDINATION.md)).
2. If self-funded: create a cloud account. Azure matches the TopFull paper; AWS/GCP also work.
3. Plan ~$5–15/day while 4 VMs run. Deallocate/stop VMs when you are not working.

**Done when:** You can log into a cloud portal and create a virtual machine.

---

#### 0b. Clone TopFull repo on your PC and read key files

**Why:** You need to understand paths and run order before paying for VMs.

**How:**

1. Run: `git clone https://github.com/kaist-ina/TopFull.git`
2. Open `global_config.json` (all IPs and paths you will edit later).
3. Skim `deploy_rl.py`, `proxy_online_boutique.go`, and `online_boutique_original_custom.yaml`.
4. Read `RetryGuard.pdf` Sec. 4 and 6.2 in the Workshop folder.
5. Note experiment order: proxy first, then `deploy_rl`, then load, then `metric_collector`.

**Done when:** You know where configuration lives and what runs on the master vs loadgen.

---

#### 0c. Coordinate with mentors (RetryGuard)

**Why:** You implement RetryGuard from the paper. Mentors confirm credits, provider, and where retries are toggled.

**How:**

1. Complete [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md) in the Workshop folder (checklist + message template).
2. You do not need RetryGuard source code from the lab.
3. Read RetryGuard Sec. 4 (controller) and Sec. 6.2 (~20% threshold, ~30s interval).

**Done when:** Mentor checklist done and Istio integration approach approved (RetryGuard toggles Istio VirtualService retry policies per service, matching the paper's Sec. 4 design).

---

#### 0d. Generate SSH key on your Windows PC

**Why:** You will SSH from Windows into every Linux VM.

**How:**

1. In PowerShell: `ssh-keygen -t ed25519 -C workshop-topfull`
2. Keep the private key at `C:\Users\YOU\.ssh\id_ed25519`
3. When creating VMs, paste the contents of `id_ed25519.pub` as the SSH public key.

**Done when:** You have a `.pub` file ready to paste into VM creation.

---

### Phase 1 — Provision Cloud VMs (Day 1–2)

#### 1a. Create 4–7 Ubuntu 20.04 VMs

**Why:** Kubernetes needs a dedicated master (control plane + TopFull), workers (app pods), and a separate load generator.

**How:**

1. Create 1 VM named e.g. `topfull-master` (master role).
2. Create 2–5 VMs named e.g. `topfull-worker-1..N` (run microservice pods). Paper used 5 workers; 2 is OK to start.
3. Create 1 VM named e.g. `topfull-loadgen` (runs Locust only).
4. Image: Ubuntu Server 20.04 LTS (not 22.04). Size: at least 8 vCPU and 16 GB RAM each.
5. Azure example: Resource group + VNet, then Create VM > Standard_D8ds_v5, SSH key auth, same subnet.
6. AWS example: VPC + subnet, EC2 m5.2xlarge, Ubuntu 20.04 AMI, same security group.
7. Put all VMs in the same region and virtual network so private IPs can talk.

**Done when:** You have 4+ running VMs, all Ubuntu 20.04, tagged by role (master / worker / loadgen).

---

#### 1b. Configure networking (firewall / security group)

**Why:** Pods and Locust must reach the master; you must SSH in; nodes must join the cluster.

**How:**

1. Allow SSH (port 22) to each VM from your IP (or via bastion).
2. Allow TCP 6443 on master (Kubernetes API).
3. Allow TCP 30440 on master (Online Boutique NodePort).
4. Allow TCP 8090 on master (TopFull Go proxy).
5. Allow TCP 15010, 15012, 15014, 15017 on master (Istio control plane).
6. Allow all traffic between VMs inside the same subnet (pod network + node communication).
7. Azure: edit Network Security Group inbound rules. AWS: edit Security Group.

**Done when:** From master you can ping worker private IPs; from loadgen you can ping master private IP.

---

#### 1c. SSH into each VM and record IPs

**Why:** You will paste these IPs into `global_config.json` and Locust scripts.

**How:**

1. `ssh azureuser@MASTER_PUBLIC_IP` (or `ubuntu@` on AWS).
2. Run: `ip addr show` and note the private IP (e.g. 10.0.1.4).
3. Write down `MASTER_PRIVATE_IP`, `LOADGEN_PRIVATE_IP`, and each `WORKER_PRIVATE_IP`.
4. Keep a text file on your PC with these values.

**Done when:** You can SSH to every VM and have a written list of private (and public) IPs.

---

#### 1d. Clone TopFull on master and load-gen VMs

**Why:** Only master and loadgen need the git repo; workers only run containers pulled by Kubernetes.

**How:**

1. SSH to master: `sudo apt-get update && sudo apt-get install -y git`
2. `git clone https://github.com/kaist-ina/TopFull.git`
3. Repeat the same clone on the loadgen VM.
4. Workers do not need the repo unless you debug there.

**Done when:** `ls ~/TopFull/TopFull_master` works on master and loadgen.

---

### Phase 2 — Kubernetes Cluster Setup (Day 2–3)

#### 2a. Install Docker + cri-docker on ALL nodes

**Why:** This TopFull setup uses Kubernetes 1.26 with cri-dockerd, not plain containerd.

**How:**

1. On every VM (master + all workers): `sudo swapoff -a`
2. Install Docker (get.docker.com script or TopFull README).
3. Install cri-dockerd binary + systemd units (TopFull README section 1).
4. Set `/etc/docker/daemon.json` cgroup driver to systemd; restart docker and cri-docker.
5. Apply br_netfilter and sysctl settings from README.

**Done when:** `docker` and `cri-docker` services are active on every node; `docker info` shows cgroup systemd.

---

#### 2b. Install kubeadm, kubelet, kubectl v1.26 on ALL nodes

**Why:** All nodes need kubelet; only master uses kubectl for control initially.

**How:**

1. Follow TopFull README: add Kubernetes 1.26 apt repo on each node.
2. `sudo apt-get install -y kubelet kubeadm kubectl`
3. `sudo apt-mark hold kubelet kubeadm kubectl`
4. Verify: `kubeadm version`

**Done when:** `kubeadm` and `kubectl` are installed on all nodes.

---

#### 2c. Initialize Kubernetes on master only

**Why:** Creates the control plane that workers will join.

**How:**

1. On master only, run `kubeadm init` with pod-network-cidr `192.168.0.0/16` and cri-docker socket (see README).
2. Copy `admin.conf` to `~/.kube/config` and chown to your user.
3. Run: `kubectl get nodes` (master may show NotReady until CNI).

**Done when:** `kubectl get nodes` shows the master node.

---

#### 2d. Install Calico CNI on master

**Why:** Pods need a network plugin before they can get IPs and run.

**How:**

1. `cd ~/TopFull/TopFull_master`
2. `kubectl apply -f calico.yaml`
3. Watch: `kubectl get pods -n kube-system` until Calico is Running.

**Done when:** Master node status is Ready.

---

#### 2e. Join worker nodes to the cluster

**Why:** Workers run the Online Boutique microservice pods.

**How:**

1. On master: `sudo kubeadm token create --print-join-command`
2. On each worker: run that command and append `--cri-socket unix:///var/run/cri-dockerd.sock`
3. On master: `kubectl get nodes` until all workers show Ready.

**Done when:** `kubectl get nodes` lists master + all workers as Ready.

---

#### 2f. Deploy cAdvisor for resource monitoring

**Why:** TopFull collects per-pod CPU/memory via cAdvisor.

**How:**

1. `cd ~/TopFull/TopFull_master/online_boutique_scripts/cadvisor`
2. `kubectl kustomize deploy/kubernetes/base | kubectl apply -f -`
3. `kubectl get pods -A | grep -i cadvisor`

**Done when:** cAdvisor pods are Running (typically one per worker).

---

#### 2g. Verify cluster health

**Why:** Catch networking or CRI issues before deploying the app.

**How:**

1. `kubectl get nodes`
2. `kubectl get po --all-namespaces -o wide`
3. Fix any CrashLoopBackOff before continuing.

**Done when:** All nodes Ready; system pods Running; screenshot saved as baseline.

---

#### 2h. Install Istio service mesh

**Why:** RetryGuard controls retries by toggling Istio VirtualService retry policies per service, matching the paper's architecture (Sec. 4). Istio injects Envoy sidecar proxies into each pod, giving mesh-level retry control over inter-service gRPC calls.

**How:**

1. On master: download `istioctl` (use Istio 1.17.x for K8s 1.26 compatibility).
2. `curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.17.8 sh -`
3. Add `istio-1.17.8/bin` to PATH.
4. `istioctl install --set profile=minimal -y` (minimal profile avoids unnecessary components).
5. Label the namespace for automatic sidecar injection: `kubectl label namespace default istio-injection=enabled`
6. Verify: `kubectl get pods -n istio-system` — `istiod` should be Running.
7. Confirm Istio does not conflict with Calico: `kubectl get pods --all-namespaces` — no CrashLoopBackOff.

**Done when:** `istiod` is Running in `istio-system`; sidecar injection is enabled on the default namespace.

---

### Phase 3 — Install Dependencies (Day 3–4)

#### 3a. Install Python dependencies on master

**Why:** `deploy_rl.py`, `metric_collector.py`, and `instance_scaling.py` need Ray, TensorFlow, kubernetes client, etc.

**How:**

1. `sudo apt-get install -y python3 python3-pip python3-venv`
2. `cd ~/TopFull && python3 -m venv venv && source venv/bin/activate`
3. `pip install -r TopFull_master/requirements.txt`
4. If python-apt or systemd-python fail, skip them (not needed in venv).
5. Test: `python -c "import ray; import kubernetes"`

**Done when:** Virtualenv activates and key imports work on master.

---

#### 3b. Install Go 1.13.8 on master

**Why:** The TopFull entry proxy is a Go program: `proxy_online_boutique.go`.

**How:**

1. `wget https://go.dev/dl/go1.13.8.linux-amd64.tar.gz`
2. `sudo tar -C /usr/local -xzf go1.13.8.linux-amd64.tar.gz`
3. Add `/usr/local/go/bin` to PATH in `~/.bashrc`
4. Set GOPATH to `~/TopFull/TopFull_master/go`
5. `go version` should show go1.13.8

**Done when:** `go version` works on master.

---

#### 3c. Install Locust on load-gen VM

**Why:** Load is generated by Locust scripts in `TopFull_loadgen/`, not on the master.

**How:**

1. On loadgen: `python3 -m venv venv && source venv/bin/activate`
2. `pip install -r TopFull_loadgen/requirements.txt`
3. `locust --version` (expect 2.8.x)

**Done when:** `locust` command runs on the loadgen VM.

---

### Phase 4 — Configure and Deploy Online Boutique (Day 4–5)

#### 4a. Edit global_config.json

**Why:** TopFull scripts read IPs and paths from this file; defaults point to the authors' machines.

**How:**

1. File: `TopFull_master/online_boutique_scripts/src/global_config.json`
2. Replace `/home/master_artifact/...` with your real path, e.g. `/home/azureuser/TopFull/...`
3. Set `proxy_url` to `http://MASTER_PRIVATE_IP:8090`
4. Set `frontend_url` to `MASTER_PRIVATE_IP:30440`
5. Set `locust_url` to `LOADGEN_PRIVATE_IP`

**Done when:** JSON has your IPs and valid absolute paths on the master.

---

#### 4b. Update hardcoded config paths in 4 source files

**Why:** Some files still point to a fixed path for `global_config.json`.

**How:**

1. Edit line with global_config path in: `proxy_online_boutique.go` (line ~28)
2. Same in: `deploy_rl.py` (~13), `metric_collector.py` (~9), `overload_detection.py` (~10)
3. Use the same absolute path you used in `global_config.json`.

**Done when:** All four files reference your `global_config.json` path.

---

#### 4c. Update resource_collector.py for worker count

**Why:** Code assumes a fixed number of cAdvisor pods matching worker nodes.

**How:**

1. Open `resource_collector.py` around line 456.
2. Count how many worker nodes you joined.
3. Adjust the exec command count to match (default in repo expects 5 workers).

**Done when:** `resource_collector` matches your actual worker count.

---

#### 4d. Update load generator scripts with master IP

**Why:** Locust must send HTTP traffic to your master frontend and proxy, not the paper IPs.

**How:**

1. In `TopFull_loadgen/online_boutique_create.sh` and `create2.sh`: change `--host=http://10.x.x.x:30440` to your `MASTER_IP:30440`
2. In `locust_online_boutique.py` line ~293: set proxy to `http://MASTER_IP:8090`

**Done when:** No hardcoded 10.8.x.x IPs remain in loadgen scripts.

---

#### 4e. Deploy Online Boutique and metrics-server (with Istio sidecars)

**Why:** This is the microservice app you will overload and measure. With Istio injection enabled, each pod gets an Envoy sidecar that handles inter-service retries.

**How:**

1. Confirm sidecar injection is enabled: `kubectl get namespace default --show-labels` (should show `istio-injection=enabled`).
2. On master: `kubectl apply -f TopFull_master/online_boutique_scripts/deployments/online_boutique_original_custom.yaml`
3. `kubectl apply -f TopFull_master/online_boutique_scripts/deployments/metric-server-latest.yaml`
4. Wait for pods: `kubectl get pods` (may take minutes to pull images). Each pod should show 2/2 containers (app + Envoy sidecar).
5. If pods show 1/1 instead of 2/2: delete and re-apply the deployment, or manually inject with `istioctl kube-inject -f <yaml> | kubectl apply -f -`.

**Done when:** Boutique pods are Running with 2/2 containers (Envoy sidecar injected).

---

#### 4f. Scale microservice instances

**Why:** `instance_scaling.py` sets replica counts expected by the experiment.

**How:**

1. `cd TopFull_master/online_boutique_scripts/src`
2. `source ~/TopFull/venv/bin/activate`
3. `python instance_scaling.py`
4. `kubectl get pods` again to see scaled replicas.

**Done when:** Pods are Running at expected replica counts.

---

#### 4g. Smoke-test the frontend

**Why:** Confirms networking and deployment before running TopFull controllers.

**How:**

1. From loadgen or PC: `curl -I http://MASTER_IP:30440`
2. You should see HTTP 200 and HTML (Online Boutique page).
3. If connection refused: check NSG/firewall, NodePort, and pod status.

**Done when:** `curl` returns 200 from the boutique frontend.

---

### Phase 5 — TopFull Baseline Experiment (Day 5–6)

#### 5a. Terminal 1 (master): Start Go proxy

**Why:** All user traffic enters through the TopFull rate-limiting proxy on port 8090. With Istio installed, inter-service traffic flows through Envoy sidecars, but the Go proxy still serves as the edge entry point.

**How:**

1. SSH to master; use tmux so it keeps running: `tmux new -s proxy`
2. `cd TopFull_master/online_boutique_scripts/src/proxy`
3. `go run proxy_online_boutique.go`
4. Leave this terminal open. Fix errors about config path before continuing.
5. Verify traffic reaches the app through Istio: `curl http://MASTER_IP:30440` should still return 200 with Envoy sidecars active.

**Done when:** Proxy listens on 8090 without crashing; traffic flows through Go proxy → Istio sidecars → services.

---

#### 5b. Terminal 2 (master): Start RL controller

**Why:** TopFull adaptive overload control (`deploy_rl.py`) adjusts API rate limits.

**How:**

1. New tmux session on master: `tmux new -s toprl`
2. `cd TopFull_master/online_boutique_scripts/src`
3. `source ~/TopFull/venv/bin/activate`
4. `python deploy_rl.py`
5. Requires proxy from step 5a to already be running.

**Done when:** `deploy_rl.py` runs without import/config errors.

---

#### 5c. Load-gen VM: Generate API workloads

**Why:** You need sustained overload to study retries and TopFull behavior.

**How:**

1. SSH to loadgen; `tmux new -s locust`
2. `cd TopFull/TopFull_loadgen`
3. `chmod +x online_boutique_create.sh online_boutique_create2.sh`
4. `./online_boutique_create.sh` then `./online_boutique_create2.sh`
5. Scripts start multiple Locust workers targeting your master `--host` URL.

**Done when:** Locust processes are running and sending requests.

---

#### 5d. Terminal 3 (master): Collect metrics

**Why:** `metric_collector.py` writes goodput, latency, and rejection data to `logs/`.

**How:**

1. On master while load runs: `tmux new -s metrics`
2. `cd TopFull_master/online_boutique_scripts/src`
3. `source venv; python metric_collector.py`
4. Needs load from 5c to be active.

**Done when:** `metric_collector` is running during the load test.

---

#### 5e. Save baseline results

**Why:** Phase 6 compares RetryGuard against this run.

**How:**

1. Check `TopFull_master/online_boutique_scripts/src/logs/` for CSV output.
2. Copy logs to a folder named e.g. `baseline_topfull_no_retryguard`.
3. Note experiment duration, load settings, and date.

**Done when:** You have saved CSVs labeled as the TopFull baseline (default retries).

---

### Phase 6 — Integrate RetryGuard (Day 6–8)

#### 6a. Implement RetryGuard controller (Algorithm 1)

**Why:** RetryGuard turns retries off during prolonged overload to prevent retry storms. The controller monitors overload metrics and toggles Istio VirtualService retry policies per service.

**How:**

1. Write a Python script that polls per-API rejection rate (or latency) from TopFull’s built-in collectors (`metric_collector.py` / `overload_detection.py` logs). Map each API to its primary downstream service (e.g. `getproduct` → productcatalog, `getcart` → cart).
2. If rejection > ~20% for N consecutive ~30s intervals: patch VirtualService to set `retries.attempts: 0` for the overloaded service.
3. If below threshold for N intervals: patch VirtualService to restore `retries.attempts: 3` (or original value).
4. Use the Kubernetes Python client (`kubernetes.client.CustomObjectsApi`) to patch VirtualService CRDs.
5. See RetryGuard paper Algorithm 1 and Sec. 4.3.2.

**Done when:** You have a script that can flip Istio VirtualService retry policies per service based on metrics.

---

#### 6b. Create Istio VirtualService resources for each microservice

**Why:** RetryGuard toggles retries at the Istio mesh level (matching the paper's Sec. 4 architecture). Each service needs a VirtualService with a retry policy that the controller can patch.

**How:**

1. Create VirtualService YAML for each Online Boutique service (frontend, productcatalog, cart, recommendation, etc.).
2. Set default retry policy: `retries: { attempts: 3, retryOn: "5xx,reset,connect-failure" }`.
3. Apply: `kubectl apply -f virtualservices/`
4. Verify: `kubectl get virtualservices` — one per microservice.
5. Test manual toggle: `kubectl patch virtualservice <svc> --type merge -p '{"spec":{"http":[{"retries":{"attempts":0}}]}}'` — confirm retries stop.
6. Revert the manual toggle after testing.

**Done when:** VirtualService resources exist for each microservice with configurable retry policies; manual patch toggle works.

---

#### 6c. Deploy RetryGuard alongside TopFull

**Why:** RetryGuard runs in parallel with TopFull during the second experiment. It watches overload metrics and patches Istio VirtualService retry policies in real time.

**How:**

1. Run RetryGuard as a process on master (same venv as other TopFull scripts).
2. Ensure it has `kubectl` access (uses `~/.kube/config`) and reads the same metrics source you validated.
3. Start proxy + `deploy_rl` + RetryGuard before load.
4. Tail RetryGuard logs to confirm it detects overload and patches VirtualService resources (log should show service name, old attempts, new attempts).

**Done when:** RetryGuard is running, patching VirtualService retry policies, and logging when it enables/disables retries per service.

---

#### 6d. Run experiment: TopFull + RetryGuard

**Why:** This is the primary project measurement.

**How:**

1. Repeat Phase 5 exactly: same Locust scripts, same duration, same replica counts.
2. Only difference: RetryGuard active.
3. Collect metrics to a new folder e.g. `run_topfull_retryguard`.

**Done when:** You have two result sets: baseline vs RetryGuard.

---

### Phase 7 — Evaluation and Report (Day 8–9)

#### 7a. Compare baseline vs TopFull + RetryGuard

**Why:** This is the core project deliverable.

**How:**

1. Plot or table: goodput, p99 latency, rejection %, retries per request.
2. Compare CPU/memory and pod replica counts during overload.
3. Check if RetryGuard reduced retry storms without hurting goodput (paper Table 1).

**Done when:** You have clear numbers showing difference between the two runs.

---

#### 7b. Write evaluation report

**Why:** Document setup, methodology, and findings for the workshop.

**How:**

1. Describe environment: VM sizes, K8s 1.26, Istio service mesh, TopFull + Online Boutique.
2. Explain RetryGuard integration: Istio VirtualService retry policy toggling per service (matching paper Sec. 4).
3. Present Phase 5 baseline vs Phase 6 RetryGuard metrics with graphs/tables.
4. Match report format mentors requested in [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md).

**Done when:** Report is ready for lab review.

---

## Experiment matrix (two runs only)

| Run | Overload control | Retries | When |
|-----|------------------|---------|------|
| Baseline | TopFull | Default (retries on) | Phase 5 |
| Primary | TopFull | RetryGuard | Phase 6 |

---

## Key metrics to collect

### Performance

| Metric | Description |
|--------|-------------|
| **Goodput (rps)** | Successful responses within latency SLO |
| **P99 Latency (ms)** | End-to-end 99th percentile |
| **Rejection Rate (%)** | Failed requests |

### Cost / efficiency

| Metric | Description |
|--------|-------------|
| **Retries per request** | Retry storm size during overload |
| **CPU + Memory** | Pod resource usage |
| **Pod replica count** | Over-scaling from retries |
