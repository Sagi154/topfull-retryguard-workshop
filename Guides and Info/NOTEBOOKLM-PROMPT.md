# NotebookLM Prompt — Project Plan Slide Deck

Paste this prompt into NotebookLM after uploading the source documents listed below.

---

## Sources to upload

1. `RetryGuard.pdf` — the paper we are implementing (Algorithm 1, Sec. 4, Sec. 6.2; TAU Deepness Lab, arXiv:2511.23278, November 2025)
2. `TopFull.pdf` — the overload-control system (SIGCOMM 2024) we run RetryGuard on top of
3. `TAU-workshop -26 retryGuard.pptx` — existing workshop slide deck (use for style and formatting reference only)
4. `WORKPLAN.md` — full phase-by-phase project plan (Phases 0–7, ~8 days, VM architecture, experiment matrix)
5. `PRESENTATION-GUIDE.md` — **the authoritative slide flow** (10-section structure the deck must follow, including section order)
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

- **Our project:** Self-implement RetryGuard from the RetryGuard paper and evaluate its impact on a
  Kubernetes microservice system running TopFull overload control, on Ron Nezer's existing lab environment.
- **TopFull** (SIGCOMM 2024, KAIST): Top-down, API-wise overload control at the entry point. Uses
  an RL-based rate controller (Sim2Real transfer learning) that adjusts admission rates every
  1 second based on end-to-end goodput and percentile latencies. Solves the starvation problem
  where shared downstream microservices cause some API requests to be partially processed then
  rejected, wasting resources.
- **RetryGuard** (TAU Deepness Lab, 2025): Each microservice has a controller that watches its own health signal (typically HTTP rejection rate from the local Istio/Envoy sidecar). If rejections stay above ~20% for several consecutive ~30-second windows → disable retries for that service only (patch Istio VirtualService). Once below threshold for the same number of windows → re-enable. Distributed — each service decides independently; no central coordinator. Quiet under normal load. Validated on AWS Lambda/DynamoDB and Istio Kubernetes Bookinfo. Do NOT lead slides with pseudocode or "Algorithm 1" — describe behavior in plain language.
- **Integration method:** RetryGuard runs on the master node as a Python script, reads rejection
  signals from Istio/Envoy sidecar metrics (HTTP error rates per service), and patches Istio
  VirtualService retry policies per microservice via the Kubernetes Python client. Matches
  RetryGuard paper Appendix A (Istio integration) and paper Sec. 4 architecture.
- **Test application:** Online Boutique (Google's demo microservice app, 11 microservices including
  Frontend, Checkout, Cart, Productcatalog, Shipping, Currency, Email, Payment, Recommendation, Ad,
  Redis cache). A representative call chain, not the subject of study itself.
- **Infrastructure:** **Ron Nezer's existing lab environment** — a pre-provisioned Kubernetes cluster with TopFull + Online Boutique already set up (Kubernetes 1.26, Istio service mesh, Locust load generator). We are not provisioning new cloud VMs from scratch.

### Section order (follow PRESENTATION-GUIDE.md exactly)

The 10 sections must appear in this order:
0. Opening — project name and participants only
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

Do NOT use phase numbers (Phase 5, Phase 6, etc.) anywhere on slides. Use **TopFull only** and
**TopFull + RetryGuard** — not "The Baseline" / "The Experiment" unless those labels are paired
with the explicit names above. Phase numbers are internal planning references.

---

### Slide 0 — Opening (1 slide)

- **Project name:** RetryGuard on TopFull — TAU Communication Networks Workshop
- **Participants:** Yoav Binyamin Naaman, Sagi Eisenberg, Ido Zacharia
- Nothing else on this slide — no plan summary, roles, timeline, hypothesis, or bullets.
- Source: PRESENTATION-GUIDE.md §0, PRESENTATION-ACTION-ITEMS.md §0.

---

### Slide 1 — Goal and Hypothesis (1 slide)

- One slide: measure RetryGuard (self-implemented from the paper) on TopFull + Online Boutique
  under overload — where it helps, where it doesn't, and what trade-offs emerge.
- **Hypothesis:** dynamic retry control reduces retry storms and protects goodput vs. default retries.
  Present this as the motivating idea (align with RetryGuard paper Table 1 style metrics — retries
  per request, resource billing, rejection rate). This is not a disclaimer.
- Note: system-wide gain may be small while **specific microservices** show large improvement.
  Plan to surface both.
- Deliverables: (1) working TopFull + RetryGuard setup on Ron Nezer's environment,
  (2) TopFull only vs TopFull + RetryGuard experiment data across all scenarios,
  (3) evaluation report with time-series charts comparing performance, resource, and cost metrics.
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

