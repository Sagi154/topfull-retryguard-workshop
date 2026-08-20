import {
  Stack,
  H1,
  H2,
  H3,
  Text,
  Card,
  CardHeader,
  CardBody,
  Table,
  Pill,
  Stat,
  Callout,
  Divider,
  Grid,
  TodoList,
  type TodoItem,
  type TodoStatus,
} from "cursor/canvas";

type StepGuide = {
  id: string;
  title: string;
  status: TodoStatus;
  why: string;
  how: readonly string[];
  doneWhen: string;
};

function PhaseSteps({ guides }: { guides: readonly StepGuide[] }) {
  const todos: TodoItem[] = guides.map((g) => ({
    id: g.id,
    content: g.title,
    status: g.status,
  }));

  return (
    <Stack gap={12}>
      <TodoList todos={todos} />
      <Text tone="secondary" size="small">
        Open one step at a time below. Before Phase 1: PREREQUISITES.md and
        MENTOR-COORDINATION.md. Commands: SETUP-GUIDE.md.
      </Text>
      {guides.map((g) => (
        <Card key={g.id} collapsible defaultOpen={false}>
          <CardHeader trailing={<Pill tone="neutral" size="sm">{g.id}</Pill>}>
            {g.title}
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                <Text weight="semibold" as="span">
                  Why:{" "}
                </Text>
                {g.why}
              </Text>
              <Text weight="semibold">How:</Text>
              {g.how.map((line, i) => (
                <Text key={i} size="small">
                  {i + 1}. {line}
                </Text>
              ))}
              <Callout tone="success" title="Done when">
                {g.doneWhen}
              </Callout>
            </Stack>
          </CardBody>
        </Card>
      ))}
    </Stack>
  );
}

