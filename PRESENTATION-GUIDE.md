# Project Plan Presentation Guide

RetryGuard on TopFull — TAU Communication Networks Workshop

---

## Core narrative

We're integrating RetryGuard with TopFull on a Kubernetes microservice stack and measuring what happens — good or bad — when RetryGuard dynamically toggles retries during overload. The questions are open, the methodology is controlled, and the results will speak for themselves.

---

## General slide design principle

**Text-first, visuals as support.** Every slide should be understandable from its text alone. Diagrams, charts, and graphs are there to reinforce and illustrate what the text already explains — not to replace the explanation. If a concept can only be understood by staring at a visual, the slide is missing its explanation.

In practice:
- Write out what the slide is saying in plain sentences or bullets first.
- Add a visual only if it makes an already-clear explanation easier to follow.
- Never use a diagram or graph as the primary vehicle for conveying a concept — a viewer who misses the visual should still walk away with the core idea.
- Avoid decorative or "atmosphere" visuals that consume slide space without adding meaning.

This applies everywhere — not just to the TopFull and RetryGuard background slides.

---

## Slide flow

### 1. Goal and hypothesis

- One slide: measure **RetryGuard** (self-implemented from the paper, integrated via Istio service mesh) on **TopFull** + **Online Boutique** under overload — where it helps, where it doesn't, and what trade-offs emerge.
- **Hypothesis:** dynamic retry control reduces retry storms and protects goodput vs. default retries (align with RetryGuard paper Table 1 style metrics). Present this as the motivating idea, not as a disclaimer.
- Note: system-wide gain may be small while **specific microservices** show large improvement — plan to surface both.
- Do **not** add explicit "this is not a sales pitch" or "we don't know yet" lines — the controlled setup and open questions do that work implicitly.

### 2. What is TopFull? (1–2 slides)

**Primary focus — explain what it is and how it works.** These slides should give the audience a real understanding of the system before any numbers are mentioned. Key results are supporting context at the end, not the centerpiece.

**The problem it solves:** Existing overload controls (DAGOR, Breakwater) manage individual microservices in isolation. When multiple APIs share overloaded microservices, this causes *starvation* — some API requests get partially processed then rejected downstream, wasting resources.

**How it works (this is the main content of the slide):**

- Top-down, API-wise load control at the entry point — controls the rate of external APIs, not individual microservices.
- Clusters interdependent APIs for parallel load control — breaks the problem into independent sub-problems that can be solved simultaneously.
- RL-based rate controller — adaptively adjusts throttling aggressiveness based on end-to-end goodput and latency (trained via Sim2real transfer learning).

**Key results (SIGCOMM 2024) — brief, supporting context only:**

- 1.82x more goodput than DAGOR, 2.26x more than Breakwater during overload.
- With autoscaler: up to 3.91x more goodput under traffic surge vs standalone autoscaler.
- Tolerates traffic spikes with up to 57% fewer resources.
- Converges to optimal rate in 5 seconds (vs 27 seconds for DAGOR).

> **Slide design note:** Do not let benchmark numbers dominate the visual layout. The mechanism explanation (problem → how it works) must occupy the bulk of the slide space. Results belong in a compact footnote or a secondary bullet block — they validate the system, they do not define it.

### 3. What is RetryGuard? (1–2 slides)

**Primary focus — explain what it is and how it works.** These slides should give the audience a real understanding of the algorithm and its design logic before any numbers are mentioned. Key results are supporting context at the end, not the centerpiece.

**The problem it solves:** Default retry mechanisms (exponential backoff, jitter, retry budgets) are designed for instantaneous failures. During prolonged miscoordination — when services scale at different rates — retries become counterproductive. They create *retry storms*: a snowball effect of failed retries that wastes resources, inflates costs (self-inflicted Denial-of-Wallet), and degrades performance.

**How it works (this is the main content of the slide):**

- A productive-retry controller (Algorithm 1) monitors rejection rate (or latency/retry volume) per service.
- If rejections exceed a threshold (~20%) for N consecutive intervals (~30s): disable retries for that service.
- If below threshold for N intervals: re-enable retries.
- Distributed — each service manages retries independently, no central orchestrator needed.
- Non-intrusive under normal conditions — only activates during prolonged miscoordination.

**Key results (TAU Deepness Lab, 2025) — brief, supporting context only:**

