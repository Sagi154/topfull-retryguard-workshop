# Action items — project plan presentation (RetryGuard on TopFull)

From mentor meeting **2026-06-04**. Use this when building the slide deck that explains **how you will test RetryGuard** on the TopFull + Online Boutique stack (not a live demo).

Related: [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md) | [WORKPLAN.md](WORKPLAN.md) Phases 5–7 | `Workshop recordings/meeting_transcript.md`

---

## Core narrative

We're integrating RetryGuard with TopFull on a Kubernetes microservice stack and measuring what happens — good or bad — when RetryGuard dynamically toggles retries during overload. The questions are open, the methodology is controlled, and the results will speak for themselves.

---

## Presentation scope (what mentors expect)

- [ ] **Plan, not demo** — Show project plan, milestones, setup, and evaluation approach. Running system is optional; a clear, concrete plan matters more.
- [ ] **Cover the full path** — Ron Nezer's environment setup → TopFull only run → RetryGuard integration → TopFull + RetryGuard comparison → report.
- [ ] **Be concrete on timing** — When each phase closes, what depends on what, and when you need mentor input or budget.
- [ ] **Expect deep questions** — Especially on metrics, workloads, and where RetryGuard hooks into the stack. Slides should answer these before they are asked.

## General slide design rule

- [ ] **Text-first, visuals as support** — Every slide must be understandable from its text alone. Diagrams and charts reinforce an explanation; they do not replace it. If the concept only makes sense by looking at the visual, the slide is missing its explanation.
- [ ] Write the explanation in plain text or bullets first; add a visual only if it makes a clear point easier to follow.
- [ ] No decorative or "atmosphere" visuals that consume space without adding meaning.
- [ ] This applies to all slides, not just the background slides on TopFull and RetryGuard.

---

## Slide / section checklist

### 0. Opening (1 slide)

- [ ] **Project name only:** RetryGuard on TopFull — TAU Communication Networks Workshop
- [ ] **Participants only:** Yoav Binyamin Naaman, Sagi Eisenberg, Ido Zacharia
- [ ] Nothing else on this slide — no plan summary, roles, timeline, or bullets

### 1. Goal and hypothesis

- [ ] One slide: measure **RetryGuard** (self-implemented from the paper) on **TopFull** + **Online Boutique** under overload — where it helps, where it doesn't, and what trade-offs emerge.
- [ ] Hypothesis: dynamic retry control reduces retry storms and protects goodput vs. default retries (align with RetryGuard paper Table 1 style metrics). Present this as the motivating idea, not as a disclaimer.
- [ ] Note: system-wide gain may be small while **specific microservices** show large improvement — plan to surface both.
- [ ] Do **not** add explicit "this is not a sales pitch" or "we don't know yet" lines — the controlled setup and open questions do that work implicitly.

### 2. What is TopFull? / What is RetryGuard? (background slides)

- [ ] **Lead with explanation, not visuals.** Each slide must first answer "what is this system and how does it work?" — the problem it solves + the mechanism. This is the primary content.
- [ ] Key results (benchmark numbers) go at the end as supporting context — compact, not dominant. Do not use large callout numbers or oversized stat blocks as the visual anchor of these slides.
- [ ] For TopFull: cover (1) the local starvation problem, (2) API-wise top-down control, (3) RL-based rate controller. Benchmarks summarized in 2–3 bullets, no big graphical callouts.
- [ ] For RetryGuard: cover (1) retry storms during prolonged miscoordination, (2) how it works in plain language (per-service monitoring → disable retries when rejections stay high → re-enable when recovered — no pseudocode or "Algorithm 1"), (3) distributed, no central orchestrator. Benchmarks summarized in 2–3 bullets, no big graphical callouts.
- [ ] Use 1–2 slides per system — the slide count exists to give room for real explanation, not to add more visuals.

### 3. Stack and topology

- [ ] **Environment:** We will run on **Ron Nezer's existing lab environment** — a pre-provisioned Kubernetes cluster with the TopFull + Online Boutique stack already set up, rather than provisioning new cloud VMs from scratch.
- [ ] Diagram: Locust → TopFull proxy + RL (master) → Istio Envoy sidecars → Online Boutique on workers (keep topology **simple** — mentors said fancy visuals are unnecessary).
- [ ] Show **RetryGuard integration point**: RetryGuard runs on the master node — it reads per-service rejection rates from Istio/Envoy sidecar metrics and dynamically enables or disables retries by updating Istio VirtualService configurations (decided — matches paper Sec. 4).

