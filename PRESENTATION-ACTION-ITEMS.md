# Action items — project plan presentation (RetryGuard on TopFull)

From mentor meeting **2026-06-04**. Use this when building the slide deck that explains **how you will test RetryGuard** on the TopFull + Online Boutique stack (not a live demo).

Related: [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md) | [WORKPLAN.md](WORKPLAN.md) Phases 5–7 | `Workshop recordings/meeting_transcript.md`

---

## Presentation scope (what mentors expect)

- [ ] **Plan, not demo** — Show project plan, milestones, setup, and evaluation approach. Running system is optional; clarity of the test plan matters more.
- [ ] **Cover the full path** — VM/K8s setup → TopFull baseline run → RetryGuard integration → comparison → report.
- [ ] **Be concrete on timing** — When each phase closes, what depends on what, and when you need mentor input or budget.
- [ ] **Expect deep questions** — Especially on metrics, workloads, and where RetryGuard hooks into the stack. Slides should answer these before they are asked.

---

## Slide / section checklist

### 1. Goal and hypothesis

- [ ] One slide: evaluate **RetryGuard** (self-implemented from the paper) on **TopFull** + **Online Boutique** under overload.
- [ ] State hypothesis: dynamic retry control reduces retry storms / protects goodput vs. default retries (align with RetryGuard paper Table 1 style metrics).
- [ ] Note: system-wide gain may be small while **specific microservices** show large improvement — plan to find both.

### 2. Stack and topology

- [ ] Diagram: Locust → TopFull proxy + RL (master) → Istio Envoy sidecars → Online Boutique on workers (keep topology **simple** — mentors said fancy visuals are unnecessary).
- [ ] List VM roles (master, 2–5 workers, loadgen) and min specs from [WORKPLAN.md](WORKPLAN.md). Note: master also runs Istio control plane.
- [ ] Show **RetryGuard integration point**: Istio VirtualService retry policies per service (decided — matches paper Sec. 4).

### 3. Cloud and budget

- [ ] Provider plan: **GCP** with student credits (~$300) was discussed; confirm with mentors (Alon / Chanok) before provisioning.
- [ ] Cost model: ~4–7 VMs, estimate hours/day and deallocate-when-idle policy.
- [ ] **Start minimal** (e.g. 3-node / smaller footprint), scale only if experiments require it; request extra budget only with justification.

### 4. How you will test (core of the deck)

#### Baseline (Phase 5)

- [ ] Same Locust scenario, duration, and replica counts for every later run.
- [ ] TopFull running; retries at **default (on)**; RetryGuard **off**.
- [ ] Save CSVs/logs to `baseline_topfull_no_retryguard`.

#### Experiment (Phase 6)

- [ ] **Identical** load and topology; only change: RetryGuard **on**.
- [ ] Document controller params from paper Sec. 6.2 (~20% threshold, ~30s interval).

#### Metrics — system **and** per-microservice

- [ ] **System-level:** goodput, latency, retries/request, overload indicators (mentors want both global score and local insight).
- [ ] **Per-microservice:** where RetryGuard helps vs. does nothing — tie to topology / specific services.
- [ ] **Cross-service propagation:** measure whether RetryGuard’s effect on one service **propagates** to other services in the call chain (if any).
- [ ] Results will be presented in a clear manner with charts, graphs, and dashboards.

### 5. Workloads and scenarios

- [ ] Use TopFull’s **synthetic workload generator** (same framework as the paper) — Locust + TopFull scripts, not ad-hoc traffic.
- [ ] **Two scenarios (decided):** (1) **no overload** — verify RetryGuard does not interfere with normal operation; (2) **expected overload** — measure RetryGuard’s effect when overload occurs (the core experiment).
- [ ] Traffic must create **periodic overload** (TopFull-style), not flat RPS.
- [ ] Overload detection: sustained retries, latency, or rejections for **X seconds** → stop retrying → cool-down → retry again; show effect on **call chains**.
- [ ] Use **TopFull’s built-in collectors** (`metric_collector.py`, `overload_detection.py`, `resource_collector.py`) for metrics. Map per-API rejection rates to downstream services for RetryGuard decisions.

### 6. Security scenarios (brief slide)

- [ ] Include a scenario with **malicious / attack traffic** targeting the services — measure how it affects RetryGuard’s effectiveness and overall system behavior.
- [ ] Note: full stack is **not** expected to run on laptops; cloud VMs are the real environment.

### 7. Milestones and dependencies

| Milestone | Owner | Target | Blocked by |
|-----------|-------|--------|------------|
| Mentor alignment (integration point, budget) | Team | Before Phase 1 | GCP access confirmation |
| VMs + K8s + Online Boutique up | Team | Phase 1–4 | Credits, SSH, networking |
| Baseline experiment (Phase 5) | Team | Day 5–6 | Stable cluster + metrics |
| RetryGuard implementation + Istio VirtualService hook | Team | Phase 6a–6b | Istio installed + mentor approval |
| RetryGuard experiment (Phase 6d) | Team | Day 6–8 | Baseline artifacts saved |
| Report + comparison (Phase 7) | Team | Day 8–9 | Both result sets |

- [ ] Fill in names and dates for your team.

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
| 7 | Rehearse Q&A: “where does RetryGuard sit?” and “how do you know it helped?” | Whole team |

---

## What *not* to promise in the presentation

- Live cluster demo (unless already stable).
- Extra baselines (DAGOR, DiffTry) unless mentors explicitly expand scope.
- Perfect Hebrew/English transcript of the meeting — use [MENTOR-COORDINATION.md](MENTOR-COORDINATION.md) and this file as the source of truth.
