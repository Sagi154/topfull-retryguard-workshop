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

### 0. Opening (1 slide)

**Project name:** RetryGuard on TopFull — TAU Communication Networks Workshop

**Participants:** Yoav Binyamin Naaman, Sagi Eisenberg, Ido Zacharia

Nothing else on this slide — no plan summary, roles, or timeline.

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

**Primary focus — explain what it is and how it works.** These slides should give the audience a real understanding of the mechanism and its design logic before any numbers are mentioned. Key results are supporting context at the end, not the centerpiece. Do **not** lead with pseudocode or "Algorithm 1" — describe the behavior in plain language.

**The problem it solves:** Default retry mechanisms (exponential backoff, jitter, retry budgets) are designed for instantaneous failures. During prolonged miscoordination — when services scale at different rates — retries become counterproductive. They create *retry storms*: a snowball effect of failed retries that wastes resources, inflates costs (self-inflicted Denial-of-Wallet), and degrades performance.

**How it works (this is the main content of the slide):**

- Each microservice has a small controller that watches its own health signal — typically HTTP rejection rate (503/429), optionally latency or retry volume — read from the local Istio/Envoy sidecar.
- **When things go bad:** if rejections stay above ~20% for several consecutive measurement windows (~30 seconds each), the controller turns off retries for that service only (patches the Istio VirtualService so new requests are not retried).
- **When things recover:** once rejections stay below the threshold for the same number of consecutive windows, retries are turned back on.
- **Distributed by design:** every service decides independently; there is no central coordinator.
- **Quiet under normal load:** if rejection rates stay low, the controller never changes anything — retries behave as configured by default.

**Key results (TAU Deepness Lab, 2025) — brief, supporting context only:**

- AWS: reduced retry attempts from 2.09/request to 0.05/request (98% reduction), resource billing from 1029% to 100%.
- Istio/Kubernetes: reduced retries from 0.31/request to 0.01/request, billing from 224% to 100%.
- Rejection rate stayed the same or improved slightly.
- Up to 65% reduction in resource consumption, 90% improvement in latency.
- Also mitigates DDoS amplification — prevents attackers from exploiting retry storms to multiply short bursts into prolonged damage.

> **Slide design note:** Do not let benchmark numbers dominate the visual layout. The mechanism explanation (problem → how it works → distributed design) must occupy the bulk of the slide space. Results belong in a compact footnote or a secondary bullet block — they validate the approach, they do not define it.

### 4. Stack & Topology (1 slide)

- **Environment:** We will run on **Ron Nezer's existing lab environment** — a pre-provisioned Kubernetes cluster with the TopFull + Online Boutique stack already set up, rather than provisioning new cloud VMs from scratch. This removes setup risk and keeps the project focused on RetryGuard integration and measurement.
- Simple diagram: Locust → TopFull Go proxy + RL (master) → Istio/Envoy sidecars → Online Boutique pods on workers.
- RetryGuard runs on the master node: it reads per-service rejection rates from Istio/Envoy sidecar metrics and dynamically enables or disables retries by updating Istio VirtualService configurations.
- Online Boutique is the test application — a representative microservice call chain, not the subject of the study itself.

### 5. How We Test (2–3 slides — core of the deck)

**Baseline — TopFull only:**

- TopFull overload control active; Istio default retries on; RetryGuard **off**.
- Fixed workload scenario, duration, and replica counts — same for every run.
- Save logs/CSVs as the TopFull-only reference run.

**Experiment — TopFull + RetryGuard:**

- **Identical** load, topology, and duration; only addition: RetryGuard **on** alongside TopFull.
- Controller settings from paper Sec. 6.2 (~20% rejection threshold, ~30s measurement interval).

**Repeated runs:**

- Locust generates randomized user behavior (non-deterministic) — a single run per scenario is not enough.
- Each scenario (**TopFull only** and **TopFull + RetryGuard**) will be run multiple times with the same configuration.
- Results compared using averages/medians across runs to account for load generator variability.
- This ensures observed differences are due to RetryGuard, not random variation in traffic patterns.

**Comparison:**

- Same inputs, two experiment arms (**TopFull only** vs **TopFull + RetryGuard**), multiple runs — isolates RetryGuard's effect from noise.

### 6. What We Want to Find Out (2–3 slides — the intellectual core)

This section is the intellectual core of the project. It deserves real slide space — not a single bullet list. Each question should be stated clearly, explained in a sentence or two, and the audience should understand *why* it's worth asking. This section comes **before** the load scenarios because the questions are what motivate the scenarios.

**Opening frame (1 slide):**

The central question: does adding RetryGuard on top of TopFull actually make things better, or is TopFull's overload control already sufficient on its own? RetryGuard was validated in AWS and Istio/K8s environments — but never specifically alongside a sophisticated top-down overload controller. That gap is exactly what this project investigates.