const phases: {
  id: string;
  title: string;
  duration: string;
  guides: StepGuide[];
}[] = [
  {
    id: "phase0",
    title: "Phase 0 - Preparation & Accounts",
    duration: "Day 1",
    guides: [
      {
        id: "0a",
        title: "Choose cloud provider and get credits",
        status: "pending",
        why: "TopFull runs on real Linux VMs in the cloud. You cannot run this stack on Windows alone.",
        how: [
          "Ask mentors if the lab provides Azure/AWS/GCP credits or a shared subscription (MENTOR-COORDINATION.md).",
          "If self-funded: create a cloud account. Azure matches the TopFull paper; AWS/GCP also work.",
          "Plan ~$5-15/day while 4 VMs run. Deallocate/stop VMs when you are not working.",
        ],
        doneWhen: "You can log into a cloud portal and create a virtual machine.",
      },
      {
        id: "0b",
        title: "Clone TopFull repo on your PC and read key files",
        status: "pending",
        why: "You need to understand paths and run order before paying for VMs.",
        how: [
          "Run: git clone https://github.com/kaist-ina/TopFull.git",
          "Open global_config.json (all IPs and paths you will edit later).",
          "Skim deploy_rl.py, proxy_online_boutique.go, and online_boutique_original_custom.yaml.",
          "Read RetryGuard.pdf Sec. 4 and 6.2 in the Workshop folder.",
          "Note experiment order: proxy first, then deploy_rl, then load, then metric_collector.",
        ],
        doneWhen: "You know where configuration lives and what runs on the master vs loadgen.",
      },
      {
        id: "0c",
        title: "Coordinate with mentors (RetryGuard)",
        status: "pending",
        why: "You implement RetryGuard from the paper. Mentors confirm credits, provider, and where retries are toggled.",
        how: [
          "Complete MENTOR-COORDINATION.md in the Workshop folder (checklist + message template).",
          "You do not need RetryGuard source code from the lab.",
          "Read RetryGuard Sec. 4 (controller) and Sec. 6.2 (~20% threshold, ~30s interval).",
        ],
        doneWhen:
          "Mentor checklist done and retry integration point agreed (proxy, Istio, or app config).",
      },
      {
        id: "0d",
        title: "Generate SSH key on your Windows PC",
        status: "pending",
        why: "You will SSH from Windows into every Linux VM.",
        how: [
          "In PowerShell: ssh-keygen -t ed25519 -C workshop-topfull",
          "Keep the private key at C:\\Users\\YOU\\.ssh\\id_ed25519",
          "When creating VMs, paste the contents of id_ed25519.pub as the SSH public key.",
        ],
        doneWhen: "You have a .pub file ready to paste into VM creation.",
      },
    ],
  },
  {
    id: "phase1",
    title: "Phase 1 - Provision Cloud VMs",
    duration: "Day 1-2",
    guides: [
      {
        id: "1a",
        title: "Create 4-7 Ubuntu 20.04 VMs",
        status: "pending",
        why: "Kubernetes needs a dedicated master (control plane + TopFull), workers (app pods), and a separate load generator.",
        how: [
          "Create 1 VM named e.g. topfull-master (master role).",
          "Create 2-5 VMs named e.g. topfull-worker-1..N (run microservice pods). Paper used 5 workers; 2 is OK to start.",
          "Create 1 VM named e.g. topfull-loadgen (runs Locust only).",
          "Image: Ubuntu Server 20.04 LTS (not 22.04). Size: at least 8 vCPU and 16 GB RAM each.",
          "Azure example: Resource group + VNet, then Create VM > Standard_D8ds_v5, SSH key auth, same subnet.",
          "AWS example: VPC + subnet, EC2 m5.2xlarge, Ubuntu 20.04 AMI, same security group.",
          "Put all VMs in the same region and virtual network so private IPs can talk.",
        ],
        doneWhen:
          "You have 4+ running VMs, all Ubuntu 20.04, tagged by role (master / worker / loadgen).",
      },
      {
        id: "1b",
        title: "Configure networking (firewall / security group)",
        status: "pending",
        why: "Pods and Locust must reach the master; you must SSH in; nodes must join the cluster.",
        how: [
          "Allow SSH (port 22) to each VM from your IP (or via bastion).",
          "Allow TCP 6443 on master (Kubernetes API).",
          "Allow TCP 30440 on master (Online Boutique NodePort).",
          "Allow TCP 8090 on master (TopFull Go proxy).",
          "Allow all traffic between VMs inside the same subnet (pod network + node communication).",
          "Azure: edit Network Security Group inbound rules. AWS: edit Security Group.",
        ],
        doneWhen:
          "From master you can ping worker private IPs; from loadgen you can ping master private IP.",
      },
      {
        id: "1c",
        title: "SSH into each VM and record IPs",
        status: "pending",
        why: "You will paste these IPs into global_config.json and Locust scripts.",
        how: [
          "ssh azureuser@MASTER_PUBLIC_IP (or ubuntu@ on AWS).",
          "Run: ip addr show and note the private IP (e.g. 10.0.1.4).",
          "Write down MASTER_PRIVATE_IP, LOADGEN_PRIVATE_IP, and each WORKER_PRIVATE_IP.",
          "Keep a text file on your PC with these values.",
        ],
        doneWhen:
          "You can SSH to every VM and have a written list of private (and public) IPs.",
      },
      {
        id: "1d",
        title: "Clone TopFull on master and load-gen VMs",
        status: "pending",
        why: "Only master and loadgen need the git repo; workers only run containers pulled by Kubernetes.",
        how: [
          "SSH to master: sudo apt-get update && sudo apt-get install -y git",
          "git clone https://github.com/kaist-ina/TopFull.git",
          "Repeat the same clone on the loadgen VM.",
          "Workers do not need the repo unless you debug there.",
        ],
        doneWhen: "ls ~/TopFull/TopFull_master works on master and loadgen.",
      },
    ],
  },
  {
    id: "phase2",
    title: "Phase 2 - Kubernetes Cluster Setup",
    duration: "Day 2-3",
    guides: [
      {
        id: "2a",
        title: "Install Docker + cri-docker on ALL nodes",
        status: "pending",
        why: "This TopFull setup uses Kubernetes 1.26 with cri-dockerd, not plain containerd.",
        how: [
          "On every VM (master + all workers): sudo swapoff -a",
          "Install Docker (get.docker.com script or TopFull README).",
          "Install cri-dockerd binary + systemd units (TopFull README section 1).",
          "Set /etc/docker/daemon.json cgroup driver to systemd; restart docker and cri-docker.",
          "Apply br_netfilter and sysctl settings from README.",
        ],
        doneWhen:
          "docker and cri-docker services are active on every node; docker info shows cgroup systemd.",
      },
      {
        id: "2b",
        title: "Install kubeadm, kubelet, kubectl v1.26 on ALL nodes",
        status: "pending",
        why: "All nodes need kubelet; only master uses kubectl for control initially.",
        how: [
          "Follow TopFull README: add Kubernetes 1.26 apt repo on each node.",
          "sudo apt-get install -y kubelet kubeadm kubectl",
          "sudo apt-mark hold kubelet kubeadm kubectl",
          "Verify: kubeadm version",
        ],
        doneWhen: "kubeadm and kubectl are installed on all nodes.",
      },
      {
        id: "2c",
        title: "Initialize Kubernetes on master only",
        status: "pending",
        why: "Creates the control plane that workers will join.",
        how: [
          "On master only, run kubeadm init with pod-network-cidr 192.168.0.0/16 and cri-docker socket (see README).",
          "Copy admin.conf to ~/.kube/config and chown to your user.",
          "Run: kubectl get nodes (master may show NotReady until CNI).",
        ],
        doneWhen: "kubectl get nodes shows the master node.",
      },
      {
        id: "2d",
        title: "Install Calico CNI on master",
        status: "pending",
        why: "Pods need a network plugin before they can get IPs and run.",
        how: [
          "cd ~/TopFull/TopFull_master",
          "kubectl apply -f calico.yaml",
          "Watch: kubectl get pods -n kube-system until Calico is Running.",
        ],
        doneWhen: "Master node status is Ready.",
      },
      {
        id: "2e",
        title: "Join worker nodes to the cluster",
        status: "pending",
        why: "Workers run the Online Boutique microservice pods.",
        how: [
          "On master: sudo kubeadm token create --print-join-command",
          "On each worker: run that command and append --cri-socket unix:///var/run/cri-dockerd.sock",
          "On master: kubectl get nodes until all workers show Ready.",
        ],
        doneWhen: "kubectl get nodes lists master + all workers as Ready.",
      },
      {
        id: "2f",
        title: "Deploy cAdvisor for resource monitoring",
        status: "pending",
        why: "TopFull collects per-pod CPU/memory via cAdvisor.",
        how: [
          "cd ~/TopFull/TopFull_master/online_boutique_scripts/cadvisor",
          "kubectl kustomize deploy/kubernetes/base | kubectl apply -f -",
          "kubectl get pods -A | grep -i cadvisor",
        ],
        doneWhen: "cAdvisor pods are Running (typically one per worker).",
      },
      {
        id: "2g",
        title: "Verify cluster health",
        status: "pending",
        why: "Catch networking or CRI issues before deploying the app.",
        how: [
          "kubectl get nodes",
          "kubectl get po --all-namespaces -o wide",
          "Fix any CrashLoopBackOff before continuing.",
        ],
        doneWhen: "All nodes Ready; system pods Running; screenshot saved as baseline.",
      },
    ],
  },
  {
    id: "phase3",
    title: "Phase 3 - Install Dependencies",
    duration: "Day 3-4",
    guides: [
      {
        id: "3a",
        title: "Install Python dependencies on master",
        status: "pending",
        why: "deploy_rl.py, metric_collector.py, and instance_scaling.py need Ray, TensorFlow, kubernetes client, etc.",
        how: [
          "sudo apt-get install -y python3 python3-pip python3-venv",
          "cd ~/TopFull && python3 -m venv venv && source venv/bin/activate",
          "pip install -r TopFull_master/requirements.txt",
          "If python-apt or systemd-python fail, skip them (not needed in venv).",
          "Test: python -c \"import ray; import kubernetes\"",
        ],
        doneWhen: "Virtualenv activates and key imports work on master.",
      },
      {
        id: "3b",
        title: "Install Go 1.13.8 on master",
        status: "pending",
        why: "The TopFull entry proxy is a Go program: proxy_online_boutique.go.",
        how: [
          "wget https://go.dev/dl/go1.13.8.linux-amd64.tar.gz",
          "sudo tar -C /usr/local -xzf go1.13.8.linux-amd64.tar.gz",
          "Add /usr/local/go/bin to PATH in ~/.bashrc",
          "Set GOPATH to ~/TopFull/TopFull_master/go",
          "go version should show go1.13.8",
        ],
        doneWhen: "go version works on master.",
      },
      {
        id: "3c",
        title: "Install Locust on load-gen VM",
        status: "pending",
        why: "Load is generated by Locust scripts in TopFull_loadgen/, not on the master.",
        how: [
          "On loadgen: python3 -m venv venv && source venv/bin/activate",
          "pip install -r TopFull_loadgen/requirements.txt",
          "locust --version (expect 2.8.x)",
        ],
        doneWhen: "locust command runs on the loadgen VM.",
      },
    ],
  },
  {
    id: "phase4",
    title: "Phase 4 - Configure and Deploy Online Boutique",
    duration: "Day 4-5",
    guides: [
      {
        id: "4a",
        title: "Edit global_config.json",
        status: "pending",
        why: "TopFull scripts read IPs and paths from this file; defaults point to the authors machines.",
        how: [
          "File: TopFull_master/online_boutique_scripts/src/global_config.json",
          "Replace /home/master_artifact/... with your real path, e.g. /home/azureuser/TopFull/...",
          "Set proxy_url to http://MASTER_PRIVATE_IP:8090",
          "Set frontend_url to MASTER_PRIVATE_IP:30440",
          "Set locust_url to LOADGEN_PRIVATE_IP",
        ],
        doneWhen: "JSON has your IPs and valid absolute paths on the master.",
      },
      {
        id: "4b",
        title: "Update hardcoded config paths in 4 source files",
        status: "pending",
        why: "Some files still point to a fixed path for global_config.json.",
        how: [
          "Edit line with global_config path in: proxy_online_boutique.go (line ~28)",
          "Same in: deploy_rl.py (~13), metric_collector.py (~9), overload_detection.py (~10)",
          "Use the same absolute path you used in global_config.json.",
        ],
        doneWhen: "All four files reference your global_config.json path.",
      },
      {
        id: "4c",
        title: "Update resource_collector.py for worker count",
        status: "pending",
        why: "Code assumes a fixed number of cAdvisor pods matching worker nodes.",
        how: [
          "Open resource_collector.py around line 456.",
          "Count how many worker nodes you joined.",
          "Adjust the exec command count to match (default in repo expects 5 workers).",
        ],
        doneWhen: "resource_collector matches your actual worker count.",
      },
      {
        id: "4d",
        title: "Update load generator scripts with master IP",
        status: "pending",
        why: "Locust must send HTTP traffic to your master frontend and proxy, not the paper IPs.",
        how: [
          "In TopFull_loadgen/online_boutique_create.sh and create2.sh: change --host=http://10.x.x.x:30440 to your MASTER_IP:30440",
          "In locust_online_boutique.py line ~293: set proxy to http://MASTER_IP:8090",
        ],
        doneWhen: "No hardcoded 10.8.x.x IPs remain in loadgen scripts.",
      },
      {
        id: "4e",
        title: "Deploy Online Boutique and metrics-server",
        status: "pending",
        why: "This is the microservice app you will overload and measure.",
        how: [
          "On master: kubectl apply -f TopFull_master/online_boutique_scripts/deployments/online_boutique_original_custom.yaml",
          "kubectl apply -f TopFull_master/online_boutique_scripts/deployments/metric-server-latest.yaml",
          "Wait for pods: kubectl get pods (may take minutes to pull images).",
        ],
        doneWhen: "Boutique-related pods are Running or completing startup.",
      },
      {
        id: "4f",
        title: "Scale microservice instances",
        status: "pending",
        why: "instance_scaling.py sets replica counts expected by the experiment.",
        how: [
          "cd TopFull_master/online_boutique_scripts/src",
          "source ~/TopFull/venv/bin/activate",
          "python instance_scaling.py",
          "kubectl get pods again to see scaled replicas.",
        ],
        doneWhen: "Pods are Running at expected replica counts.",
      },
      {
        id: "4g",
        title: "Smoke-test the frontend",
        status: "pending",
        why: "Confirms networking and deployment before running TopFull controllers.",
        how: [
          "From loadgen or PC: curl -I http://MASTER_IP:30440",
          "You should see HTTP 200 and HTML (Online Boutique page).",
          "If connection refused: check NSG/firewall, NodePort, and pod status.",
        ],
        doneWhen: "curl returns 200 from the boutique frontend.",
      },
    ],
  },
  {
    id: "phase5",
    title: "Phase 5 - TopFull Baseline Experiment",
    duration: "Day 5-6",
    guides: [
      {
        id: "5a",
        title: "Terminal 1 (master): Start Go proxy",
        status: "pending",
        why: "All user traffic enters through the TopFull rate-limiting proxy on port 8090.",
        how: [
          "SSH to master; use tmux so it keeps running: tmux new -s proxy",
          "cd TopFull_master/online_boutique_scripts/src/proxy",
          "go run proxy_online_boutique.go",
          "Leave this terminal open. Fix errors about config path before continuing.",
        ],
        doneWhen: "Proxy listens on 8090 without crashing.",
      },
      {
        id: "5b",
        title: "Terminal 2 (master): Start RL controller",
        status: "pending",
        why: "TopFull adaptive overload control (deploy_rl.py) adjusts API rate limits.",
        how: [
          "New tmux session on master: tmux new -s toprl",
          "cd TopFull_master/online_boutique_scripts/src",
          "source ~/TopFull/venv/bin/activate",
          "python deploy_rl.py",
          "Requires proxy from step 5a to already be running.",
        ],
        doneWhen: "deploy_rl.py runs without import/config errors.",
      },
      {
        id: "5c",
        title: "Load-gen VM: Generate API workloads",
        status: "pending",
        why: "You need sustained overload to study retries and TopFull behavior.",
        how: [
          "SSH to loadgen; tmux new -s locust",
          "cd TopFull/TopFull_loadgen",
          "chmod +x online_boutique_create.sh online_boutique_create2.sh",
          "./online_boutique_create.sh then ./online_boutique_create2.sh",
          "Scripts start multiple Locust workers targeting your master --host URL.",
        ],
        doneWhen: "Locust processes are running and sending requests.",
      },
      {
        id: "5d",
        title: "Terminal 3 (master): Collect metrics",
        status: "pending",
        why: "metric_collector.py writes goodput, latency, and rejection data to logs/.",
        how: [
          "On master while load runs: tmux new -s metrics",
          "cd TopFull_master/online_boutique_scripts/src",
          "source venv; python metric_collector.py",
          "Needs load from 5c to be active.",
        ],
        doneWhen: "metric_collector is running during the load test.",
      },
      {
        id: "5e",
        title: "Save baseline results",
        status: "pending",
        why: "Phase 6 compares RetryGuard against this run.",
        how: [
          "Check TopFull_master/online_boutique_scripts/src/logs/ for CSV output.",
          "Copy logs to a folder named e.g. baseline_topfull_no_retryguard.",
          "Note experiment duration, load settings, and date.",
        ],
        doneWhen: "You have saved CSVs labeled as the TopFull baseline (default retries).",
      },
    ],
  },
  {
    id: "phase6",
    title: "Phase 6 - Integrate RetryGuard",
    duration: "Day 6-8",
    guides: [
      {
        id: "6a",
        title: "Implement RetryGuard controller (Algorithm 1)",
        status: "pending",
        why: "RetryGuard turns retries off during prolonged overload to prevent retry storms.",
        how: [
          "Poll rejection rate (or latency) per service from Prometheus/metrics or TopFull logs.",
          "If rejection > ~20% for N consecutive ~30s intervals: disable retries.",
          "If below threshold for N intervals: re-enable retries.",
          "See RetryGuard paper Algorithm 1 and Sec. 4.3.2.",
        ],
        doneWhen: "You have a script that can flip retry policy based on metrics.",
      },
      {
        id: "6b",
        title: "Choose where retries are controlled",
        status: "pending",
        why: "Retries must be toggled in the actual request path, not only in metrics.",
        how: [
          "Option A: extend TopFull Go proxy to skip retries when RetryGuard says OFF.",
          "Option B: Istio VirtualService retry policy (if you add Istio).",
          "Option C: modify Online Boutique client retry settings.",
          "Confirm preferred option with mentors (see MENTOR-COORDINATION.md).",
        ],
        doneWhen: "You know exactly which config/file changes when RetryGuard disables retries.",
      },
      {
        id: "6c",
        title: "Deploy RetryGuard alongside TopFull",
        status: "pending",
        why: "RetryGuard runs in parallel with TopFull during the second experiment.",
        how: [
          "Run RetryGuard as a process on master or as a Kubernetes pod.",
          "Ensure it reads the same metrics source you validated.",
          "Start proxy + deploy_rl + RetryGuard before load.",
        ],
        doneWhen: "RetryGuard is running and logs when it enables/disables retries.",
      },
      {
        id: "6d",
        title: "Run experiment: TopFull + RetryGuard",
        status: "pending",
        why: "This is the primary project measurement.",
        how: [
          "Repeat Phase 5 exactly: same Locust scripts, same duration, same replica counts.",
          "Only difference: RetryGuard active.",
          "Collect metrics to a new folder e.g. run_topfull_retryguard.",
        ],
        doneWhen: "You have two result sets: baseline vs RetryGuard.",
      },
    ],
  },
  {
    id: "phase7",
    title: "Phase 7 - Evaluation and Report",
    duration: "Day 8-9",
    guides: [
      {
        id: "7a",
        title: "Compare baseline vs TopFull + RetryGuard",
        status: "pending",
        why: "This is the core project deliverable.",
        how: [
          "Plot or table: goodput, p95 latency, rejection %, retries per request.",
          "Compare CPU/memory and pod replica counts during overload.",
          "Check if RetryGuard reduced retry storms without hurting goodput (paper Table 1).",
        ],
        doneWhen: "You have clear numbers showing difference between the two runs.",
      },
      {
        id: "7b",
        title: "Write evaluation report",
        status: "pending",
        why: "Document setup, methodology, and findings for the workshop.",
        how: [
          "Describe environment: VM sizes, K8s 1.26, TopFull + Online Boutique.",
          "Explain RetryGuard integration point (what mentors agreed in Phase 0c).",
          "Present Phase 5 baseline vs Phase 6 RetryGuard metrics with graphs/tables.",
          "Match report format mentors requested in MENTOR-COORDINATION.md.",
        ],
        doneWhen: "Report is ready for lab review.",
      },
    ],
  },
];

