# NotebookLM Prompt — Project Plan Slide Deck

Paste this prompt into NotebookLM after uploading the source documents listed below.

---

## Sources to upload

1. `RetryGuard.pdf` — the paper we are implementing (Algorithm 1, Sec. 4, Sec. 6.2; TAU Deepness Lab, arXiv:2511.23278, November 2025)
2. `TopFull.pdf` — the overload-control system (SIGCOMM 2024) we run RetryGuard on top of
3. `TAU-workshop -26 retryGuard.pptx` — existing workshop slide deck (use for style and formatting reference only)
4. `WORKPLAN.md` — full phase-by-phase project plan (Phases 0–7, ~8 days, VM architecture, experiment matrix)
5. `PRESENTATION-GUIDE.md` — **the authoritative slide flow** (9-section structure the deck must follow, including section order)
6. `PRESENTATION-ACTION-ITEMS.md` — slide checklist, mentor expectations, team tasks
7. `SETUP-GUIDE.md` — detailed step-by-step setup instructions for the full stack
8. TopFull GitHub repo README: https://github.com/kaist-ina/TopFull/tree/main

---

## Prompt

```
You are helping a student team at a Workshop in Communication Networks and Information Security
build a **project plan presentation** (slide deck). This is NOT a results talk — it presents how we
plan to test RetryGuard on a TopFull Kubernetes microservice setup. We have no results yet.

### Audience and purpose

Our professor said (translated): "I want to understand what you are going to do in the project and
what the deliverables will be. This is an expectations alignment. If the document is clear enough,
it can stand on its own without a meeting."

This means:
- The deck MUST be **self-explanatory** — it may be reviewed as a standalone document, without us
  presenting it live.
- The focus is: **what we will do**, **how we will do it**, and **what the deliverables are**.
- Clarity and concreteness matter more than flashy visuals.
- Tone: present the plan clearly and scientifically. Let the structure carry the rigor — do NOT add
  meta-commentary such as "this is not a sales pitch" or "we don't know the answers yet". These
  phrases appear weak and defensive. The controlled setup and open questions do that work implicitly.

### Slide design principle (applies to every slide)

**Text-first, visuals as support.** Every slide must be understandable from its text alone. Diagrams
and charts reinforce an explanation; they do not replace it. If the concept only makes sense by looking
at the visual, the slide is missing its explanation.
- Write the explanation in plain sentences or bullets first; add a visual only if it makes a
  clear point easier to follow.
- Never use a diagram or graph as the primary vehicle for conveying a concept.
- No decorative or "atmosphere" visuals that consume space without adding meaning.
- For the TopFull and RetryGuard background slides: mechanism explanation (problem → how it works)
  must occupy the bulk of the slide. Benchmark numbers belong in a compact footnote or secondary
  bullet block — they validate the system, they do not define it.

### Project summary

- **Our project:** Self-implement RetryGuard (Algorithm 1 from the RetryGuard paper) and evaluate
  its impact on a Kubernetes microservice system running TopFull overload control.
- **TopFull** (SIGCOMM 2024, KAIST): Top-down, API-wise overload control at the entry point. Uses
  an RL-based rate controller (Sim2Real transfer learning) that adjusts admission rates every
  1 second based on end-to-end goodput and percentile latencies. Solves the starvation problem
  where shared downstream microservices cause some API requests to be partially processed then
  rejected, wasting resources.
- **RetryGuard** (TAU Deepness Lab, 2025): A productive-retry controller (Algorithm 1) that monitors
  rejection rate per service. If rejections exceed ~20% for N consecutive ~30-second measurement
  intervals → disable retries (Consecutive_high ≥ Interval). Once below threshold for N consecutive
  intervals → re-enable (Consecutive_low ≥ Interval). Distributed — each service manages retries
  independently. Non-intrusive during normal operation. Validated on AWS Lambda/DynamoDB and Istio
  Kubernetes Bookinfo.
- **Integration method:** RetryGuard runs on the master node as a Python script, reads rejection
  signals from Istio/Envoy sidecar metrics (HTTP error rates per service), and patches Istio
  VirtualService retry policies per microservice via the Kubernetes Python client. Matches
  RetryGuard paper Appendix A (Istio integration) and paper Sec. 4 architecture.
- **Test application:** Online Boutique (Google's demo microservice app, 11 microservices including
  Frontend, Checkout, Cart, Productcatalog, Shipping, Currency, Email, Payment, Recommendation, Ad,
  Redis cache). A representative call chain, not the subject of study itself.
- **Infrastructure:** 4–7 cloud VMs (Ubuntu 20.04), Kubernetes 1.26, Istio service mesh, Calico CNI,
  cAdvisor, Locust load generator. Cloud provider: GCP with ~$300 student credits.

### Section order (follow PRESENTATION-GUIDE.md exactly)

The 9 sections must appear in this order:
1. Goal and hypothesis
2. What is TopFull?
3. What is RetryGuard?
4. Stack & Topology
5. How We Test
6. **What We Want to Find Out** ← comes BEFORE load scenarios; the questions motivate the scenarios
7. Load Scenarios ← each scenario is explicitly tied to the questions above
8. Metrics
9. Timeline & Milestones

Do NOT reorder these sections. In particular, do NOT put open questions after scenarios.

### Slide structure

The deck should have approximately 20–25 content slides. For each slide, produce:
1. A short slide title
2. Concise bullet points / content for the slide
3. Speaker notes (what to say or what a reader should understand)
4. Source reference (which uploaded document and section the content comes from)

Do NOT use phase numbers (Phase 5, Phase 6, etc.) anywhere on slides. Use descriptive titles:
"The Baseline", "The Experiment", "The Setup", etc. Phase numbers are internal planning references.

---

### Slide 1 — Goal and Hypothesis (1 slide)

- One slide: measure RetryGuard (self-implemented from Algorithm 1) on TopFull + Online Boutique
  under overload — where it helps, where it doesn't, and what trade-offs emerge.
- **Hypothesis:** dynamic retry control reduces retry storms and protects goodput vs. default retries.
  Present this as the motivating idea (align with RetryGuard paper Table 1 style metrics — retries
  per request, resource billing, rejection rate). This is not a disclaimer.
- Note: system-wide gain may be small while **specific microservices** show large improvement.
  Plan to surface both.
- Deliverables: (1) working K8s + TopFull + RetryGuard setup, (2) baseline vs. RetryGuard experiment
  data across all scenarios, (3) evaluation report with time-series charts comparing performance,
  resource, and cost metrics.
- Source: PRESENTATION-GUIDE.md §1, PRESENTATION-ACTION-ITEMS.md §1.

---

### Slides 2–3 — What is TopFull? (1–2 slides)

**Primary focus: explain what it is and how it works.** Mechanism first, numbers last.

**The problem it solves:**
Existing overload controls (DAGOR, Breakwater) manage individual microservices in isolation. When
multiple APIs share an overloaded downstream microservice, this causes *starvation* — some API
requests get partially processed then rejected, wasting resources. Example: if API 1 and API 2 both
pass through Microservice A (capacity 10k rps) and API 1 also passes through Microservice B (capacity
3k rps), a naive controller throttles both at MA but wastes MA's capacity on API 1 requests that will
be rejected at MB anyway, starving API 2.

**How TopFull works (main content):**
- Top-down, API-wise load control at the entry point — controls the rate of external APIs, not
  individual microservices internally.
- Clusters interdependent APIs for parallel load control — groups APIs that share overloaded
  microservices into independent sub-problems that can be solved simultaneously.
- RL-based rate controller (PPO, Sim2Real transfer learning) — adaptively adjusts throttling
  aggressiveness based on end-to-end goodput and percentile latencies. Makes rate-control decisions
  every 1 second.
- Respects business priority: rate-limits lowest-priority APIs first when reducing, increases
  highest-priority APIs first when recovering.

**Key results (SIGCOMM 2024) — compact, supporting context only:**
- 1.82x more goodput than DAGOR, 2.26x more than Breakwater during overload.
- With autoscaler: up to 3.91x more goodput under traffic surge vs. standalone autoscaler.
- Tolerates traffic spikes with up to 57% fewer resources.
- Converges to optimal rate in 5 seconds (vs. 27 seconds for DAGOR).
- Source: TopFull.pdf, PRESENTATION-GUIDE.md §2.

---

### Slides 4–5 — What is RetryGuard? (1–2 slides)

**Primary focus: explain what it is and how it works.** Mechanism first, numbers last.

**The problem it solves:**
Default retry mechanisms (exponential backoff, jitter, retry budgets) are designed for *instantaneous*
failures. During *prolonged miscoordination* — when services scale at different rates (e.g., a fast
upstream auto-scaler vs. a slow downstream database) — retries become counterproductive. They create
*retry storms*: a snowball effect where failed retries amplify load on an already-overloaded service.
Load factor ρ > 1 causes rejection rate to rise sharply (shown analytically in paper Sec. 5), and
each retry multiplies the load further. Result: self-inflicted Denial-of-Wallet (DoW) — inflated
costs, over-scaling, and degraded performance.

**How RetryGuard works (main content):**
- A productive-retry controller (Algorithm 1 in the paper) monitors rejection rate per service.
- If rejection rate exceeds Threshold (~20%) for `Interval` consecutive measurement periods
  (Consecutive_high ≥ Interval, ~30s each) → disable retries for that service.
- If rejection rate stays below Threshold for `Interval` consecutive periods
  (Consecutive_low ≥ Interval) → re-enable retries.
- Distributed — each service manages retries independently via its own local metrics.
  No central orchestrator required.
- Non-intrusive under normal operation (ρ < 1) — the transition from stable to overloaded is
  analytically sharp (Fig. 7 in paper), so false positives are negligible.
- Istio integration: a designated pod periodically samples Istio/Envoy sidecar HTTP error rates
  and patches Istio VirtualService retry configs via Kubernetes API. No per-request overhead.

**Key results (TAU Deepness Lab, 2025) — compact, supporting context only:**
- AWS: retries per request from 2.09 → 0.05 (98% reduction); billing from 1029% → 100%.
- Istio/Kubernetes: retries from 0.31 → 0.01/request; billing from 224% → 100%.
- Rejection rate maintained or slightly improved (not sacrificed for cost savings).
- Up to 65% reduction in resource consumption, >90% improvement in latency.
- Also mitigates DDoS amplification — brief burst attacks cannot sustain retry storms.
- Source: RetryGuard.pdf (Algorithm 1, Sec. 4, Sec. 6.2, Table 1), PRESENTATION-GUIDE.md §3.

---

### Slide 6 — Stack & Topology (1 slide)

- Simple diagram: Locust (load-gen VM) → Go proxy / rate limiter (master) → Istio/Envoy sidecars
  → Online Boutique microservices (worker VMs).
- RetryGuard runs on the master node alongside TopFull's RL controller: monitors rejection signals
  from Istio/Envoy sidecar metrics and dynamically enables or disables retries per service by
  patching Istio VirtualService configurations.
- Online Boutique is the test application — a representative microservice call chain (Frontend →
  Checkout → Cart, Shipping, Currency, ProductCatalog, Email, Payment; Frontend also calls
  Recommendation, Ad). Not the subject of study itself.
- VM roles: Master (8+ vCPU, 16GB — K8s control plane, Istio control plane, TopFull, RetryGuard),
  Workers 2–N (pods, cAdvisor), Load-gen (Locust only).
- Cloud provider: GCP with ~$300 student credits. Start minimal (3 nodes), scale only if needed.
  Deallocate when idle.
- Source: WORKPLAN.md (VM architecture table), PRESENTATION-GUIDE.md §4,
  PRESENTATION-ACTION-ITEMS.md §3–4.

---

### Slides 7–9 — How We Test (2–3 slides — core methodology)

**Important slide language note:** Do not use phase numbers. Use descriptive titles only.

**The Baseline (1 slide):**
- TopFull running, retries ON (Istio default), RetryGuard OFF.
- Fixed workload scenario, duration, and replica counts — identical for every run.
- Save all CSVs and logs to a named baseline artifact directory.

**The Experiment (1 slide):**
- Identical setup to baseline — same load, same topology, same replica counts.
- Only change: RetryGuard ON.
- Controller parameters from RetryGuard paper Sec. 6.2: ~20% rejection threshold,
  ~30-second measurement interval (Interval parameter in Algorithm 1).
- RetryGuard implemented as Python script on master node using Kubernetes Python client
  to patch Istio VirtualService CRDs.

**Repeated Runs (1 slide):**
- Locust generates randomized user behavior (non-deterministic) — a single run per scenario is
  insufficient to isolate RetryGuard's effect from random traffic variation.
- Each scenario (baseline and RetryGuard) run multiple times with the same configuration.
- Results compared using averages/medians across runs.
- Same inputs, different retry behavior, multiple runs → isolates RetryGuard's effect from noise.
- Source: PRESENTATION-GUIDE.md §5, WORKPLAN.md Phases 5–6,
  PRESENTATION-ACTION-ITEMS.md §5.

---

### Slides 10–12 — What We Want to Find Out (2–3 slides — intellectual core)

**This section is the intellectual core of the project. It deserves real slide space. Place it here,
BEFORE the scenario slides, because the questions are what motivate each scenario.**

Each question should be written as a full sentence and briefly explained. Do NOT render as a grid of
labelled boxes or a 2×2 layout.

**Opening frame (1 slide):**
The central question: does adding RetryGuard on top of TopFull actually make things better, or is
TopFull's overload control already sufficient on its own? RetryGuard has been validated in AWS and
standalone Istio/Kubernetes environments — but never specifically alongside a sophisticated top-down
overload controller. TopFull controls admission at the entry; but once a request is admitted, Istio's
internal retry policies fire independently inside the cluster, invisible to TopFull's proxy. Does
RetryGuard suppress this internal retry amplification and produce measurable gains on top of TopFull?
That gap is exactly what this project investigates.

**The specific open questions (1–2 slides):**

- **System-level gains** — Does RetryGuard further improve global goodput and latency during overload,
  or does TopFull's entry-point control already absorb the retry problem so that internal retries
  are no longer a meaningful factor?

- **Topology beneficiaries** — Which specific microservices in the call chain benefit most? Do
  leaf-node services (deeper in the chain, farther from where TopFull throttles) respond differently
  than gateway-adjacent services? Is the benefit uneven across the topology?

- **Chain propagation** — If RetryGuard activates on one downstream service, do the resource savings
  propagate upward through the rest of the execution path? Or is the effect local to that service?

- **Controller interaction** — TopFull's RL controller and RetryGuard are both feedback loops running
  simultaneously on overlapping signals. TopFull adjusts admission rates every 1 second based on
  end-to-end goodput; RetryGuard toggles per-service retry policies on a ~30-second cycle based on
  local rejection rates. Do they cooperate — RetryGuard suppressing internal amplification while
  TopFull manages entry load — or does one loop's correction interfere with the other's? This
  combination has not been studied.

- **Combined equilibrium** — When RetryGuard suppresses internal retries at a bottleneck, the
  bottleneck's load drops, which improves the goodput and latency signals that TopFull's RL observes.
  TopFull may respond by increasing its admission rate. Does this feedback loop find a better stable
  throughput point — more goodput at the same capacity — or does the increased admission re-trigger
  overload and undo the gains?

- **Topology position sensitivity** — Does the structural position of the bottleneck service in the
  call chain change RetryGuard's relative contribution? Three positions matter:
  (1) Gateway-adjacent / shallow sub-tree (e.g., Recommendation or ProductCatalog): called directly
  by Frontend, few downstream dependencies. TopFull sees this bottleneck most directly at entry.
  (2) Hub / sub-tree root (e.g., Checkout): downstream from Frontend but fans out to call Cart,
  Shipping, Currency, ProductCatalog, Email, and Payment. Overloading Checkout creates bidirectional
  retry amplification — Frontend retries Checkout (upward) and Checkout retries its six downstream
  callers simultaneously (downward). The hub case is expected to show the most severe amplification.
  (3) Deep leaf (e.g., Email or Payment): no downstream dependencies of its own, reachable only
  through Checkout. TopFull's top-down signal here is most attenuated — the bottleneck is invisible
  at the entry until Checkout itself starts degrading.

- **Interval parameter sensitivity** — Is RetryGuard's 30-second re-enable interval optimal when
  TopFull is co-running? This interval was validated in the original paper (Sec. 6.2) without a
  simultaneous top-down overload controller. TopFull's RL makes rate-control decisions every 1 second,
  so the recovery dynamics after overload may be faster or more oscillatory than in the original
  RetryGuard experiments. Does the optimal interval shift in this context?

- **Adversarial resilience** — Under malicious traffic, does hostile load trick the controller into
  misfiring — suppressing retries when it shouldn't — or does RetryGuard successfully blunt retry
  amplification from attack traffic?

Source: PRESENTATION-GUIDE.md §6, PRESENTATION-ACTION-ITEMS.md §6.

---

### Slides 13–19 — Load Scenarios (one slide per scenario, plus one intro slide)

**Each scenario must be described in prose first** — what is happening in the system, not just a
traffic shape label. State clearly which open question(s) that scenario is designed to answer.
Traffic graphs/timelines may support the description but must not replace it.

All scenarios use TopFull's built-in synthetic workload generator (Locust + TopFull scripts from
the paper), not ad-hoc traffic.

**Intro slide (1 slide):**
- Explain that the scenarios are derived directly from the open questions above, not chosen
  independently. Each scenario is an operationalization of one or more specific questions.
- State the shared infrastructure: all scenarios use TopFull's synthetic workload generator.
- Note: RetryGuard's per-service decisions are driven by Istio/Envoy sidecar metrics (HTTP error
  rates read locally at each service) — a separate measurement point from TopFull's entry-proxy
  collectors. Cross-reference both data streams when interpreting results.

**Scenario: Normal Operation (1 slide)**
- Traffic: flat, manageable RPS, well within service capacity — no overload.
- What it tests: does RetryGuard stay entirely non-intrusive when things are healthy? The controller
  should detect rejection rates below the ~20% threshold and leave Istio configurations untouched.
- Answers: the "system-level gains" question from the non-overload side — a necessary sanity check
  before the core experiment.

**Scenario: Sustained Overload — the core experiment (1 slide)**
- Traffic: a load increase that pushes ρ > 1 and holds it there for several minutes — long enough
  for RetryGuard's detection window (~30s consecutive intervals above the rejection threshold) to
  trigger and suppress retries.
- What it tests: TopFull controls admission at the entry. Once admitted, Istio's default retry policy
  fires internally, after TopFull has already admitted the request — invisible to TopFull's rate
  limiter. Does RetryGuard suppress this internal retry amplification, and does that produce
  measurable improvement in goodput or resource usage on top of TopFull alone?
- Answers: system-level gains, topology beneficiaries, chain propagation, controller interaction.

**Scenario: Targeted Bottleneck (1 slide)**
- Traffic: load that exercises the full call chain, while one specific downstream service (e.g.,
  Checkout or a mid-chain service) is constrained — reduced replica count or CPU limit — so it
  reaches ρ > 1 even under TopFull's throttled entry rate.
- What it tests: TopFull detects the overloaded service and throttles APIs routing through it at
  the entry. But after TopFull admits a request, the constrained service may still reject it, and
  its immediate upstream caller (via Istio) retries it — invisible to TopFull. RetryGuard, operating
  per-service with Istio metrics, sees the rejection rate directly at the bottleneck and suppresses
  those internal retries. Does this per-service suppression reduce load at the bottleneck faster and
  more directly than TopFull's top-down throttling? Does the benefit propagate upward?
- Directly analogous to the RetryGuard Bookinfo case study (Reviews service with slow HPA vs.
  Product service with fast HPA, Sec. 6.2 of the RetryGuard paper).
- Answers: topology beneficiaries, chain propagation, controller interaction.

**Scenario: Topology Position Comparison (1 slide)**
- Traffic: three separate Targeted Bottleneck runs — same load, same methodology — varying only
  *where* in the Online Boutique call chain the constrained service sits.
  (1) Gateway-adjacent / shallow sub-tree (e.g., Recommendation or ProductCatalog): called directly
  by Frontend, with few or no downstream dependencies. TopFull's entry-level routing sees this
  bottleneck most directly.
  (2) Hub / sub-tree root (e.g., Checkout): downstream from Frontend but fans out to Cart, Shipping,
  Currency, ProductCatalog, Email, and Payment. Overloading Checkout creates bidirectional retry
  amplification (the widest fan-out case in Online Boutique). Suppressing retries at Checkout
  simultaneously relieves pressure across all its downstream callers.
  (3) Deep leaf (e.g., Email or Payment): no downstream dependencies, reachable only through
  Checkout. TopFull's top-down signal is most attenuated here.
- Answers: topology position sensitivity, topology beneficiaries, chain propagation.

**Scenario: Re-enable Interval Tuning (1 slide)**
- Traffic: the Sustained Overload scenario run multiple times, holding all other parameters constant
  and varying only RetryGuard's re-enable interval (e.g., 10s, 20s, 30s [paper default], 60s).
- What it tests: RetryGuard's Algorithm 1 requires the rejection rate to stay below the threshold
  for `Interval` consecutive measurement periods before re-enabling retries. Too short: risks
  premature re-enabling before the bottleneck has cleared, potentially re-triggering overload.
  Too long: keeps retries suppressed after the bottleneck clears, slowing throughput recovery.
  The paper's 30s default was validated without a co-running top-down controller; with TopFull's
  RL adjusting admission rates every 1 second, recovery dynamics may be faster or more oscillatory.
  Does the optimal interval shift in this context?
- Answers: interval parameter sensitivity, combined equilibrium.

**Scenario: Attack Traffic — extension, given time (1 slide)**
- Traffic: malicious burst-DDoS pattern simulating an attacker exploiting retry amplification.
- What it tests: does hostile traffic trip the controller at the wrong time, or does RetryGuard
  correctly suppress retry storms caused by the attack without disrupting healthy services?
- Answers: adversarial resilience.
- Mark clearly on the slide that this is a time-permitting extension.

Source: PRESENTATION-GUIDE.md §7, PRESENTATION-ACTION-ITEMS.md §7.

---

### Slides 20–21 — Metrics (1–2 slides)

Three layers of measurement, each answering a different part of the question.

**Layer 1 — System & API performance** (TopFull's `metric_collector.py` → CSVs in `logs/`):
- Goodput and latency per API (`getcart`, `getproduct`, `postcheckout`, etc.) — the primary outcome
  metrics. Latency SLO is 1 second (as used in TopFull paper evaluation).
- Rejection rate per API — the signal RetryGuard's controller reads to decide whether to suppress
  retries.
- **Retries per request** — the most direct measure of whether RetryGuard is doing its job.
  Compare against RetryGuard paper Table 1 benchmarks (0.31 → 0.01 for Istio).

**Layer 2 — Infrastructure resource usage** (cAdvisor via `resource_collector.py`):
- CPU consumption and memory limits per pod — tracks whether retry suppression actually frees up
  resources at the service level.
- Pod instance counts over time (`num_instances.csv`) — shows how autoscaling responds under each
  condition and whether over-scaling is prevented (key finding in RetryGuard paper Sec. 6.2).

**Layer 3 — Controller logic & state** (our RetryGuard script logs):
- Which services had retries toggled off and when — ties controller decisions to the topology
  beneficiaries question.
- Time-to-recovery: how long between retry suppression and re-enablement — shows the cool-down
  cycle in practice and is directly relevant to the interval parameter sensitivity question.
- Business priority context from TopFull's `overload_detection.py` — which APIs were flagged as
  overloaded and at what priority, so RetryGuard decisions can be cross-referenced with TopFull's
  state.

All collected data will be synthesized into comparative time-series charts — baseline run vs.
RetryGuard run, side by side across the same metrics.

Source: PRESENTATION-GUIDE.md §8, WORKPLAN.md (key metrics tables),
PRESENTATION-ACTION-ITEMS.md §8.

---

### Slide 22 — Timeline & Milestones (1 slide)

A clean, sequential view of what happens and when. No phase numbers. No blocker callouts.
Dependencies are implied by the order. If a mentor asks about blockers, address them verbally.

| What                                                  | When     |
| ----------------------------------------------------- | -------- |
| Infrastructure setup — VMs, K8s, Istio, app running   | Week 1–2 |
| Baseline experiment — TopFull running, default retries | Week 2–3 |
| RetryGuard implementation and Istio integration       | Week 3   |
| RetryGuard experiment                                 | Week 3–4 |
| Evaluation, comparison, and final report              | Week 4   |

Source: WORKPLAN.md (all phases), PRESENTATION-ACTION-ITEMS.md §9.

---

### Slide 23 (optional) — Summary / Deliverables

- Recap: what we're building, what we're testing, what we'll deliver.
- Deliverables list:
  (1) Working K8s + Istio + TopFull + RetryGuard experimental setup.
  (2) Baseline vs. RetryGuard data across all load scenarios.
  (3) Evaluation report with time-series charts comparing goodput, latency, retries/request,
      resource usage, and autoscaler behavior.
- Open questions for mentors (if any remain after the presentation).

---

### Additional guidelines

**Source discipline — apply to every slide and every speaker note:**
- Ground every bullet point and speaker note strictly in the uploaded source documents.
  Do NOT add content from your own training knowledge that is not present in those documents.
  If a claim cannot be traced to a specific uploaded document and section, omit it.
- Do NOT add slides, sections, or subsections that are not explicitly requested in this prompt.
  The slide structure above is complete — do not insert introduction slides, agenda slides,
  "background" sections, "future work" sections, or any other additions of your own.
- Do NOT add results, benchmarks, or quantitative claims beyond those stated in this prompt
  or present in the uploaded papers. We have no experimental results yet.
- Do NOT reframe or soften the experimental hypotheses or open questions. Use the exact framing
  given — do not add hedges, caveats, or enthusiasm that are not in the source material.

- The deck must work as a **standalone document** — every slide must be understandable without
  someone talking over it. Use clear titles and enough context in bullet points.
- Do NOT include results we don't have. Do NOT promise a live demo.
- Do NOT over-promise extra baselines (DAGOR, DiffTry) unless mentors explicitly expand scope.
- Keep technical detail precise: reference specific paper sections (e.g., "Algorithm 1", "Sec. 6.2",
  "Table 1", "Appendix A") and specific tool names (`metric_collector.py`, `overload_detection.py`,
  `resource_collector.py`, Locust, Istio VirtualService CRD, Kubernetes Python client).
- Use the existing pptx (TAU-workshop -26 retryGuard.pptx) for style and formatting reference only.
- Where PRESENTATION-GUIDE.md says something, prefer its wording and structure over all other
  documents.
- Let the structure carry the rigor: the slide flow itself (open questions → scenarios designed to
  answer them → controlled methodology → defined metrics) communicates scientific credibility.
  The outcome — whether RetryGuard helps a lot, helps only specific services, or barely moves the
  needle — is the point of the work.
```
