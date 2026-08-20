# Evaluating RetryGuard on TopFull

> Markdown transcription of `context/Evaluating_RetryGuard_on_TopFull.pdf` (17 slides, NotebookLM-generated deck).
> Content below follows the deck slide-by-slide. Slide headers ("LAB PROTOCOL", "16:9") and the NotebookLM watermark are omitted.

---

## Slide 1 — Title

**RetryGuard on TopFull — TAU Communication Networks Workshop**

Authors:

- Yoav Binyamin Naaman
- Sagi Eisenberg
- Ido Zacharia

---

## Slide 2 — Experimental Overview

### Evaluating dynamic retry control beneath top-down overload admission

**Objective**

Our objective is to measure a custom implementation of RetryGuard integrated via the Istio service mesh beneath TopFull's global admission controller.

We are evaluating this stack on the Online Boutique application under overload conditions to identify systemic benefits, trade-offs, and microservice-specific improvements.

**Hypothesis**

Dynamic, per-service retry control reduces retry storms and protects global goodput and resource utilization significantly better than default static retry mechanisms.

---

## Slide 3 — TopFull manages global entry to prevent local starvation

**The Problem: Local Starvation**

Existing overload controls (like DAGOR) manage individual microservices in isolation. When multiple APIs share an overloaded microservice, requests get partially processed and then rejected deep in the call chain. This wastes resources and causes starvation for other APIs.

**The Mechanism: API-Wise Load Control**

TopFull solves this by moving load control to the top of the stack.

- It operates at the entry point, controlling the rate of external APIs rather than individual microservices.
- It clusters interdependent APIs so load control decisions can be solved in parallel.
- It utilizes a Reinforcement Learning (RL) rate controller that adjusts throttling aggressiveness every 1 second based on end-to-end goodput and latency.

**Validation Baseline**

TopFull achieves **1.82x more goodput than DAGOR** during overload and converges to optimal rates in just **5 seconds**.

**Accompanying diagram:** API 1 (isolated, dashed blue group) and APIs 2 + 3 (dashed red group) fan out into shared Service A and Service B — API 1 → Service A; API 2 → Service A and Service B; API 3 → Service B. This illustrates interdependent APIs sharing downstream microservices.

---

## Slide 4 — RetryGuard eliminates self-inflicted retry storms during prolonged miscoordination

**The Problem: Prolonged Miscoordination**

Default retries (exponential backoff, jitter) handle instantaneous network failures. However, during prolonged miscoordination — such as auto-scaler lag — retries become counterproductive. They create "retry storms" that waste resources and trigger Denial-of-Wallet scenarios.

**The Mechanism: Distributed Local Protection**

RetryGuard operates bottom-up, without a central orchestrator.

- Small controllers at each microservice read local Istio/Envoy sidecar health signals.
- If the local HTTP rejection rate stays above **~20%** for several consecutive **~30s** windows, the controller explicitly disables retries by patching the local Istio VirtualService.
- Once rejections drop and stay below the threshold, retries are automatically re-enabled.

**Validation Baseline**

In production tests, RetryGuard reduced retry attempts by **98%** and improved latency by up to **90%**.

**Accompanying illustration:** two waste-bin drawings contrasting a *Transient Failure* (a single crumpled paper dropped cleanly into the bin) with *Prolonged Miscoordination* (an overflowing bin with paper spilling everywhere) — the visual metaphor for a retry storm.

---

## Slide 5 — Pre-provisioned Kubernetes cluster executing the Online Boutique application

The experiment operates within a pre-provisioned lab environment to ensure isolated, repeatable testing variables.

**System Topology Mapping**

1. **Workload Generation:** Locust load generator.
2. **Global Throttling:** TopFull Go Proxy + RL Controller (Master Node).
3. **Local Routing:** Istio Envoy Sidecars.
4. **Application Layer:** Online Boutique Pods (Worker Nodes).

**Integration Point**

RetryGuard runs as a dedicated Python process on the Master Node. It reads per-service rejection rates from local Istio metrics and dynamically patches Istio VirtualService configurations to toggle retries.

**Accompanying architecture diagram**

- `User` and `loadgenerator` both send HTTP into `frontend` (which has an Istio Sidecar).
- `frontend` fans out to: `ad`, `recommendation`, `checkout`, and `cart` (Istio Sidecar).
- `recommendation` → `productcatalog` (Istio Sidecar).
- `cart` → Redis cache.
- `checkout` → `shipping`, `currency`, `payment`, `email` (each with an Istio Sidecar).
- **Master Node** box contains three stacked components: `TopFull Proxy`, `RL Controller`, and `RetryGuard` (highlighted).
- A dashed control-plane line labeled **"Read Metrics & Patch Configs"** runs from the Master Node components to the sidecar-equipped services.