### 4. How you will test (core of the deck)

> **Slide language note:** Do not use phase numbers (Phase 5, Phase 6, etc.) anywhere on the slides. Use descriptive titles only — **TopFull only**, **TopFull + RetryGuard**, etc. Phase numbers are internal planning references, not audience-facing labels.

#### TopFull only (baseline)

- [ ] Same Locust scenario, duration, and replica counts for every later run.
- [ ] TopFull overload control active; Istio default retries on; RetryGuard **off**.
- [ ] Save CSVs/logs as the TopFull-only reference run.

#### TopFull + RetryGuard (experiment)

- [ ] **Identical** load, topology, and duration; only addition: RetryGuard **on** alongside TopFull.
- [ ] Document controller params from paper Sec. 6.2 (~20% rejection threshold, ~30s measurement interval).

#### Repeated runs

- [ ] Locust generates randomized user behavior (non-deterministic) — a single run per scenario is not sufficient.
- [ ] Run each scenario (**TopFull only** and **TopFull + RetryGuard**) multiple times with the same configuration.
- [ ] Compare results using averages/medians across runs to account for load generator variability.
- [ ] This ensures observed differences are due to RetryGuard, not random variation in traffic patterns.


### 5. What We Want to Find Out (2–3 slides)

This is the intellectual core of the project — give it real space, not a bullet list. Each question needs a full sentence statement and a brief explanation of why it's non-obvious. This section comes **before** the load scenarios because the questions are what motivate the scenarios.

