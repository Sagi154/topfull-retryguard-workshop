# Managed Kubernetes for TopFull + RetryGuard

Should managed Kubernetes (GKE on GCP, AKS, EKS) help with setup?

Related: [WORKPLAN.md](WORKPLAN.md) Phase 1–2 | [PRESENTATION-ACTION-ITEMS.md](PRESENTATION-ACTION-ITEMS.md) | [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md)

---

## Short answer

Managed Kubernetes **can** reduce some setup pain, but it does **not** map cleanly to how TopFull is documented today. A **hybrid** is the most realistic option if you want managed K8s.

---

## What the workplan assumes today

TopFull’s setup is not “just run pods on a cluster”:

- **Self-managed K8s 1.26** via `kubeadm` on **Ubuntu 20.04**
- **cri-dockerd** (Docker), not the default containerd most managed clusters use
- The **master VM is dual-purpose**: control plane, **Istio control plane (istiod)**, *and* host processes for the Go proxy (`:8090`), `deploy_rl.py`, metrics, and later RetryGuard
- A **separate loadgen VM** runs Locust
- IPs and ports are wired through `global_config.json` and NodePorts (`30440`, etc.)

Much of Phase 2 friction is **TopFull’s bespoke cluster layout**, not only “install Kubernetes.”

---

## Where managed K8s helps

| Benefit | Why it matters |
|--------|----------------|
| **Skip kubeadm / Calico / control-plane ops** | Phases 2b–2e become much shorter |
| **Faster bring-up** | Good for a short workshop window |
| **Node pools** | Easier to add/remove workers for Online Boutique |
| **Fits GCP direction** | Mentors already discussed GCP credits |

---

## Where it fights TopFull

| Issue | Impact |
|-------|--------|
| **No “master VM” for TopFull processes** | Proxy/RL/metrics are meant to run on the master host, not as standard managed-cluster components |
| **cri-docker vs containerd** | TopFull README targets Docker + cri-dockerd; managed clusters usually use containerd |
| **Version / YAML assumptions** | Paper setup targets K8s 1.26; managed defaults are often newer |
| **Extra cost** | Control-plane fee + nodes can burn ~$300 credits faster than 4 raw VMs |
| **Not mentor-validated** | Workshop docs and another student group likely follow the VM + kubeadm path |

---

## Practical recommendation

### For the presentation

Present the **paper-faithful path** (VMs + kubeadm) as the default plan.

### If you want managed K8s anyway — use a hybrid

```
Loadgen VM          TopFull host VM              Managed K8s (GKE)
(Locust)       →    (proxy, RL, RetryGuard,      →  worker node pool
                    kubectl, metrics)              (Online Boutique + cAdvisor
                                                   + Istio Envoy sidecars)
```

- Managed cluster runs **only the microservice workloads**
- One VM still runs **TopFull + RetryGuard** as host processes (same as today, minus kubeadm on that box)
- You still need a loadgen VM

That saves the hardest K8s bootstrap work while keeping TopFull’s architecture mostly intact.

### Istio compatibility note

RetryGuard integration uses **Istio VirtualService retry policies** (matching paper Sec. 4). If using managed GKE, Istio can be installed via `istioctl` on the host VM (same as kubeadm path) or via GKE’s Anthos Service Mesh add-on. The kubeadm path uses Istio 1.17.x for K8s 1.26 compatibility. If using GKE with a newer K8s version, use the corresponding Istio version.

### Avoid without mentor approval

**“Pure GKE, everything in-cluster”** — you’d need to containerize the proxy/RL, rework networking, and debug compatibility away from the published setup.

---

## Suggested slide line

> **Default:** self-managed K8s on VMs (TopFull paper setup).  
> **Optional:** GKE for worker nodes only + dedicated TopFull host VM — faster cluster setup, but needs mentor confirmation and config changes.

---

## Open question for mentors

Add to your mentor email / presentation:

- [ ] Is **hybrid GKE** (managed workers + TopFull host VM) acceptable, or should we stick to full VM + kubeadm for paper fidelity?