---

## Slide 6 — Isolating RetryGuard through identical fixed-workload comparisons

To guarantee attribution, the experiment holds the infrastructure, workload, and global controller identical across two comparative states.

| Variable | Baseline (TopFull Only) | Experiment (TopFull + RetryGuard) |
|---|---|---|
| Workload Scenario | Fixed | Fixed |
| Infrastructure Replicas | Fixed | Fixed |
| TopFull Overload Control | Active | Active |
| Istio Default Retries | ON | ON |
| **RetryGuard** | **OFF** | **ON** |

The only altered variable between the two arms is whether RetryGuard is running.

---

## Slide 7 — Repeated trials eliminate load generation noise

Because the Locust load generator produces non-deterministic, randomized user behavior, single test runs are statistically insufficient. We ensure data integrity through repeated iterations.

By capturing multiple runs for every scenario and evaluating the median and average outputs, any observed variance in goodput, resource consumption, or latency is strictly attributable to the activation of RetryGuard.

---

## Slide 8 — Investigating the interaction between macro admission and micro protection

RetryGuard has been validated in isolation, but its interaction with a sophisticated, top-down admission controller like TopFull is an unsolved system dynamics question. We are testing to answer:

**System-Level Gains**
Does RetryGuard further improve global goodput and latency, or does TopFull already absorb the retry problem at the proxy entry point?

**Topology Beneficiaries**
Which services benefit the most? Do services deep in the call chain — furthest from TopFull's top-down throttling — respond differently than gateway-adjacent services?

**Chain Propagation**
If RetryGuard activates on one deep downstream service, does the resulting load reduction cascade and propagate up through the rest of the call chain?

---

## Slide 9 — Uncovering combined equilibrium and parameter sensitivity

**Combined Equilibrium and Controller Interaction**
TopFull and RetryGuard represent simultaneous feedback loops acting on overlapping signals. When [RetryGuard] suppresses internal retries and clears a bottleneck, TopFull's 1-second RL loop sees improved signals and admits more traffic. Do these controllers cooperate to find a higher stable throughput, or does increased admission re-trigger overload and undo the gains?

**Topology Position Sensitivity**
Does the structural position of the bottleneck service change RetryGuard's relative contribution? The gap between TopFull's entry control and RetryGuard's local action may differ drastically by call depth.

**Interval Parameter Sensitivity**
Is RetryGuard's default 30-second re-enable interval optimal when competing with TopFull's rapid 1-second admission adjustments? The recovery dynamics after overload may be faster or more oscillatory in this combined stack.

---

## Slide 10 — A diagnostic toolkit built on shared synthetic infrastructure

The following five load scenarios are not arbitrary stress tests. They are derived directly from our open questions. By applying TopFull's synthetic workload generator (Locust + TopFull scripts) across shared infrastructure, each scenario serves as a controlled crucible designed to extract definitive answers regarding system equilibrium, topology, and controller interaction.

Scenario pipeline:

1. **Scenario 1** — Normal Operation
2. **Scenario 2** — Sustained Overload
3. **Scenario 3** — Targeted Bottleneck
4. **Scenario 4** — Topology Position Comparison
5. **Scenario 5** — Re-enable Interval Tuning

---

## Slide 11 — Scenario 1: Normal Operation

**Traceability:** Answers System-Level Gains (Sanity Check)

**System State**

The synthetic workload generator maintains a flat, manageable requests-per-second (RPS) rate well within the application's maximum capacity. There is no system overload.

**Experimental Objective**

This establishes our baseline and acts as a necessary sanity check. It tests whether RetryGuard remains entirely non-intrusive when the infrastructure is healthy. The controller should detect rejection rates far below the ~20% threshold, make zero changes, and leave the default Istio configurations untouched.

**Diagram:** `[Node A] → [Node B] → [Node C]`, all unstressed (grey).

---

## Slide 12 — Scenario 2: Sustained Overload

**Traceability:** Answers System Gains, Beneficiaries, Chain Propagation, Controller Interaction

**System State**

The RPS is stepped up until offered load exceeds capacity (ρ > 1) and is held for 5 to 10 minutes.

**Experimental Objective**

TopFull will throttle entry, but admitted requests may still fail downstream. Istio retries these failed calls internally — invisible to TopFull — creating a retry storm. We hold the overload for 5–10 minutes to cover RetryGuard's full reaction cycle. Triggering alone takes ~2 minutes of sustained rejections. A long hold allows the complete **disable → recover → re-enable** cycle to fire. We measure whether RetryGuard successfully shuts off internal retries and improves goodput compared to the TopFull-only baseline.

