# Action items — project plan presentation (RetryGuard on TopFull)

From mentor meeting **2026-06-04**. Use this when building the slide deck that explains **how you will test RetryGuard** on the TopFull + Online Boutique stack (not a live demo).

Related: [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md) | [WORKPLAN.md](WORKPLAN.md) Phases 5–7 | `Workshop recordings/meeting_transcript.md`

---

## Core narrative

We're integrating RetryGuard with TopFull on a Kubernetes microservice stack and measuring what happens — good or bad — when RetryGuard dynamically toggles retries during overload. The questions are open, the methodology is controlled, and the results will speak for themselves.

---

## Presentation scope (what mentors expect)

- [ ] **Plan, not demo** — Show project plan, milestones, setup, and evaluation approach. Running system is optional; a clear, concrete plan matters more.
- [ ] **Cover the full path** — VM/K8s setup → TopFull baseline run → RetryGuard integration → comparison → report.
- [ ] **Be concrete on timing** — When each phase closes, what depends on what, and when you need mentor input or budget.
- [ ] **Expect deep questions** — Especially on metrics, workloads, and where RetryGuard hooks into the stack. Slides should answer these before they are asked.

## General slide design rule

- [ ] **Text-first, visuals as support** — Every slide must be understandable from its text alone. Diagrams and charts reinforce an explanation; they do not replace it. If the concept only makes sense by looking at the visual, the slide is missing its explanation.
- [ ] Write the explanation in plain text or bullets first; add a visual only if it makes a clear point easier to follow.
- [ ] No decorative or "atmosphere" visuals that consume space without adding meaning.
- [ ] This applies to all slides, not just the background slides on TopFull and RetryGuard.

---

## Slide / section checklist

### 1. Goal and hypothesis

- [ ] One slide: measure **RetryGuard** (self-implemented from the paper) on **TopFull** + **Online Boutique** under overload — where it helps, where it doesn't, and what trade-offs emerge.
- [ ] Hypothesis: dynamic retry control reduces retry storms and protects goodput vs. default retries (align with RetryGuard paper Table 1 style metrics). Present this as the motivating idea, not as a disclaimer.
- [ ] Note: system-wide gain may be small while **specific microservices** show large improvement — plan to surface both.
- [ ] Do **not** add explicit "this is not a sales pitch" or "we don't know yet" lines — the controlled setup and open questions do that work implicitly.

### 2. What is TopFull? / What is RetryGuard? (background slides)

- [ ] **Lead with explanation, not visuals.** Each slide must first answer "what is this system and how does it work?" — the problem it solves + the mechanism. This is the primary content.
- [ ] Key results (benchmark numbers) go at the end as supporting context — compact, not dominant. Do not use large callout numbers or oversized stat blocks as the visual anchor of these slides.
- [ ] For TopFull: cover (1) the local starvation problem, (2) API-wise top-down control, (3) RL-based rate controller. Benchmarks summarized in 2–3 bullets, no big graphical callouts.
- [ ] For RetryGuard: cover (1) retry storms during prolonged miscoordination, (2) the productive-retry algorithm (threshold → disable/re-enable), (3) distributed, no central orchestrator. Benchmarks summarized in 2–3 bullets, no big graphical callouts.
- [ ] Use 1–2 slides per system — the slide count exists to give room for real explanation, not to add more visuals.

### 3. Stack and topology

- [ ] Diagram: Locust → TopFull proxy + RL (master) → Istio Envoy sidecars → Online Boutique on workers (keep topology **simple** — mentors said fancy visuals are unnecessary).
- [ ] List VM roles (master, 1 worker, loadgen) and min specs from [WORKPLAN.md](WORKPLAN.md). Note: master also runs Istio control plane.
- [ ] Show **RetryGuard integration point**: RetryGuard runs on the master node — it monitors overload signals from TopFull's collectors and dynamically enables or disables retries per service by updating Istio VirtualService configurations (decided — matches paper Sec. 4).

### 4. Cloud and budget

- [ ] Provider plan: **GCP** with student credits (~$300) was discussed; confirm with mentors (Alon / Chanok) before provisioning.
- [ ] Cost model: ~3 VMs, estimate hours/day and deallocate-when-idle policy.
- [ ] **Start minimal** (e.g. 3-node / smaller footprint), scale only if experiments require it; request extra budget only with justification.

### 5. How you will test (core of the deck)