**How RetryGuard works (main content — plain language, no Algorithm 1 or pseudocode):**
- Each microservice has a small controller that watches its own health signal — typically HTTP
  rejection rate (503/429) from the local Istio/Envoy sidecar.
- **When things go bad:** if rejections stay above ~20% for several consecutive ~30-second windows,
  the controller turns off retries for that service only (patches Istio VirtualService).
- **When things recover:** once rejections stay below the threshold for the same number of windows,
  retries are turned back on.
- **Distributed by design:** every service decides independently; no central coordinator.
- **Quiet under normal load:** if rejection rates stay low, the controller never changes anything.
- Istio integration: controller reads sidecar HTTP error rates and patches VirtualService retry
  configs via Kubernetes API. No per-request overhead.

**Key results (TAU Deepness Lab, 2025) — compact, supporting context only:**
- AWS: retries per request from 2.09 → 0.05 (98% reduction); billing from 1029% → 100%.
- Istio/Kubernetes: retries from 0.31 → 0.01/request; billing from 224% → 100%.
- Rejection rate maintained or slightly improved (not sacrificed for cost savings).
- Up to 65% reduction in resource consumption, >90% improvement in latency.
- Also mitigates DDoS amplification — brief burst attacks cannot sustain retry storms.
- Source: RetryGuard.pdf (Sec. 4, Sec. 6.2, Table 1), PRESENTATION-GUIDE.md §3.

---

### Slide 6 — Stack & Topology (1 slide)

- **Environment:** We will run on **Ron Nezer's existing lab environment** — a pre-provisioned
  Kubernetes cluster with the TopFull + Online Boutique stack already set up, rather than
  provisioning new cloud VMs from scratch.
- Simple diagram: Locust → TopFull Go proxy + RL (master) → Istio/Envoy sidecars → Online Boutique
  pods on workers.
- RetryGuard runs on the master node: reads per-service rejection rates from Istio/Envoy sidecar
  metrics and dynamically enables or disables retries by updating Istio VirtualService
  configurations.
- Online Boutique is the test application — a representative microservice call chain (Frontend →
  Checkout → Cart, Shipping, Currency, ProductCatalog, Email, Payment; Frontend also calls
  Recommendation, Ad). Not the subject of study itself.
- Source: PRESENTATION-GUIDE.md §4, PRESENTATION-ACTION-ITEMS.md §3.

---

### Slides 7–9 — How We Test (2–3 slides — core methodology)

**Important slide language note:** Do not use phase numbers. Use descriptive titles only.

**TopFull only (1 slide):**
- TopFull overload control active; Istio default retries on; RetryGuard **off**.
- Fixed workload scenario, duration, and replica counts — identical for every run.
- Save all CSVs and logs as the TopFull-only reference run.

**TopFull + RetryGuard (1 slide):**
- **Identical** load, topology, and duration to TopFull only.
- Only addition: RetryGuard **on** alongside TopFull.
- Controller settings from RetryGuard paper Sec. 6.2: ~20% rejection threshold,
  ~30-second measurement interval.
- RetryGuard implemented as Python script on master node using Kubernetes Python client
  to patch Istio VirtualService CRDs.

**Repeated Runs (1 slide):**
- Locust generates randomized user behavior (non-deterministic) — a single run per scenario is
  insufficient to isolate RetryGuard's effect from random traffic variation.
- Each scenario (**TopFull only** and **TopFull + RetryGuard**) run multiple times with the same
  configuration.
- Results compared using averages/medians across runs.
- Same inputs, two experiment arms, multiple runs → isolates RetryGuard's effect from noise.
- Source: PRESENTATION-GUIDE.md §5, PRESENTATION-ACTION-ITEMS.md §4.

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

- **Topology position sensitivity** — Does the structural position of the bottleneck service change
  RetryGuard's relative contribution? Compare two positions that differ in **how directly TopFull's
  entry control reaches them** — not in raw chain depth:
  (1) **Gateway-adjacent, directly controlled** (e.g., ProductCatalog): called directly from Frontend
  on many entry APIs; TopFull maps and throttles this bottleneck most directly at entry.
  (2) **Indirect, single-path** (e.g., Payment): reachable only through Checkout on one API path, so
  TopFull's top-down signal is mediated by Checkout and most attenuated. RetryGuard operates
  per-service regardless of position, but the gap between TopFull's entry control and RetryGuard's
  local action may differ by how directly the bottleneck is exposed to that entry control.
  Note: Online Boutique is a shallow topology, so this contrasts the *directness* of control
  (direct vs Checkout-mediated), not literal chain depth.