- [ ] **Opening frame (1 slide):** State the central question — does RetryGuard add value on top of TopFull, or is TopFull's overload control already sufficient? Explain why this is genuinely unknown: RetryGuard has been validated in AWS and K8s, but never alongside a sophisticated top-down overload controller like TopFull.
- [ ] **System-level gains** — Does RetryGuard further improve global goodput and latency, or does TopFull already absorb the retry problem at the entry point?
- [ ] **Topology beneficiaries** — Which services benefit most? Do services deeper in the call chain — farther from the entry point where TopFull throttles — respond differently than gateway-adjacent services?
- [ ] **Chain propagation** — If RetryGuard activates on one downstream service, does the benefit propagate up through the rest of the call chain?
- [ ] **Controller interaction** — TopFull's RL controller and RetryGuard are simultaneous feedback loops on overlapping signals. Do they cooperate or interfere? This is unique to the combination and not studied elsewhere.
- [ ] **Combined equilibrium** — When RetryGuard suppresses internal retries at a bottleneck, the bottleneck's load drops and TopFull's RL sees improved signals, potentially increasing its admission rate in response. Does this feedback loop settle at a better stable throughput point, or does the increased admission re-trigger overload and undo the gains?
- [ ] **Topology position sensitivity** — Does the structural position of the bottleneck service change RetryGuard's relative contribution? Compare two positions that differ in **how directly TopFull's entry control reaches them** — not in raw chain depth: a **gateway-adjacent, directly-controlled** service (e.g., ProductCatalog — called directly from Frontend on many entry APIs; TopFull maps and throttles it most directly at entry) vs an **indirect, single-path** service (e.g., Payment — reachable only through Checkout on one API path, so TopFull's signal is mediated by Checkout and most attenuated). RetryGuard operates per-service regardless of position, but the gap between TopFull's entry control and RetryGuard's local action may differ by how directly the bottleneck is exposed to entry control. Note: Online Boutique is a shallow topology, so this contrasts the *directness* of control (direct vs Checkout-mediated), not literal chain depth — state this as a limitation. Not tested alongside a top-down controller like TopFull.
- [ ] **Interval parameter sensitivity** — Is RetryGuard's 30-second re-enable interval optimal when TopFull is co-running? This interval was validated in the original paper (Sec. 6.2) without a simultaneous top-down overload controller. TopFull's RL makes rate-control decisions every 1 second, so the recovery dynamics after overload may be faster or more oscillatory than in the original RetryGuard experiments. Does the optimal interval shift in this context? A shorter interval could allow faster retry recovery once TopFull has stabilized admission; a longer one provides more conservative suppression but delays throughput recovery. There is no established answer for this combination.
- [ ] Each question should be written as a full sentence and briefly explained — not rendered as a grid of labelled boxes or a 2×2 layout.

### 6. Load Scenarios (one slide per scenario, plus an intro slide)

The scenarios follow directly from the open questions above — present them in that order on the slides. Each scenario is explicitly tied to the question(s) it is designed to answer. State that connection clearly on each slide. Given the centrality of this section to the experiment, allocate a dedicated slide to every scenario rather than compressing multiple scenarios onto one slide.

- [ ] **Intro slide:** explain that the scenarios are derived from the open questions above, not chosen independently. State the shared infrastructure: all scenarios use TopFull's **synthetic workload generator** (Locust + TopFull scripts), not ad-hoc traffic. This slide sets up the logic before the individual scenario slides.

- [ ] **Scenario 1 slide: Normal Operation** — flat RPS within capacity. Tests that RetryGuard is non-intrusive when healthy; controller should detect <20% rejections and make zero changes. Answers the "system-level gains" sanity check (baseline side). The slide should describe what is happening in the system in plain language — not just label a traffic shape. Traffic graphs/timelines may support the description but must not replace it.

- [ ] **Scenario 2 slide: Sustained Overload (the core experiment)** — **Setup:** step Locust RPS up until ρ > 1 and hold for 5–10 minutes (long enough for RetryGuard's ~30s windows to fire repeatedly). **What happens:** TopFull throttles entry; admitted requests may still fail downstream; Istio retries internally (invisible to TopFull), creating a retry storm. **Why 5–10 minutes and not 1–2:** the hold must cover RetryGuard's full cycle, not just its trigger — (1) triggering alone takes ~1–2 min because rejections must exceed ~20% for several consecutive ~30s windows, so a short test mostly measures detection latency, not effect; (2) the effect only appears *after* suppression, once load drops and TopFull's 1s RL loop re-settles; (3) 5–10 min lets the disable → recover → re-enable cycle fire repeatedly, proving stable not one-off behavior; (4) it matches RetryGuard's real target — prolonged miscoordination, not brief spikes that default backoff/retry budgets already absorb. **Tests:** TopFull only vs TopFull + RetryGuard — does RetryGuard shut off internal retries and improve goodput or resource usage? Answers: system-level gains, topology beneficiaries, chain propagation, controller interaction.

- [ ] **Scenario 3 slide: Targeted Bottleneck** — full call-chain traffic with one downstream service constrained (reduced replicas or CPU limit) so it reaches ρ > 1 even under TopFull's throttled entry rate. TopFull throttles the APIs routing through it at the entry; Istio retries from the bottleneck's upstream caller are internal and invisible to TopFull. RetryGuard detects the per-service rejection rate and suppresses those retries directly. **How this differs from Sustained Overload (beyond targeting one service):** Sustained Overload saturates the whole system (global ρ > 1), giving an aggregate effect that's hard to attribute; here the stress is *engineered at one node*, so overall load need not exceed total capacity. This exposes a gap global overload can't: relieving one deep service forces TopFull to throttle entire entry APIs (blunt, indirect), while RetryGuard acts surgically at the hot spot — and a single known bottleneck gives clean attribution and lets us watch relief propagate upward. Does this reduce load at the bottleneck faster than TopFull's top-down throttling, and does the benefit propagate up the call chain? Directly analogous to the RetryGuard Bookinfo case study. Answers: topology beneficiaries, chain propagation, controller interaction. The slide should describe what is happening in the system in plain language.

- [ ] **Scenario 4 slide: Topology Position Comparison** — two Targeted Bottleneck runs, same load and constraint method, differing only in **which service** is constrained. **Why separate from Targeted Bottleneck (why not combine):** Targeted Bottleneck establishes *that* per-service suppression helps (varying RetryGuard on/off); this scenario holds that constant and varies only the bottleneck's **position** — changing one variable at a time, so the position effect stays attributable. **Run A — Gateway-adjacent, directly controlled (e.g., ProductCatalog):** Frontend calls it directly on many entry APIs; TopFull maps overload to entry APIs quickly; Istio retries from Frontend still invisible to TopFull after admission. **Run B — Indirect, Checkout-mediated (e.g., Payment):** reachable only via Checkout on a single path (Frontend → Checkout → Payment); TopFull's entry signal is mediated by Checkout and won't throttle the right APIs until Checkout itself fails; Istio retries stack at Checkout→Payment. **Tests:** does RetryGuard matter more when TopFull's entry signal is strong and direct (A) vs indirect and attenuated (B)? **Scope note:** Online Boutique is shallow, so this contrasts *directness* of control and fan-in (one mediated path vs many direct APIs), not literal chain depth — note as a limitation. Answers: topology position sensitivity, topology beneficiaries, chain propagation.

- [ ] **Scenario 5 slide: Re-enable Interval Tuning** — repeat Sustained Overload multiple times; vary only RetryGuard's **re-enable interval** (10s, 20s, 30s \[paper default\], 60s). **What happens:** after RetryGuard disables retries, overload eases and TopFull's RL may admit more traffic; too-short re-enable restarts internal retries before recovery; too-long delays goodput recovery. **Why with TopFull:** paper tuned 30s without a co-running top-down controller; TopFull adjusts admission every ~1s. **Tests:** which interval gives best combined goodput and stability? Answers: interval parameter sensitivity, combined equilibrium.

- [ ] Across all scenario slides: use **TopFull's built-in collectors** (`metric_collector.py`, `overload_detection.py`, `resource_collector.py`) for system-level and API-level metrics. RetryGuard's per-service decisions are driven by Istio/Envoy sidecar metrics — HTTP error rates read locally at each service — which are a separate measurement point from TopFull's entry-proxy collectors. Cross-reference both data streams when interpreting results.

### 7. Metrics (1–2 slides)

Three layers of measurement, each answering a different part of the question.

- [ ] **Layer 1 — System & API performance** (TopFull's `metric_collector.py` → CSVs in `logs/`):
  - Goodput and latency per API (`getcart`, `getproduct`, `postcheckout`, etc.) — the primary outcome metrics.
  - Rejection rate per API — the signal RetryGuard's controller reads to decide whether to suppress retries.
  - **Retries per request** — the most direct measure of whether RetryGuard is doing its job. This is the number to watch when comparing **TopFull only** vs **TopFull + RetryGuard**.
- [ ] **Layer 2 — Infrastructure resource usage** (cAdvisor via `resource_collector.py`):
  - CPU consumption and memory limits per pod — tracks whether retry suppression actually frees up resources at the service level.
  - Pod instance counts over time (`num_instances.csv`) — shows how autoscaling responds under each condition.
- [ ] **Layer 3 — Controller logic & state** (our RetryGuard script logs):
  - Which services had retries toggled off and when — ties controller decisions to the topology beneficiaries question.
  - Time-to-recovery: how long between retry suppression and re-enablement — shows the cool-down cycle in practice.
  - Business priority context from TopFull's `overload_detection.py` — which APIs were flagged as overloaded and at what priority, so RetryGuard decisions can be cross-referenced with TopFull's state.
- [ ] All collected data synthesized into comparative time-series charts for the final evaluation report — **TopFull only** vs **TopFull + RetryGuard**, side by side across the same metrics.

### 8. Milestones and dependencies

- [ ] **No phase numbers on the slide** — phase numbers are internal planning references. The audience doesn't know them and doesn't need to.
- [ ] **No blocker callouts as visual elements** — dependencies are implied by the order of the milestones. If a mentor asks about blockers, address them verbally. Putting them on the slide as warnings makes them the visual focal point, which they shouldn't be.
- [ ] Present a clean, sequential list: what happens and when. That's all the slide needs.

| What | When |
|------|------|
| Infrastructure setup — Ron Nezer's environment, Istio, app running | Week 1–2 |
| Baseline experiment — TopFull only | Week 2–3 |
| RetryGuard implementation and Istio integration | Week 3 |
| Experiment — TopFull + RetryGuard | Week 3–4 |
| Evaluation, comparison, and final report | Week 4 |

- [ ] Fill in actual dates once the project start date is confirmed.

---

## Team tasks (this week)

| # | Task | Suggested owner |
|---|------|-----------------|
| 1 | Draft slide outline from sections above | PM / presenter |
| 2 | Draw simple architecture diagram (Locust → TopFull proxy → Istio/Envoy sidecars → Boutique) | Infra |
| 3 | Write one-page test matrix: TopFull only vs TopFull + RetryGuard, metrics, workloads | Evaluation lead |
| 4 | Confirm access to Ron Nezer's environment; email mentors (Chanok in CC) on presentation format | Infra |
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