> **Slide language note:** Do not use phase numbers (Phase 5, Phase 6, etc.) anywhere on the slides. Use descriptive titles only — "The Baseline", "The Experiment", "The Setup", etc. Phase numbers are internal planning references, not audience-facing labels.

#### The Baseline

- [ ] Same Locust scenario, duration, and replica counts for every later run.
- [ ] TopFull running; retries at **default (on)**; RetryGuard **off**.
- [ ] Save CSVs/logs to `baseline_topfull_no_retryguard`.

#### The Experiment

- [ ] **Identical** load and topology; only change: RetryGuard **on**.
- [ ] Document controller params from paper Sec. 6.2 (~20% threshold, ~30s interval).

#### Repeated runs

- [ ] Locust generates randomized user behavior (non-deterministic) — a single run per scenario is not sufficient.
- [ ] Run each scenario (baseline and RetryGuard) multiple times with the same configuration.
- [ ] Compare results using averages/medians across runs to account for load generator variability.
- [ ] This ensures observed differences are due to RetryGuard, not random variation in traffic patterns.


### 6. What We Want to Find Out (2–3 slides)

This is the intellectual core of the project — give it real space, not a bullet list. Each question needs a full sentence statement and a brief explanation of why it's non-obvious. This section comes **before** the load scenarios because the questions are what motivate the scenarios.

- [ ] **Opening frame (1 slide):** State the central question — does RetryGuard add value on top of TopFull, or is TopFull's overload control already sufficient? Explain why this is genuinely unknown: RetryGuard has been validated in AWS and K8s, but never alongside a sophisticated top-down overload controller like TopFull.
- [ ] **System-level gains** — Does RetryGuard further improve global goodput and latency, or does TopFull already absorb the retry problem at the entry point?
- [ ] **Topology beneficiaries** — Which services benefit most? Do services deeper in the call chain — farther from the entry point where TopFull throttles — respond differently than gateway-adjacent services?
- [ ] **Chain propagation** — If RetryGuard activates on one downstream service, does the benefit propagate up through the rest of the call chain?
- [ ] **Adversarial resilience** — Does hostile traffic trip the controller into misfiring, or does RetryGuard correctly suppress retry amplification from attacks?
- [ ] **Controller interaction** — TopFull's RL controller and RetryGuard are simultaneous feedback loops on overlapping signals. Do they cooperate or interfere? This is unique to the combination and not studied elsewhere.
- [ ] **Combined equilibrium** — When RetryGuard suppresses internal retries at a bottleneck, the bottleneck's load drops and TopFull's RL sees improved signals, potentially increasing its admission rate in response. Does this feedback loop settle at a better stable throughput point, or does the increased admission re-trigger overload and undo the gains?
- [ ] **Topology position sensitivity** — Does the structural position of the bottleneck service in the call chain change RetryGuard's relative contribution? Three positions matter: a gateway-adjacent service with a shallow sub-tree (TopFull sees it most directly at entry), a hub service like Checkout that fans out to many downstream callers (TopFull sees it indirectly; overload here triggers bidirectional retry amplification — upstream callers retry the hub while the hub retries all its downstream dependencies simultaneously), and a true leaf (TopFull's top-down signal is most attenuated). RetryGuard operates per-service regardless of position. The hub case is expected to be the most severe — suppressing retries at the hub relieves pressure across its entire downstream fan-out in one action — but this has not been tested alongside a top-down controller like TopFull.
- [ ] **Interval parameter sensitivity** — Is RetryGuard's 30-second re-enable interval optimal when TopFull is co-running? This interval was validated in the original paper (Sec. 6.2) without a simultaneous top-down overload controller. TopFull's RL makes rate-control decisions every 1 second, so the recovery dynamics after overload may be faster or more oscillatory than in the original RetryGuard experiments. Does the optimal interval shift in this context? A shorter interval could allow faster retry recovery once TopFull has stabilized admission; a longer one provides more conservative suppression but delays throughput recovery. There is no established answer for this combination.
- [ ] Each question should be written as a full sentence and briefly explained — not rendered as a grid of labelled boxes or a 2×2 layout.

### 7. Load Scenarios (one slide per scenario, plus an intro slide)

The scenarios follow directly from the open questions above — present them in that order on the slides. Each scenario is explicitly tied to the question(s) it is designed to answer. State that connection clearly on each slide. Given the centrality of this section to the experiment, allocate a dedicated slide to every scenario rather than compressing multiple scenarios onto one slide.

