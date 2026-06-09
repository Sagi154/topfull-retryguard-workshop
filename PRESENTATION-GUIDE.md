# Project Plan Presentation Guide

RetryGuard on TopFull — TAU Deepness Lab Workshop

---

## Core narrative

We're building a controlled experiment to evaluate RetryGuard's real-world effectiveness when integrated with TopFull on a Kubernetes microservice stack. The experiment measures what happens — good or bad — when RetryGuard dynamically toggles retries during overload. We don't assume it works; we test it.

---

## Slide flow

### 1. Project Goal (1 slide)

- Evaluate RetryGuard's impact on a microservice system running TopFull overload control.
- Not proving it works — designing an experiment that reveals where it helps, where it doesn't, and what trade-offs emerge.
- Based on RetryGuard's algorithm (self-implemented from the paper) integrated via Istio service mesh.

### 2. What is TopFull? (1–2 slides)

**The problem it solves:** Existing overload controls (DAGOR, Breakwater) manage individual microservices in isolation. When multiple APIs share overloaded microservices, this causes *starvation* — some API requests get partially processed then rejected downstream, wasting resources.

**How it works:**
- Top-down, API-wise load control at the entry point — controls the rate of external APIs, not individual microservices.
- Clusters interdependent APIs for parallel load control — breaks the problem into independent sub-problems that can be solved simultaneously.
- RL-based rate controller — adaptively adjusts throttling aggressiveness based on end-to-end goodput and latency (trained via Sim2real transfer learning).

**Key results (SIGCOMM 2024):**
- 1.82x more goodput than DAGOR, 2.26x more than Breakwater during overload.
- With autoscaler: up to 3.91x more goodput under traffic surge vs standalone autoscaler.
- Tolerates traffic spikes with up to 57% fewer resources.
- Converges to optimal rate in 5 seconds (vs 27 seconds for DAGOR).

### 3. What is RetryGuard? (1–2 slides)

**The problem it solves:** Default retry mechanisms (exponential backoff, jitter, retry budgets) are designed for instantaneous failures. During prolonged miscoordination — when services scale at different rates — retries become counterproductive. They create *retry storms*: a snowball effect of failed retries that wastes resources, inflates costs (self-inflicted Denial-of-Wallet), and degrades performance.

**How it works:**
- A productive-retry controller (Algorithm 1) monitors rejection rate (or latency/retry volume) per service.
- If rejections exceed a threshold (~20%) for N consecutive intervals (~30s): disable retries for that service.
- If below threshold for N intervals: re-enable retries.
- Distributed — each service manages retries independently, no central orchestrator needed.
- Non-intrusive under normal conditions — only activates during prolonged miscoordination.

**Key results (TAU Deepness Lab, 2025):**
- AWS: reduced retry attempts from 2.09/request to 0.05/request (98% reduction), resource billing from 1029% to 100%.
- Istio/Kubernetes: reduced retries from 0.31/request to 0.01/request, billing from 224% to 100%.
- Rejection rate stayed the same or improved slightly.
- Up to 65% reduction in resource consumption, 90% improvement in latency.
- Also mitigates DDoS amplification — prevents attackers from exploiting retry storms to multiply short bursts into prolonged damage.

### 4. Stack & Topology (1 slide)

- Simple diagram: Locust → Go proxy → Istio/Envoy sidecars → microservice application (Online Boutique).
- RetryGuard runs on the master node: it monitors overload signals from TopFull's collectors and dynamically enables or disables retries per service by updating Istio VirtualService configurations.
- Online Boutique is the test application — a representative microservice call chain, not the subject of the study itself.

### 5. How We Test (2–3 slides — core of the deck)

**Baseline experiment:**

- TopFull running, retries ON (default), RetryGuard OFF.
- Fixed workload scenario, duration, and replica counts — same for every run.

**RetryGuard experiment:**

- Identical setup, only change: RetryGuard ON.
- Controller params from paper Sec. 6.2 (~20% threshold, ~30s interval).

**Repeated runs:**

- Locust generates randomized user behavior (non-deterministic) — a single run per scenario is not enough.
- Each scenario (baseline and RetryGuard) will be run multiple times with the same configuration.
- Results compared using averages/medians across runs to account for load generator variability.
- This ensures observed differences are due to RetryGuard, not random variation in traffic patterns.

**Comparison:**

- Same inputs, different retry behavior, multiple runs — isolates RetryGuard's effect from noise.

### 6. Workloads & Scenarios (1–2 slides)

**Two load scenarios:**

- **No overload** — does RetryGuard stay out of the way when things are normal?
- **Expected overload** — periodic overload (TopFull-style), does RetryGuard improve the situation?

**Future exploration (given time):**

- Given time, we would like to explore additional scenarios such as **malicious / attack traffic** — how does hostile traffic affect RetryGuard's behavior? Does it trigger retry suppression at the wrong time?

All driven by TopFull's synthetic workload generator (same framework as the paper), not ad-hoc traffic.

### 7. What We Want to Find Out (1 slide — the experimental questions)

These are open questions the experiment will answer:

- Does adding RetryGuard on top of TopFull further improve system-level goodput and latency during overload, or is TopFull's overload control already sufficient?
- Which types of services in the call chain benefit? Are leaf services affected differently than gateway services?
- Does RetryGuard's effect on one service propagate to others through the call chain?
- Given time: how does RetryGuard behave under adversarial conditions like attack traffic?

Frame explicitly: *"We don't know these answers yet. That's what we're testing."*

### 8. Metrics (1 slide)

**Provided by TopFull's built-in collectors:**

| Level | What we measure | Source |
|-------|-----------------|--------|
| **Per-API performance** | Goodput, latency, rejection rate for each API (`getcart`, `getproduct`, `postcheckout`, etc.) | `metric_collector.py` → CSVs in `logs/` |
| **Resource usage** | CPU/memory per pod | `resource_collector.py` → cAdvisor |
| **Replica counts** | Pod instance counts over time | `num_instances.csv` |
| **Overload state** | Which APIs are in overload and business priority | `overload_detection.py` |

**We build / log ourselves:**

| Level | What we measure | Source |
|-------|-----------------|--------|
| **RetryGuard decisions** | When it fires, which services it toggles on/off, time to recovery | Our RetryGuard script logs |

Results presented with charts and graphs.

### 9. Timeline & Milestones (1 slide)

| Milestone | Target |
|-----------|--------|
| Infrastructure setup (VMs, K8s, Istio, app deployed) | Week 1–2 |
| Baseline experiment (TopFull, default retries) | Week 2–3 |
| RetryGuard implementation + integration | Week 3 |
| RetryGuard experiment | Week 3–4 |
| Evaluation and comparison report | Week 4 |

---

## Key tone point

This is an experiment, not a sales pitch for RetryGuard. Present it as: *"Here's our test plan. Here's what we'll measure. Here are the questions we'll answer."* The results might show RetryGuard helps a lot, helps only specific services, or barely helps at all in this setup — all of those are valid findings. Mentors will respect that you're designing a rigorous experiment rather than assuming an outcome.