- AWS: reduced retry attempts from 2.09/request to 0.05/request (98% reduction), resource billing from 1029% to 100%.
- Istio/Kubernetes: reduced retries from 0.31/request to 0.01/request, billing from 224% to 100%.
- Rejection rate stayed the same or improved slightly.
- Up to 65% reduction in resource consumption, 90% improvement in latency.
- Also mitigates DDoS amplification — prevents attackers from exploiting retry storms to multiply short bursts into prolonged damage.

> **Slide design note:** Do not let benchmark numbers dominate the visual layout. The mechanism explanation (problem → algorithm logic → distributed design) must occupy the bulk of the slide space. Results belong in a compact footnote or a secondary bullet block — they validate the algorithm, they do not define it.

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

### 6. What We Want to Find Out (2–3 slides — the intellectual core)

This section is the intellectual core of the project. It deserves real slide space — not a single bullet list. Each question should be stated clearly, explained in a sentence or two, and the audience should understand *why* it's worth asking. This section comes **before** the load scenarios because the questions are what motivate the scenarios.

**Opening frame (1 slide):**

The central question: does adding RetryGuard on top of TopFull actually make things better, or is TopFull's overload control already sufficient on its own? RetryGuard was validated in AWS and Istio/K8s environments — but never specifically alongside a sophisticated top-down overload controller. That gap is exactly what this project investigates.

**The specific open questions (1–2 slides):**

- **System-level gains** — Does RetryGuard further improve global goodput and latency during overload, or does TopFull's entry-point control already absorb the problem so that retries are no longer a meaningful factor?

- **Topology beneficiaries** — Which specific microservices in the call chain benefit most? Do leaf-node services (deeper in the chain, closer to the bottleneck) respond differently than gateway-adjacent services? Is the benefit uneven across the topology?

- **Chain propagation** — If RetryGuard activates on a single downstream service, do those resource savings propagate upward through the rest of the execution path? Or is the effect local?

- **Adversarial resilience** — Under malicious traffic, does hostile load trick the controller into misfiring — suppressing retries when it shouldn't — or does RetryGuard successfully blunt retry amplification from attack traffic?

- **Controller interaction** — TopFull's RL controller and RetryGuard are both feedback loops running simultaneously on overlapping signals. TopFull adjusts entry admission rates; RetryGuard toggles per-service retry policies. Do they cooperate — RetryGuard suppressing internal amplification while TopFull manages entry load — or does one loop's correction interfere with the other's? This is unique to the combination of these two systems and has not been studied.

- **Combined equilibrium** — When RetryGuard suppresses internal retries at a bottleneck, the bottleneck's load drops, which improves the goodput and latency signals that TopFull's RL observes. TopFull may respond by increasing its admission rate. Does this feedback loop find a better stable throughput point — more goodput at the same capacity — or does the increased admission re-trigger overload and undo the gains?

- **Topology position sensitivity** — Does the structural position of the bottleneck service in the call chain change RetryGuard's relative contribution? Three positions matter: a gateway-adjacent service with a shallow sub-tree (TopFull sees it most directly at entry), a hub service like Checkout that fans out to many downstream callers (TopFull sees it indirectly; overload here triggers bidirectional retry amplification — upstream callers retry the hub while the hub retries all its downstream dependencies simultaneously), and a true leaf (TopFull's top-down signal is most attenuated). RetryGuard operates per-service regardless of position. The hub case is expected to be the most severe — suppressing retries at the hub relieves pressure across its entire downstream fan-out in one action — but this has not been tested alongside a top-down controller like TopFull.

- **Interval parameter sensitivity** — Is RetryGuard's 30-second re-enable interval optimal when TopFull is co-running? This interval was validated in the original paper (Sec. 6.2) without a simultaneous top-down overload controller. TopFull's RL makes rate-control decisions every 1 second, so the recovery dynamics after overload may be faster or more oscillatory than in the original RetryGuard experiments. Does the optimal interval shift in this context? A shorter interval could allow faster retry recovery once TopFull has stabilized admission; a longer one provides more conservative suppression but delays throughput recovery. There is no established answer for this combination.

Each question should be written as a full sentence and briefly explained — not rendered as a grid of labelled boxes or a 2×2 layout.

### 7. Load Scenarios (one slide per scenario, plus an intro slide — follow directly from the questions above)