- [ ] **Intro slide:** explain that the scenarios are derived from the open questions above, not chosen independently. State the shared infrastructure: all scenarios use TopFull's **synthetic workload generator** (Locust + TopFull scripts), not ad-hoc traffic. This slide sets up the logic before the individual scenario slides.

- [ ] **Scenario slide: Normal Operation** — flat RPS within capacity. Tests that RetryGuard is non-intrusive when healthy; controller should detect <20% rejections and make zero changes. Answers the "system-level gains" sanity check (baseline side). The slide should describe what is happening in the system in plain language — not just label a traffic shape. Traffic graphs/timelines may support the description but must not replace it.

- [ ] **Scenario slide: Sustained Overload (the core experiment)** — a load increase that holds ρ > 1 for several minutes — long enough for RetryGuard's ~30s detection window to trigger. TopFull throttles at the entry; Istio retries fire internally after admission and are invisible to TopFull's proxy. Does RetryGuard suppress this internal retry amplification and produce measurable improvement on top of TopFull? Answers: system-level gains, topology beneficiaries, chain propagation, controller interaction. The slide should describe what is happening in the system in plain language — not just label a traffic shape.

- [ ] **Scenario slide: Targeted Bottleneck** — full call-chain traffic with one downstream service constrained (reduced replicas or CPU limit) so it reaches ρ > 1 even under TopFull's throttled entry rate. TopFull throttles the APIs routing through it at the entry; Istio retries from the bottleneck's upstream caller are internal and invisible to TopFull. RetryGuard detects the per-service rejection rate and suppresses those retries directly. Does this reduce load at the bottleneck faster than TopFull's top-down throttling, and does the benefit propagate up the call chain? Directly analogous to the RetryGuard Bookinfo case study. Answers: topology beneficiaries, chain propagation, controller interaction. The slide should describe what is happening in the system in plain language.

- [ ] **Scenario slide: Topology Position Comparison** — three Targeted Bottleneck runs that vary *where* in the Online Boutique call chain the constrained service sits, covering three structurally distinct positions. In all three runs, Istio retries from each constrained service's upstream caller(s) are internal and invisible to TopFull. The comparison tests whether RetryGuard's per-service suppression value scales with fan-out width and topology depth. Answers: topology position sensitivity, topology beneficiaries, chain propagation.
  1. **Gateway-adjacent / shallow sub-tree** (e.g., Recommendation or ProductCatalog): called directly by Frontend, with few or no downstream dependencies of its own. TopFull's entry-level API routing sees this bottleneck most directly.
  2. **Hub / sub-tree root** (e.g., Checkout): downstream from Frontend but itself fans out to call Cart, Shipping, Currency, ProductCatalog, Email, and Payment. Overloading Checkout creates retry amplification in both directions — Frontend retries Checkout (upward) and Checkout retries its six downstream callers simultaneously (downward). This is the widest fan-out case in Online Boutique; the hub case is expected to show the most severe retry amplification because suppressing retries at Checkout simultaneously relieves pressure across all its downstream callers.
  3. **Deep leaf** (e.g., Email or Payment): a leaf service — no downstream dependencies of its own — that is only reachable through an intermediate service (Checkout). Frontend cannot call it directly. TopFull's top-down signal here is most attenuated — the bottleneck is invisible at the entry until Checkout itself starts degrading.

- [ ] **Scenario slide: Re-enable Interval Tuning** — run the Sustained Overload scenario multiple times, holding all other parameters constant and varying only RetryGuard's re-enable interval (e.g., 10s, 20s, 30s \[paper default\], 60s). RetryGuard's Algorithm requires the rejection rate to stay below threshold for `Interval` consecutive measurement periods before re-enabling retries. Too short: risks premature re-enabling before the bottleneck has cleared, potentially re-triggering overload. Too long: keeps retries suppressed after the bottleneck clears, slowing throughput recovery. The paper's 30s default was validated without a co-running top-down controller; with TopFull's RL already adjusting admission rates every 1 second, the optimal interval may be shorter or longer. Is there a value that maximizes combined goodput during recovery in the TopFull context? Answers: interval parameter sensitivity, combined equilibrium.

- [ ] **Scenario slide: Attack Traffic (extension, given time)** — malicious burst-DDoS exploiting retry amplification. Tests whether hostile load trips the controller at the wrong time. Answers: adversarial resilience. Mark clearly on the slide that this is a time-permitting extension.