- **Interval parameter sensitivity** — Is RetryGuard's 30-second re-enable interval optimal when
  TopFull is co-running? This interval was validated in the original paper (Sec. 6.2) without a
  simultaneous top-down overload controller. TopFull's RL makes rate-control decisions every 1 second,
  so the recovery dynamics after overload may be faster or more oscillatory than in the original
  RetryGuard experiments. Does the optimal interval shift in this context?

Source: PRESENTATION-GUIDE.md §6, PRESENTATION-ACTION-ITEMS.md §5.

---

### Slides 13–18 — Load Scenarios (one slide per scenario, plus one intro slide)

**Each scenario MUST be its own dedicated, separately numbered slide.** Do NOT combine two or more
scenarios onto a single slide, and do NOT merge a scenario with the intro slide. There are exactly
6 slides in this section — 1 intro slide followed by 5 scenario slides — and each must carry its own
slide number and title (Slide 13 through Slide 18, as numbered below). Reproduce the slide numbers
in the output.

**Each scenario must be described in prose first** — what is happening in the system, not just a
traffic shape label. State clearly which open question(s) that scenario is designed to answer.
Traffic graphs/timelines may support the description but must not replace it.

All scenarios use TopFull's built-in synthetic workload generator (Locust + TopFull scripts from
the paper), not ad-hoc traffic.

**Slide 13 — Scenarios Intro (1 slide):**
- Explain that the scenarios are derived directly from the open questions above, not chosen
  independently. Each scenario is an operationalization of one or more specific questions.
- State the shared infrastructure: all scenarios use TopFull's synthetic workload generator.
- Note: RetryGuard's per-service decisions are driven by Istio/Envoy sidecar metrics (HTTP error
  rates read locally at each service) — a separate measurement point from TopFull's entry-proxy
  collectors. Cross-reference both data streams when interpreting results.

**Slide 14 — Scenario 1: Normal Operation (1 slide)**
- Traffic: flat, manageable RPS, well within service capacity — no overload.
- What it tests: does RetryGuard stay entirely non-intrusive when things are healthy? The controller
  should detect rejection rates below the ~20% threshold and leave Istio configurations untouched.
- Answers: the "system-level gains" question from the non-overload side — a necessary sanity check
  before the core experiment.

**Slide 15 — Scenario 2: Sustained Overload — the core experiment (1 slide)**
- **Setup:** Start from Normal Operation traffic, then step Locust RPS up until ρ > 1 and **hold
  for 5–10 minutes** — long enough for RetryGuard's ~30s measurement windows to fire repeatedly.
- **What happens in the system:** TopFull throttles entry; admitted requests may still fail
  downstream (503/429); Istio retries internally — invisible to TopFull's rate limiter — creating
  a retry storm where one user request generates multiple backend attempts.
- **Why duration matters — why 5–10 minutes, not 1–2:** the hold must cover RetryGuard's full
  reaction *cycle*, not just its trigger. (1) Triggering alone costs ~1–2 minutes, since rejections
  must stay above ~20% for several consecutive ~30s windows — a short test mostly measures detection
  latency, not effect, and often the load drops before the windows confirm. (2) The effect only
  appears *after* suppression: load drops, TopFull's 1s RL loop reacts to improved signals, and the
  system re-settles. (3) 5–10 minutes lets the disable → recover → re-enable cycle fire repeatedly,
  proving stable rather than one-off behavior. (4) It matches RetryGuard's real target — prolonged
  miscoordination, not brief spikes that default backoff, jitter, and retry budgets already absorb.
- **What it tests:** TopFull only vs TopFull + RetryGuard — does RetryGuard detect high rejection
  rates and shut off internal retries, improving goodput or resource usage?
- Answers: system-level gains, topology beneficiaries, chain propagation, controller interaction.

**Slide 16 — Scenario 3: Targeted Bottleneck (1 slide)**
- Traffic: load that exercises the full call chain, while one specific downstream service (e.g.,
  Checkout or a mid-chain service) is constrained — reduced replica count or CPU limit — so it
  reaches ρ > 1 even under TopFull's throttled entry rate.
- **How this differs from Sustained Overload (beyond targeting one service):** Sustained Overload
  saturates the whole system by flooding the entry (global ρ > 1), giving an aggregate effect that
  is hard to attribute. Here the overall load need not exceed total capacity — the stress is
  *engineered at one node*. This exposes a gap global overload cannot: relieving one deep service
  forces TopFull to throttle entire entry APIs that route through it (blunt and indirect), while
  RetryGuard acts surgically at the exact hot spot — and a single known bottleneck gives clean
  attribution and lets us watch whether relief propagates upward.