The scenarios follow directly from the open questions above — each scenario is designed to answer specific questions, not chosen arbitrarily. Make this connection explicit on every scenario slide: state clearly which question(s) that scenario is designed to answer. Explain each scenario — what the traffic looks like, what stress it creates, and which questions it is designed to answer.

**Intro slide:** Explain that the scenarios are derived from the open questions above, not chosen independently. State the shared infrastructure: all scenarios use TopFull's synthetic workload generator (Locust + TopFull scripts), not ad-hoc traffic. This slide sets up the logic before the individual scenario slides.

**Scenario: Normal Operation**

- Traffic: flat, manageable RPS, well within service capacity — no overload.
- What it tests: does RetryGuard stay entirely non-intrusive when things are healthy? The controller should detect rejection rates below the threshold and leave Istio configurations untouched.
- Answers: the "system-level gains" question from the non-overload side — a necessary sanity check before the core experiment.

**Scenario: Sustained Overload (the core experiment)**

- Traffic: a load increase that pushes ρ > 1 and holds it there for several minutes — long enough for RetryGuard's detection window (~30s consecutive intervals above the rejection threshold) to trigger and suppress retries. This is the exact miscoordination condition the RetryGuard paper was designed for, and the condition that matters: RetryGuard only acts during *prolonged* overload. A brief spike does not activate it.
- What it tests: TopFull controls admission at the entry; Istio's default retry policy fires retries internally, after TopFull has already admitted the request. These internal retries are invisible to TopFull's rate limiter and amplify load on downstream services beyond what TopFull can throttle. Does RetryGuard suppress this internal retry amplification, and does that produce measurable improvement in goodput or resource usage on top of TopFull alone?
- Answers: system-level gains, topology beneficiaries, chain propagation, and controller interaction.

**Scenario: Targeted Bottleneck**

- Traffic: load that exercises the full call chain, while one specific downstream service (e.g., Checkout or a mid-chain service in Online Boutique) is constrained — reduced replica count or CPU limit — so it reaches ρ > 1 even under TopFull's throttled entry rate.
- What it tests: TopFull detects the overloaded service and throttles the APIs that route through it at the entry. But after TopFull admits a request, the constrained service may still reject it, and its immediate upstream caller (via Istio) retries it. These internal retries are not counted by TopFull's proxy. RetryGuard, operating per-service with Istio metrics, sees the rejection rate directly at the bottleneck and suppresses those internal retries. Does this per-service suppression reduce load at the bottleneck faster and more directly than TopFull's top-down throttling? Does the benefit propagate upward through the call chain?
- Answers: topology beneficiaries, chain propagation, controller interaction. This is the scenario most directly analogous to the RetryGuard Bookinfo case study (Reviews service with slow HPA vs. Product service with fast HPA).

**Scenario: Topology Position Comparison**

- Traffic: three separate Targeted Bottleneck runs — same load, same methodology — varying only *where* in the Online Boutique call chain the constrained service sits. In all three runs, Istio retries from each constrained service's upstream caller(s) are internal and invisible to TopFull. The comparison tests whether RetryGuard's per-service suppression value scales with fan-out width and topology depth.
  1. **Gateway-adjacent / shallow sub-tree** (e.g., Recommendation or ProductCatalog): called directly by Frontend, with few or no downstream dependencies of its own. TopFull's entry-level API routing sees this bottleneck most directly.
  2. **Hub / sub-tree root** (e.g., Checkout): downstream from Frontend but itself fans out to call Cart, Shipping, Currency, ProductCatalog, Email, and Payment. Overloading Checkout creates retry amplification in both directions — Frontend retries Checkout (upward) and Checkout retries its six downstream callers simultaneously (downward). The hub case is expected to show the most severe retry amplification because suppressing retries at Checkout simultaneously relieves pressure across all its downstream callers.
  3. **Deep leaf** (e.g., Email or Payment): a leaf service with no downstream dependencies of its own, reachable only through an intermediate service (Checkout). Frontend cannot call it directly. TopFull's top-down signal here is most attenuated — the bottleneck is invisible at the entry until Checkout itself starts degrading.
- Answers: topology position sensitivity, topology beneficiaries, chain propagation.

**Scenario: Re-enable Interval Tuning**