**The specific open questions (1–2 slides):**

- **System-level gains** — Does RetryGuard further improve global goodput and latency during overload, or does TopFull's entry-point control already absorb the problem so that retries are no longer a meaningful factor?

- **Topology beneficiaries** — Which specific microservices in the call chain benefit most? Do leaf-node services (deeper in the chain, closer to the bottleneck) respond differently than gateway-adjacent services? Is the benefit uneven across the topology?

- **Chain propagation** — If RetryGuard activates on a single downstream service, do those resource savings propagate upward through the rest of the execution path? Or is the effect local?

- **Controller interaction** — TopFull's RL controller and RetryGuard are both feedback loops running simultaneously on overlapping signals. TopFull adjusts entry admission rates; RetryGuard toggles per-service retry policies. Do they cooperate — RetryGuard suppressing internal amplification while TopFull manages entry load — or does one loop's correction interfere with the other's? This is unique to the combination of these two systems and has not been studied.

- **Combined equilibrium** — When RetryGuard suppresses internal retries at a bottleneck, the bottleneck's load drops, which improves the goodput and latency signals that TopFull's RL observes. TopFull may respond by increasing its admission rate. Does this feedback loop find a better stable throughput point — more goodput at the same capacity — or does the increased admission re-trigger overload and undo the gains?