- What it tests: TopFull detects the overloaded service and throttles APIs routing through it at
  the entry. But after TopFull admits a request, the constrained service may still reject it, and
  its immediate upstream caller (via Istio) retries it — invisible to TopFull. RetryGuard, operating
  per-service with Istio metrics, sees the rejection rate directly at the bottleneck and suppresses
  those internal retries. Does this per-service suppression reduce load at the bottleneck faster and
  more directly than TopFull's top-down throttling? Does the benefit propagate upward?
- Directly analogous to the RetryGuard Bookinfo case study (Reviews service with slow HPA vs.
  Product service with fast HPA, Sec. 6.2 of the RetryGuard paper).
- Answers: topology beneficiaries, chain propagation, controller interaction.

**Slide 17 — Scenario 4: Topology Position Comparison (1 slide)**
- **Setup:** Two Targeted Bottleneck runs — same Locust load and constraint method — differing
  only in **which service** is constrained.
- **Why separate from Targeted Bottleneck (why not combine):** Targeted Bottleneck establishes
  *that* per-service suppression helps (varying RetryGuard on/off); this scenario holds that constant
  and varies only the bottleneck's **position**. Changing one variable at a time keeps the position
  effect attributable — combining them would entangle "does RetryGuard help" with "does position
  matter."
- **Run A — Gateway-adjacent, directly controlled (e.g., ProductCatalog):** Frontend calls it
  directly on many product-browse paths; TopFull maps overload to entry APIs quickly; Istio retries
  from Frontend still invisible to TopFull after admission.
- **Run B — Indirect, Checkout-mediated (e.g., Payment):** reachable only via Checkout on a single
  path (Frontend → Checkout → Payment); TopFull's entry signal is mediated by Checkout and won't
  throttle the right APIs until Checkout itself fails; Istio retries stack at Checkout→Payment.
- **What it tests:** Does RetryGuard's per-service suppression matter more when TopFull's entry
  signal is strong and direct (Run A) vs indirect and attenuated (Run B)? Do savings propagate
  differently up the chain?
- **Scope note:** Online Boutique is a shallow topology, so this contrasts the *directness* of
  TopFull's control and fan-in (one mediated path vs many direct entry APIs), not literal chain
  depth — state this as a limitation in the report.
- Answers: topology position sensitivity, topology beneficiaries, chain propagation.

**Slide 18 — Scenario 5: Re-enable Interval Tuning (1 slide)**
- **Setup:** Repeat Sustained Overload multiple times; keep load, replicas, and threshold fixed;
  vary only RetryGuard's **re-enable interval** (10s, 20s, 30s [paper default], 60s).
- **What happens:** After RetryGuard disables retries, overload eases; TopFull's RL may admit more
  traffic. Too-short re-enable restarts internal retries before recovery; too-long delays goodput
  recovery. Paper tuned 30s without a co-running top-down controller; TopFull adjusts admission
  every ~1 second.
- **What it tests:** Which re-enable interval gives the best combined goodput and stability when
  TopFull and RetryGuard run together?
- Answers: interval parameter sensitivity, combined equilibrium.

Source: PRESENTATION-GUIDE.md §7, PRESENTATION-ACTION-ITEMS.md §6.

---

### Slides 19–20 — Metrics (1–2 slides)

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

All collected data will be synthesized into comparative time-series charts — **TopFull only** vs
**TopFull + RetryGuard**, side by side across the same metrics.

Source: PRESENTATION-GUIDE.md §8, PRESENTATION-ACTION-ITEMS.md §7.

---

### Slide 21 — Timeline & Milestones (1 slide)

A clean, sequential view of what happens and when. No phase numbers. No blocker callouts.
Dependencies are implied by the order. If a mentor asks about blockers, address them verbally.

| What                                                  | When     |
| ----------------------------------------------------- | -------- |
| Infrastructure setup — Ron Nezer's environment, Istio, app running | Week 1–2 |
| Baseline experiment — TopFull only                              | Week 2–3 |
| RetryGuard implementation and Istio integration                 | Week 3   |
| Experiment — TopFull + RetryGuard                               | Week 3–4 |
| Evaluation, comparison, and final report                        | Week 4   |

Source: PRESENTATION-GUIDE.md §9, PRESENTATION-ACTION-ITEMS.md §8.

---

### Slide 22 (optional) — Summary / Deliverables

- Recap: what we're building, what we're testing, what we'll deliver.
- Deliverables list:
  (1) Working TopFull + RetryGuard setup on Ron Nezer's environment.
  (2) TopFull only vs TopFull + RetryGuard data across all load scenarios.
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
  The slide structure above is complete — do not insert agenda slides, extra introduction content
  on the opening slide, "background" sections, "future work" sections, or any other additions
  of your own. The opening slide (Slide 0) must contain **only** the project name and participant
  names — nothing else.
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