- Traffic: the Sustained Overload scenario run multiple times, holding all other parameters constant and varying only RetryGuard's re-enable interval (e.g., 10s, 20s, 30s \[paper default\], 60s).
- What it tests: RetryGuard's algorithm requires the rejection rate to stay below the threshold for `Interval` consecutive measurement periods before re-enabling retries. Too short: risks premature re-enabling before the bottleneck has cleared, potentially re-triggering overload. Too long: keeps retries suppressed after the bottleneck clears, slowing throughput recovery. The paper's 30s default was validated without a co-running top-down controller; with TopFull's RL adjusting admission rates every 1 second, the recovery dynamics may be faster or more oscillatory. Does the optimal interval shift in this context?
- Answers: interval parameter sensitivity, combined equilibrium.

**Scenario: Attack Traffic (extension, given time)**

- Traffic: malicious burst-DDoS pattern simulating an attacker exploiting retry amplification.
- What it tests: does hostile traffic trip the controller at the wrong time, or does RetryGuard correctly suppress retry storms caused by the attack without disrupting healthy services?
- Answers: adversarial resilience.
- Mark clearly on the slide that this is a time-permitting extension.

> **Slide design note:** Each scenario should be described in prose first — what is happening in the system, not just a traffic pattern label. A traffic shape graph or timeline can support the description, but the slide must make sense without it. Across all scenarios, use TopFull's built-in collectors (`metric_collector.py`, `overload_detection.py`, `resource_collector.py`) for system-level and API-level metrics. RetryGuard's per-service decisions are driven by Istio/Envoy sidecar metrics — HTTP error rates read locally at each service — which are a separate measurement point from TopFull's entry-proxy collectors. Cross-reference both data streams when interpreting results.

### 8. Metrics (1–2 slides)

Three layers of measurement, each answering a different part of the question.

**Layer 1 — System & API performance** (TopFull's `metric_collector.py` → CSVs in `logs/`):

- Goodput and latency per API (`getcart`, `getproduct`, `postcheckout`, etc.) — the primary outcome metrics.
- Rejection rate per API — the signal RetryGuard's controller reads to decide whether to suppress retries.
- **Retries per request** — the most direct measure of whether RetryGuard is doing its job. This is the number to watch when comparing baseline vs. experiment.

**Layer 2 — Infrastructure resource usage** (cAdvisor via `resource_collector.py`):

- CPU consumption and memory limits per pod — tracks whether retry suppression actually frees up resources at the service level.
- Pod instance counts over time (`num_instances.csv`) — shows how autoscaling responds under each condition.

**Layer 3 — Controller logic & state** (our RetryGuard script logs):

- Which services had retries toggled off and when — ties controller decisions to the topology beneficiaries question.
- Time-to-recovery: how long between retry suppression and re-enablement — shows the cool-down cycle in practice.
- Business priority context from TopFull's `overload_detection.py` — which APIs were flagged as overloaded and at what priority, so RetryGuard decisions can be cross-referenced with TopFull's state.

All collected data will be synthesized into comparative time-series charts for the final evaluation report — baseline run vs. RetryGuard run, side by side across the same metrics.

### 9. Timeline & Milestones (1 slide)

A clean, sequential view of what happens and when. No phase numbers — those are internal. No blocker callouts — dependencies are implied by the order, and surfacing them as visual warnings dominates the slide for the wrong reason. If a mentor asks about blockers, address them verbally.

| What                                                 | When     |
| ---------------------------------------------------- | -------- |
| Infrastructure setup — VMs, K8s, Istio, app running  | Week 1–2 |
| Baseline experiment — TopFull running, default retries | Week 2–3 |
| RetryGuard implementation and Istio integration      | Week 3   |
| RetryGuard experiment                                | Week 3–4 |
| Evaluation, comparison, and final report             | Week 4   |


---

## Key tone point

Let the structure carry the rigor — don't announce it. The slide flow itself (open questions → scenarios designed to answer them → controlled methodology → defined metrics) communicates scientific credibility. Avoid meta-commentary like "this is not a sales pitch" or "we don't know the answers yet" — those phrases appear weak and defensive. Instead, just present the plan clearly: here's what we want to find out, here's how we'll test it, here's what we'll measure. The outcome — whether RetryGuard helps a lot, helps specific services only, or barely moves the needle — is the point of the work, not a caveat to apologize for.