const vmSpec = [
  ["Master Node", "1", "8+ vCPU, 16 GB RAM", "K8s control plane, TopFull proxy, RL, metrics"],
  ["Worker Nodes", "2-5", "8+ vCPU, 16 GB RAM", "Online Boutique pods, cAdvisor"],
  ["Load Generator", "1", "8+ vCPU, 16 GB RAM", "Locust traffic only"],
];

const configFiles = [
  ["global_config.json", "All paths, IPs, ports", "First file to edit"],
  ["proxy_online_boutique.go:28", "Config path", "Absolute path to global_config.json"],
  ["deploy_rl.py:13", "Config path", "Absolute path to global_config.json"],
  ["metric_collector.py:9", "Config path", "Absolute path to global_config.json"],
  ["overload_detection.py:10", "Config path", "Absolute path to global_config.json"],
  ["resource_collector.py:456", "cAdvisor pod count", "Must match # of worker nodes"],
  ["online_boutique_create.sh", "--host=http://IP:30440", "Master node IP"],
  ["locust_online_boutique.py:293", "Proxy address", "http://MASTER_IP:8090"],
];

const experimentMatrix = [
  ["Baseline", "TopFull", "Default (retries on)", "Phase 5"],
  ["Primary", "TopFull", "RetryGuard", "Phase 6"],
];

