# NotebookLM Prompt — Project Plan Slide Deck

Paste this prompt into NotebookLM after uploading the source documents listed below.

---

## Sources to upload

1. `RetryGuard.pdf` — the paper we are implementing (Algorithm 1, Sec. 4, Sec. 6.2)
2. `TopFull.pdf` — the overload-control system (SIGCOMM 2024) we run RetryGuard on top of
3. `TAU-workshop -26 retryGuard.pptx` — existing workshop slide deck (use for style/formatting reference only)
4. `WORKPLAN.md` — full phase-by-phase project plan (Phases 0–7, ~8 days, VM architecture, experiment matrix)
5. `PRESENTATION-GUIDE.md` — **the authoritative slide flow** (9-section structure the deck must follow)
6. `PRESENTATION-ACTION-ITEMS.md` — slide checklist, mentor expectations, team tasks
7. `SETUP-GUIDE.md` — detailed step-by-step setup instructions for the full stack
8. TopFull GitHub repo README: https://github.com/kaist-ina/TopFull/tree/main

---

## Prompt

```
You are helping a student team at Workshop in Communication Networks and Information Security build a **project plan presentation** (slide deck). This is NOT a results talk — it presents how we plan to test RetryGuard on a TopFull Kubernetes microservice setup. We have no results yet.

### Audience and purpose

Our professor said (translated): "I want to understand what you are going to do in the project and what the deliverables will be. This is an expectations alignment. If the document is clear enough, it can stand on its own without a meeting."

This means:
- The deck MUST be **self-explanatory** — it may be reviewed as a standalone document, without us presenting it live.
- The focus is: **what we will do**, **how we will do it**, and **what the deliverables are**.
- Clarity and concreteness matter more than flashy visuals.
- Tone: this is an **experiment**, not a sales pitch. We don't assume RetryGuard works — we design a rigorous test and present whatever we find.

### Project summary

- **Our project:** Self-implement RetryGuard (Algorithm 1 from the RetryGuard paper) and evaluate its impact on a Kubernetes microservice system running TopFull overload control.
- **TopFull** (SIGCOMM 2024): Top-down, API-wise overload control that uses RL-based rate limiting at the entry point. It solves the starvation problem where shared downstream microservices cause some API requests to get partially processed and then rejected.
- **RetryGuard** (TAU Deepness Lab, 2025): A productive-retry controller that monitors rejection rates per service and dynamically disables retries during prolonged overload to prevent retry storms (snowball of wasted resources, inflated costs, degraded performance).
- **Integration method:** RetryGuard runs on the master node, reads overload signals from TopFull's collectors, and toggles Istio VirtualService retry policies per microservice (matching RetryGuard paper Sec. 4 architecture).
- **Test application:** Online Boutique (Google's demo microservice app) — a representative call chain, not the subject of study itself.
- **Infrastructure:** 4–7 cloud VMs (Ubuntu 20.04), Kubernetes 1.26, Istio service mesh, Calico CNI, cAdvisor, Locust load generator.

### Slide structure to follow

Follow the **PRESENTATION-GUIDE.md** structure exactly. The deck should have ~12–15 content slides (suitable for a 30-minute presentation or standalone reading). For each slide, produce:
1. A short slide title
2. Concise bullet points / content for the slide
3. Speaker notes (what to say or what a reader should understand)
4. Source reference (which uploaded document and section the content comes from)

Here are the 9 sections:

**Slide 1 — Project Goal** (1 slide)
- Evaluate RetryGuard's impact on a microservice system running TopFull overload control.
- Frame as: "Not proving it works — designing an experiment that reveals where it helps, where it doesn't, and what trade-offs emerge."
- Based on RetryGuard's algorithm (self-implemented from the paper), integrated via Istio service mesh.
- State what the deliverables are: a working experimental setup, baseline and RetryGuard comparison data, and an evaluation report with charts/graphs.
- Source: PRESENTATION-GUIDE.md §1, PRESENTATION-ACTION-ITEMS.md §1.

**Slides 2–3 — What is TopFull?** (1–2 slides)
- The problem: existing overload controls manage individual microservices in isolation → starvation when APIs share overloaded services.
- How TopFull solves it: top-down API-wise load control at the entry point, clusters interdependent APIs, RL-based rate controller using Sim2Real transfer learning.
- Key results from the SIGCOMM 2024 paper: 1.82x more goodput than DAGOR, 2.26x more than Breakwater, converges in 5 seconds, tolerates spikes with 57% fewer resources.
- Source: TopFull.pdf, PRESENTATION-GUIDE.md §2.

**Slides 4–5 — What is RetryGuard?** (1–2 slides)
- The problem: default retries (exponential backoff, jitter, budgets) fail during prolonged miscoordination → retry storms → resource waste, cost inflation (Denial-of-Wallet), performance degradation.
- How RetryGuard works: monitors rejection rate per service; if rejections exceed ~20% for N consecutive ~30s intervals → disable retries; if below threshold → re-enable. Distributed, non-intrusive under normal conditions.
- Key results: AWS: 98% reduction in retry attempts, billing from 1029% to 100%. Istio/K8s: retries from 0.31 to 0.01/request, billing from 224% to 100%. Up to 65% reduction in resource consumption, 90% latency improvement.
- Source: RetryGuard.pdf (Algorithm 1, Sec. 4, Sec. 6.2), PRESENTATION-GUIDE.md §3.

**Slide 6 — Stack & Topology** (1 slide)
- Architecture diagram (describe for the slide): Locust (load-gen VM) → Go proxy (master) → Istio/Envoy sidecars → Online Boutique microservices (worker VMs).
- RetryGuard runs on the master node: monitors TopFull's overload signals, patches Istio VirtualService retry configs per service in real time.
- VM roles: Master (8+ vCPU, 16GB — K8s control plane, Istio, TopFull, RetryGuard), Workers 2–5 (pods, cAdvisor), Load-gen 1 (Locust only).
- Cloud provider: GCP with ~$300 student credits. Cost: ~$5–15/day. Start minimal (3 nodes), scale if needed. Deallocate when idle.
- Source: WORKPLAN.md (VM architecture table), PRESENTATION-GUIDE.md §4, PRESENTATION-ACTION-ITEMS.md §2–3.

**Slides 7–9 — How We Test** (2–3 slides — core of the deck)
This is the most important section. Be very concrete.

*Slide 7 — Baseline experiment (Phase 5):*
- TopFull running, retries ON (default), RetryGuard OFF.
- Fixed workload scenario, duration, and replica counts — same for every run.
- Save all CSVs/logs as baseline artifacts.

*Slide 8 — RetryGuard experiment (Phase 6):*
- Identical setup, only change: RetryGuard ON.
- Controller params from RetryGuard paper Sec. 6.2 (~20% rejection threshold, ~30s monitoring interval).
- RetryGuard implemented as Python script on master, uses Kubernetes Python client to patch Istio VirtualService CRDs.

*Slide 9 — Repeated runs & comparison:*
- Locust generates randomized user behavior (non-deterministic) — single run per scenario is insufficient.
- Each scenario run multiple times with identical configuration.
- Results compared using averages/medians across runs to account for load-generator variability.
- Same inputs, different retry behavior, multiple runs → isolates RetryGuard's effect from noise.
- Source: PRESENTATION-GUIDE.md §5, WORKPLAN.md Phases 5–6, PRESENTATION-ACTION-ITEMS.md §4.

**Slides 10–11 — Workloads & Scenarios** (1–2 slides)
- Two primary load scenarios:
  (1) **No overload** — does RetryGuard stay out of the way when things are normal?
  (2) **Expected overload** — periodic overload (TopFull-style), does RetryGuard improve the situation?
- Future exploration (given time): **malicious/attack traffic** — does hostile traffic cause RetryGuard to trigger at the wrong time?
- All workloads driven by TopFull's synthetic workload generator (Locust + TopFull scripts from the paper), not ad-hoc traffic.
- Source: PRESENTATION-GUIDE.md §6, PRESENTATION-ACTION-ITEMS.md §5–6.

**Slide 12 — What We Want to Find Out** (1 slide — the experimental questions)
- Frame explicitly: "We don't know these answers yet. That's what we're testing."
- Questions:
  1. Does adding RetryGuard on top of TopFull further improve goodput and latency during overload, or is TopFull already sufficient?
  2. Which types of services in the call chain benefit? Are leaf services affected differently than gateways?
  3. Does RetryGuard's effect on one service propagate to others through the call chain?
  4. (Given time) How does RetryGuard behave under adversarial conditions?
- Source: PRESENTATION-GUIDE.md §7.

**Slide 13 — Metrics** (1 slide)
- Built-in from TopFull's collectors:
  | Level | What | Source |
  |-------|------|--------|
  | Per-API performance | Goodput, latency, rejection rate per API | metric_collector.py → CSVs |
  | Resource usage | CPU/memory per pod | resource_collector.py → cAdvisor |
  | Replica counts | Pod counts over time | num_instances.csv |
  | Overload state | Which APIs are overloaded, priority | overload_detection.py |
- We build/log ourselves:
  | RetryGuard decisions | When it fires, which services toggled, time to recovery | RetryGuard script logs |
- Results presented with charts and graphs.
- Source: PRESENTATION-GUIDE.md §8, WORKPLAN.md (key metrics tables).

**Slide 14 — Timeline & Milestones** (1 slide)
- Phase-by-phase timeline from WORKPLAN.md:
  | Phase | Milestone | Target |
  |-------|-----------|--------|
  | 0 | Preparation & accounts | Day 1 |
  | 1 | Provision cloud VMs | Day 1–2 |
  | 2 | Kubernetes cluster setup + Istio | Day 2–3 |
  | 3 | Install dependencies | Day 3–4 |
  | 4 | Configure and deploy Online Boutique | Day 4–5 |
  | 5 | Baseline experiment (TopFull only) | Day 5–6 |
  | 6 | RetryGuard implementation + experiment | Day 6–8 |
  | 7 | Evaluation and comparison report | Day 8–9 |
- Highlight dependencies: each phase requires the previous one to complete.
- Source: WORKPLAN.md (all phases), PRESENTATION-ACTION-ITEMS.md §7.

**Slide 15 (optional) — Summary / Next Steps**
- Recap: what we're building, what we're testing, and what we'll deliver.
- Deliverables list: (1) working K8s + TopFull + RetryGuard setup, (2) baseline vs. RetryGuard experiment data, (3) evaluation report with charts comparing performance/cost metrics.
- Open questions for mentors (if any remain).

### Additional guidelines

- The deck must work as a **standalone document** — every slide should be understandable without someone talking over it. Use clear titles and enough context in bullet points.
- Do NOT include results we don't have. Do NOT promise a live demo.
- Do NOT over-promise extra baselines (DAGOR, DiffTry) unless mentors expand scope.
- Keep technical detail precise: reference specific paper sections (e.g., "Algorithm 1", "Sec. 6.2", "Table 1") and specific tool names (metric_collector.py, Locust, Istio VirtualService).
- Use the existing pptx (TAU-workshop -26 retryGuard.pptx) for style and formatting reference only.
- Where the PRESENTATION-GUIDE.md says something, prefer its wording and structure over other documents.
- End with the key tone from PRESENTATION-GUIDE.md: "This is an experiment, not a sales pitch. The results might show RetryGuard helps a lot, helps only specific services, or barely helps at all — all of those are valid findings."
```