**Diagram:** `[Node A] → [Node B] → [Node C]`, all three nodes stressed (red glow).

---

## Slide 13 — Scenario 3: Targeted Bottleneck

**Traceability:** Answers Topology Beneficiaries, Chain Propagation, Controller Interaction

**System State**

The application experiences full call-chain traffic, but one specific downstream service is artificially constrained via reduced replicas or CPU limits. The overall offered load does not exceed total capacity, but the targeted node hits ρ > 1.

**Experimental Objective**

This exposes a gap that global overload testing cannot. To relieve one deep service, TopFull's only lever is to blindly throttle entire entry APIs. RetryGuard, however, acts surgically at the exact hot spot based on Istio metrics. This engineered bottleneck provides clean attribution, allowing us to watch if load drops faster at the bottleneck and if that relief propagates upward.

**Diagram:** `[Node A] → [Node B] → [Node C]`, with only the middle node (B) stressed (red glow).

---

## Slide 14 — Scenario 4: Topology Position Comparison

**Traceability:** Answers Topology Position Sensitivity

**System State**

We conduct two separate Targeted Bottleneck runs with identical load and constraint methods. The only altered variable is which service is constrained.

**Experimental Objective**

- **Run A (Gateway-adjacent):** A service called directly by the frontend (e.g., ProductCatalog). TopFull's top-down signal is strong and maps overload to entry APIs quickly.
- **Run B (Deep leaf):** A service reachable only deep in the chain (e.g., Payment). TopFull's signal is heavily attenuated, and internal retries stack up sequentially.

**Comment:** Because of this relatively shallow topology, the results regarding position sensitivity and chain propagation may not be fully relevant or representative of more complex systems that comprise many more.

**Diagram:** Two vertical chains beneath a `Gateway` box. In Run A the node immediately below the gateway is stressed (red); in Run B the bottom-most node in the chain is stressed (red).

---

## Slide 15 — Scenario 5: Re-enable Interval Tuning

**Traceability:** Answers Interval Parameter Sensitivity, Combined Equilibrium

**System State**

The Sustained Overload scenario is repeated identically multiple times. We vary only a single configuration: RetryGuard's re-enable interval (testing **10s, 20s, 30s, and 60s**).

**Experimental Objective**

RetryGuard's original 30s default was tuned without a co-running top-down controller. Because TopFull adjusts admission every ~1 second, recovery dynamics are fundamentally different. If RetryGuard re-enables too soon, internal retries restart before the bottleneck clears. If it waits too long, goodput stays artificially low. This run identifies the optimal interval for combined stability.

**Diagram:** A timeline axis marked at 1s, 10s, 20s, 30s, and 60s. TopFull's rapid loop sits at 1s (highlighted red), with arrows from each candidate RetryGuard interval (10s / 20s / 30s / 60s) pointing back to it, showing the timescale mismatch between the two controllers.

---

## Slide 16 — Triangulating outcomes through three layers of measurement

We correlate three distinct data streams to construct a complete evaluation report.

| Layer | Source | Metrics & Evidence |
|---|---|---|
| **Layer 1: System & API Performance** | TopFull `metric_collector.py` | **Metrics:** Goodput, API latency, API rejection rate, retries per request. **Evidence:** The primary outcome metrics. Directly measures if RetryGuard reduces the retry storm. |
| **Layer 2: Infrastructure Resource Usage** | cAdvisor via `resource_collector.py` | **Metrics:** CPU/Memory limits, pod instance counts over time. **Evidence:** Tracks whether local retry suppression translates into tangible resource savings and prevents over-scaling. |
| **Layer 3: Controller Logic & State** | RetryGuard script logs | **Metrics:** Per-service toggle timing, time-to-recovery intervals. **Evidence:** Cross-references RetryGuard's localized decisions with TopFull's global business priority state. |

---

## Slide 17 — Project Timeline & Delivery Milestones

Our methodology is executed through a strictly sequential rollout to ensure environment stability before introduction of variables.

| Timeframe | Milestone |
|---|---|
| Week 1 – 2 | Infrastructure setup — provisioning Ron Nezer's environment, Istio mesh, and application deployment. |
| Week 2 – 3 | Baseline experiment — execution and data capture for TopFull only. |
| Week 3 | RetryGuard implementation and Istio integration. |
| Week 3 – 4 | Experiment — execution and data capture for TopFull + RetryGuard. |
| Week 4 | Evaluation, comparative metrics synthesis, and final report delivery. |