const experimentTones: Array<"info" | "success"> = ["info", "success"];

export default function WorkplanCanvas() {
  return (
    <Stack gap={20} style={{ padding: 24, maxWidth: 880 }}>
      <Stack gap={4}>
        <H1>Project 1: TopFull + RetryGuard on Cloud VMs</H1>
        <Text tone="secondary">
          TAU Deepness Lab Workshop - Retries for Cloud Microservices
        </Text>
      </Stack>

      <Callout tone="info" title="How to use this workplan">
        Before Phase 1: PREREQUISITES.md and MENTOR-COORDINATION.md. Expand a
        phase, then one step at a time. Full commands: SETUP-GUIDE.md.
      </Callout>

      <Grid columns={2} gap={12}>
        <Stat value="4-7" label="Cloud VMs" />
        <Stat value="~8 days" label="Timeline" />
        <Stat value="7 phases" label="Workplan" />
        <Stat value="$5-15/day" label="Est. cloud cost" />
      </Grid>

      <H2>Phase-by-Phase Workplan</H2>
      <Text tone="secondary" size="small">
        Scroll this panel. Open one phase, then one step inside it.
      </Text>

      {phases.map((phase, i) => (
        <Card key={phase.id} collapsible defaultOpen={i === 0}>
          <CardHeader trailing={<Pill tone="info" size="sm">{phase.duration}</Pill>}>
            {phase.title}
          </CardHeader>
          <CardBody>
            <PhaseSteps guides={phase.guides} />
          </CardBody>
        </Card>
      ))}

      <Divider />

      <H2>VM Architecture</H2>
      <Table headers={["Role", "Count", "Min Specs", "Purpose"]} rows={vmSpec} striped />

      <H2>Configuration Reference</H2>
      <Table headers={["File (line)", "What to Change", "Notes"]} rows={configFiles} striped />

      <H2>Experiment Matrix (two runs only)</H2>
      <Table
        headers={["Run", "Overload control", "Retries", "When"]}
        rows={experimentMatrix}
        rowTone={experimentTones}
        striped
      />

      <H2>Key Metrics to Collect</H2>
      <Grid columns={2} gap={12}>
        <Card>
          <CardHeader>Performance</CardHeader>
          <CardBody>
            <Stack gap={6}>
              <Text weight="semibold">Goodput (rps)</Text>
              <Text tone="secondary" size="small">Successful responses within latency SLO</Text>
              <Text weight="semibold">P95 Latency (ms)</Text>
              <Text tone="secondary" size="small">End-to-end 95th percentile</Text>
              <Text weight="semibold">Rejection Rate (%)</Text>
              <Text tone="secondary" size="small">Failed requests</Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>Cost / Efficiency</CardHeader>
          <CardBody>
            <Stack gap={6}>
              <Text weight="semibold">Retries per request</Text>
              <Text tone="secondary" size="small">Retry storm size during overload</Text>
              <Text weight="semibold">CPU + Memory</Text>
              <Text tone="secondary" size="small">Pod resource usage</Text>
              <Text weight="semibold">Pod replica count</Text>
              <Text tone="secondary" size="small">Over-scaling from retries</Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>
    </Stack>
  );
}