- [ ] Across all scenario slides: use **TopFull's built-in collectors** (`metric_collector.py`, `overload_detection.py`, `resource_collector.py`) for system-level and API-level metrics. RetryGuard's per-service decisions are driven by Istio/Envoy sidecar metrics — HTTP error rates read locally at each service — which are a separate measurement point from TopFull's entry-proxy collectors. Cross-reference both data streams when interpreting results.

### 8. Metrics (1–2 slides)

Three layers of measurement, each answering a different part of the question.

- [ ] **Layer 1 — System & API performance** (TopFull's `metric_collector.py` → CSVs in `logs/`):
  - Goodput and latency per API (`getcart`, `getproduct`, `postcheckout`, etc.) — the primary outcome metrics.
  - Rejection rate per API — the signal RetryGuard's controller reads to decide whether to suppress retries.
  - **Retries per request** — the most direct measure of whether RetryGuard is doing its job. This is the number to watch when comparing baseline vs. experiment.
- [ ] **Layer 2 — Infrastructure resource usage** (cAdvisor via `resource_collector.py`):
  - CPU consumption and memory limits per pod — tracks whether retry suppression actually frees up resources at the service level.
  - Pod instance counts over time (`num_instances.csv`) — shows how autoscaling responds under each condition.
- [ ] **Layer 3 — Controller logic & state** (our RetryGuard script logs):
  - Which services had retries toggled off and when — ties controller decisions to the topology beneficiaries question.
  - Time-to-recovery: how long between retry suppression and re-enablement — shows the cool-down cycle in practice.
  - Business priority context from TopFull's `overload_detection.py` — which APIs were flagged as overloaded and at what priority, so RetryGuard decisions can be cross-referenced with TopFull's state.
- [ ] All collected data synthesized into comparative time-series charts for the final evaluation report — baseline run vs. RetryGuard run, side by side across the same metrics.

### 9. Milestones and dependencies

- [ ] **No phase numbers on the slide** — phase numbers are internal planning references. The audience doesn't know them and doesn't need to.
- [ ] **No blocker callouts as visual elements** — dependencies are implied by the order of the milestones. If a mentor asks about blockers, address them verbally. Putting them on the slide as warnings makes them the visual focal point, which they shouldn't be.
- [ ] Present a clean, sequential list: what happens and when. That's all the slide needs.

| What | When |
|------|------|
| Infrastructure setup — VMs, K8s, Istio, app running | Week 1–2 |
| Baseline experiment — TopFull running, default retries | Week 2–3 |
| RetryGuard implementation and Istio integration | Week 3 |
| RetryGuard experiment | Week 3–4 |
| Evaluation, comparison, and final report | Week 4 |

- [ ] Fill in actual dates once the project start date is confirmed.

---

## Team tasks (this week)

| # | Task | Suggested owner |
|---|------|-----------------|
| 1 | Draft slide outline from sections above | PM / presenter |
| 2 | Draw simple architecture diagram (Locust → TopFull proxy → Istio/Envoy sidecars → Boutique) | Infra |
| 3 | Write one-page test matrix: baseline vs RetryGuard, metrics, workloads | Evaluation lead |
| 4 | Email mentors (Chanok in CC): GCP credits, recommended K8s setup, presentation format | Infra |
| 4b | Start email thread with **Itai** for ongoing technical questions | Whole team |
| 5 | Read RetryGuard Sec. 4 + 6.2; note productive-retry controller inputs/outputs for one slide | Implementation lead |
| 6 | List per-microservice metrics collection plan (cAdvisor / TopFull collectors) | Metrics |
| 7 | Rehearse Q&A: "where does RetryGuard sit?" and "how do you know it helped?" | Whole team |

---

## What *not* to promise in the presentation

- Live cluster demo (unless already stable).
- Extra baselines (DAGOR, DiffTry) unless mentors explicitly expand scope.
- Perfect Hebrew/English transcript of the meeting — use [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md) and this file as the source of truth.

---

## Key tone point

Let the structure carry the rigor — don't announce it. The slide flow itself (open questions → scenarios designed to answer them → controlled methodology → defined metrics) communicates scientific credibility. Avoid meta-commentary like "this is not a sales pitch" or "we don't know the answers yet" — those phrases appear weak and defensive. Instead, just present the plan clearly: here's what we want to find out, here's how we'll test it, here's what we'll measure. The outcome — whether RetryGuard helps a lot, helps specific services only, or barely moves the needle — is the point of the work, not a caveat to apologize for.