- **Topology position sensitivity** — Does the structural position of the bottleneck service change RetryGuard's relative contribution? We compare two positions that differ in **how directly TopFull's entry control reaches them** — not in raw chain depth: a **gateway-adjacent, directly-controlled** service (e.g., ProductCatalog — called directly from Frontend on many entry APIs; TopFull maps and throttles this bottleneck most directly at entry) vs an **indirect, single-path** service (e.g., Payment — reachable only through Checkout on one API path, so TopFull's top-down signal is mediated by Checkout and most attenuated). RetryGuard operates per-service regardless of position, but the gap between TopFull's entry control and RetryGuard's local action may differ by how directly the bottleneck is exposed to that entry control. Note: Online Boutique is a shallow topology, so this contrasts the *directness* of control (direct vs Checkout-mediated), not literal chain depth. This has not been tested alongside a top-down controller like TopFull.

- **Interval parameter sensitivity** — Is RetryGuard's 30-second re-enable interval optimal when TopFull is co-running? This interval was validated in the original paper (Sec. 6.2) without a simultaneous top-down overload controller. TopFull's RL makes rate-control decisions every 1 second, so the recovery dynamics after overload may be faster or more oscillatory than in the original RetryGuard experiments. Does the optimal interval shift in this context? A shorter interval could allow faster retry recovery once TopFull has stabilized admission; a longer one provides more conservative suppression but delays throughput recovery. There is no established answer for this combination.

Each question should be written as a full sentence and briefly explained — not rendered as a grid of labelled boxes or a 2×2 layout.

### 7. Load Scenarios (one slide per scenario, plus an intro slide — follow directly from the questions above)

The scenarios follow directly from the open questions above — each scenario is designed to answer specific questions, not chosen arbitrarily. Make this connection explicit on every scenario slide: state clearly which question(s) that scenario is designed to answer. Explain each scenario — what the traffic looks like, what stress it creates, and which questions it is designed to answer.

**Intro slide:** Explain that the scenarios are derived from the open questions above, not chosen independently. State the shared infrastructure: all scenarios use TopFull's synthetic workload generator (Locust + TopFull scripts), not ad-hoc traffic. This slide sets up the logic before the individual scenario slides.

**Scenario 1: Normal Operation**

- Traffic: flat, manageable RPS, well within service capacity — no overload.
- What it tests: does RetryGuard stay entirely non-intrusive when things are healthy? The controller should detect rejection rates below the threshold and leave Istio configurations untouched.
- Answers: the "system-level gains" question from the non-overload side — a necessary sanity check before the core experiment.

**Scenario 2: Sustained Overload (the core experiment)**

- **Setup:** Start from Normal Operation traffic, then step Locust RPS up until offered load exceeds capacity (ρ > 1) and **hold that level for at least 5–10 minutes** — long enough for RetryGuard's ~30s measurement windows to fire repeatedly.
- **What happens in the system:** TopFull throttles how many new requests enter at the Go proxy. Requests that *do* get through may still fail downstream (503/429). Istio then retries those failed calls internally — retries TopFull never counted when admitting traffic. Under sustained overload this creates a retry storm: the same user request generates multiple backend attempts, keeping services overloaded even after TopFull has cut entry rate.
- **Why duration matters — why 5–10 minutes and not 1–2:** The hold time must cover RetryGuard's full reaction *cycle*, not just its trigger.
  1. **Triggering alone costs ~1–2 minutes.** RetryGuard fires only after rejections stay above ~20% for several consecutive ~30s windows, so disabling retries even once already takes roughly 90–120 seconds. A 1–2 minute test mostly measures whether the detector *barely* manages to fire — and often it won't, because load drops before the windows confirm. That measures detection latency, not effect.
  2. **The effect needs time to appear.** The interesting behavior happens *after* suppression: bottleneck load drops, TopFull's 1-second RL loop reacts to the improved goodput/latency signals, and the system re-settles. A short run ends before any goodput recovery is observable.
  3. **The cycle must repeat.** Holding 5–10 minutes lets the disable → recover → (possibly re-enable) cycle fire repeatedly, so we observe stable, reproducible behavior rather than a single lucky event.
  4. **It matches the real failure mode.** RetryGuard is built for *prolonged miscoordination*, not brief spikes — a 1–2 minute spike is exactly the transient that default backoff, jitter, and retry budgets already absorb, so testing on it would understate RetryGuard and sit outside its design envelope.
- **What it tests:** With TopFull-only vs TopFull+RetryGuard under the same sustained overload, does RetryGuard detect the high rejection rates and shut off internal retries, reducing load and improving goodput or resource usage?
- **Answers:** system-level gains, topology beneficiaries, chain propagation, and controller interaction.

**Scenario 3: Targeted Bottleneck**

- Traffic: load that exercises the full call chain, while one specific downstream service (e.g., Checkout or a mid-chain service in Online Boutique) is constrained — reduced replica count or CPU limit — so it reaches ρ > 1 even under TopFull's throttled entry rate.
- **How this differs from Sustained Overload (beyond targeting one service):** Sustained Overload saturates the *whole system* by flooding the entry (global ρ > 1), so the effect is aggregate and hard to attribute to any single service. Here the overall offered load need not exceed total capacity — the stress is *engineered at one node* by constraining it. This difference is what makes the scenario worthwhile: it exposes a gap global overload cannot. To relieve one deep service, TopFull's only lever is to throttle the entire entry APIs that route through it — blunt and indirect, punishing healthy requests on those APIs — whereas RetryGuard acts surgically at the exact hot spot. And with a single known bottleneck we get *clean attribution*: we can measure how fast load drops at that one service and whether the relief *propagates upward*, neither of which is separable when everything is saturated at once.
- What it tests: TopFull detects the overloaded service and throttles the APIs that route through it at the entry. But after TopFull admits a request, the constrained service may still reject it, and its immediate upstream caller (via Istio) retries it. These internal retries are not counted by TopFull's proxy. RetryGuard, operating per-service with Istio metrics, sees the rejection rate directly at the bottleneck and suppresses those internal retries. Does this per-service suppression reduce load at the bottleneck faster and more directly than TopFull's top-down throttling? Does the benefit propagate upward through the call chain?
- Answers: topology beneficiaries, chain propagation, controller interaction. This is the scenario most directly analogous to the RetryGuard Bookinfo case study (Reviews service with slow HPA vs. Product service with fast HPA).

**Scenario 4: Topology Position Comparison**

- **Setup:** Two Targeted Bottleneck runs — same Locust load and same constraint method (reduced replicas or CPU limit on one service) — differing only in **which service** is constrained.
- **Why this is separate from Targeted Bottleneck (why not combine them):** Targeted Bottleneck first establishes *that* per-service suppression helps at a single bottleneck — it varies **RetryGuard on/off**. This scenario holds that result constant and varies only one new thing — the **structural position** of the bottleneck. Keeping them separate enforces changing one variable at a time: combining them would entangle "does RetryGuard help" with "does position matter," making either effect impossible to attribute. Targeted Bottleneck is the foundation; this is the controlled A/B built on top of it.
- **Run A — Gateway-adjacent, directly controlled (e.g., ProductCatalog):** Frontend calls this service directly on many product-browse paths. When ProductCatalog is overloaded, TopFull can map the problem to specific entry APIs quickly and throttle them. Istio retries from Frontend to ProductCatalog are still invisible to TopFull's proxy after admission.
- **Run B — Indirect, Checkout-mediated (e.g., Payment):** Reachable only via Checkout on a single path (Frontend → Checkout → Payment). When Payment is overloaded, TopFull's entry signal is mediated by Checkout — it may not throttle the right entry APIs until Checkout itself starts failing. Istio retries stack at Checkout→Payment.
- **What it tests:** Does RetryGuard's per-service retry suppression matter more when TopFull's entry signal is strong and direct (Run A) vs indirect and attenuated (Run B)? Do savings at the bottleneck propagate differently up the chain?
- **Scope note:** Online Boutique is a shallow topology, so Run A vs Run B contrasts how *directly* TopFull controls the bottleneck (direct vs Checkout-mediated), not literal chain depth — a limitation worth stating in the report. The distinguishing variables are indirection and fan-in (one mediated path vs many direct entry APIs).
- **Answers:** topology position sensitivity, topology beneficiaries, chain propagation.

**Scenario 5: Re-enable Interval Tuning**

- **Setup:** Repeat the Sustained Overload scenario multiple times. Keep load, replica counts, and RetryGuard threshold fixed; change only the **re-enable interval** — how long rejections must stay below ~20% before retries turn back on (e.g., 10s, 20s, 30s \[paper default\], 60s).
- **What happens in the system:** After RetryGuard disables retries, overload eases. TopFull's RL may then admit more traffic because goodput/latency signals improve. If RetryGuard re-enables retries **too soon**, internal retries restart before the bottleneck has truly cleared and overload returns. If it waits **too long**, the system stays retry-free after recovery and goodput stays artificially low.
- **Why this matters with TopFull:** The paper tuned the 30s default without a co-running top-down controller. TopFull adjusts admission every ~1 second, so recovery may be faster or more oscillatory than in the original RetryGuard experiments — the best interval may differ.
- **What it tests:** Which re-enable interval gives the best combined goodput and stability when TopFull and RetryGuard run together?
- **Answers:** interval parameter sensitivity, combined equilibrium.

> **Slide design note:** Each scenario should be described in prose first — what is happening in the system, not just a traffic pattern label. A traffic shape graph or timeline can support the description, but the slide must make sense without it. Across all scenarios, use TopFull's built-in collectors (`metric_collector.py`, `overload_detection.py`, `resource_collector.py`) for system-level and API-level metrics. RetryGuard's per-service decisions are driven by Istio/Envoy sidecar metrics — HTTP error rates read locally at each service — which are a separate measurement point from TopFull's entry-proxy collectors. Cross-reference both data streams when interpreting results.

### 8. Metrics (1–2 slides)

Three layers of measurement, each answering a different part of the question.

**Layer 1 — System & API performance** (TopFull's `metric_collector.py` → CSVs in `logs/`):

- Goodput and latency per API (`getcart`, `getproduct`, `postcheckout`, etc.) — the primary outcome metrics.
- Rejection rate per API — the signal RetryGuard's controller reads to decide whether to suppress retries.
- **Retries per request** — the most direct measure of whether RetryGuard is doing its job. This is the number to watch when comparing **TopFull only** vs **TopFull + RetryGuard**.

**Layer 2 — Infrastructure resource usage** (cAdvisor via `resource_collector.py`):

- CPU consumption and memory limits per pod — tracks whether retry suppression actually frees up resources at the service level.
- Pod instance counts over time (`num_instances.csv`) — shows how autoscaling responds under each condition.

**Layer 3 — Controller logic & state** (our RetryGuard script logs):

- Which services had retries toggled off and when — ties controller decisions to the topology beneficiaries question.
- Time-to-recovery: how long between retry suppression and re-enablement — shows the cool-down cycle in practice.
- Business priority context from TopFull's `overload_detection.py` — which APIs were flagged as overloaded and at what priority, so RetryGuard decisions can be cross-referenced with TopFull's state.

All collected data will be synthesized into comparative time-series charts for the final evaluation report — **TopFull only** vs **TopFull + RetryGuard**, side by side across the same metrics.

### 9. Timeline & Milestones (1 slide)

A clean, sequential view of what happens and when. No phase numbers — those are internal. No blocker callouts — dependencies are implied by the order, and surfacing them as visual warnings dominates the slide for the wrong reason. If a mentor asks about blockers, address them verbally.

| What                                                 | When     |
| ---------------------------------------------------- | -------- |
| Infrastructure setup — Ron Nezer's environment, Istio, app running | Week 1–2 |
| Baseline experiment — TopFull only                     | Week 2–3 |
| RetryGuard implementation and Istio integration      | Week 3   |
| Experiment — TopFull + RetryGuard                      | Week 3–4 |
| Evaluation, comparison, and final report             | Week 4   |


---

## Key tone point

Let the structure carry the rigor — don't announce it. The slide flow itself (open questions → scenarios designed to answer them → controlled methodology → defined metrics) communicates scientific credibility. Avoid meta-commentary like "this is not a sales pitch" or "we don't know the answers yet" — those phrases appear weak and defensive. Instead, just present the plan clearly: here's what we want to find out, here's how we'll test it, here's what we'll measure. The outcome — whether RetryGuard helps a lot, helps specific services only, or barely moves the needle — is the point of the work, not a caveat to apologize for.