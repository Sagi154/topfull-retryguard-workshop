# Coordinate with mentors (before Phase 1)

Ask your mentors these **before** you create cloud VMs (Phase 1). One short meeting or message thread is enough.

Related: [PREREQUISITES.md](PREREQUISITES.md) | [SETUP-GUIDE.md](SETUP-GUIDE.md) Phase 0 | [WORKPLAN.md](WORKPLAN.md) | [PRESENTATION-ACTION-ITEMS.md](PRESENTATION-ACTION-ITEMS.md) | workplan canvas (`canvases/topfull-retryguard-workplan.canvas.tsx`)

---

## Checklist

- [x] **Cloud credits** — Student **GCP credits (~$300)** discussed; confirm lab top-up or shared billing with mentors before spend.
- [ ] **Cloud provider** — **GCP** favored in meeting; TopFull docs default to Azure — confirm mentors accept GCP + Terraform private instances.
- [ ] **VM budget & timeline** — Start **minimal footprint** (~3 modules / fewer nodes); scale only if needed. Estimate ~5 nodes × limited hours/day; **deallocate when idle**.
- [x] **RetryGuard integration point** — **Istio VirtualService retry policies** per service (decided — matches paper Sec. 4).
- [ ] **Report expectations** — Confirm required plots: goodput, latency, retries/request, **system-level and per-microservice**, plus cross-service impact.

---

## Decisions from mentor meeting (2026-06-04)

Source: WhatsApp voice notes in `Workshop recordings/` (see `meeting_transcript.md`). Full transcript quality varies; treat this section as the team summary.

### Presentation (upcoming)

- Present the **project plan**, not a live demo: milestones, setup, how you will test RetryGuard on TopFull, and when phases close.
- Slide deck is fine; tone can be informal, but content should show you know **next steps** and dependencies.
- Mentors may ask detailed questions — especially Alon — on metrics, workloads, and integration.

### Evaluation strategy

- Measure RetryGuard at **two levels**: (1) **whole-system** goodput/latency/retries, and (2) **specific microservices** where it helps or has no effect.
- Consider starting with **edge/extreme cases** (where TopFull already acts vs. where RetryGuard adds value), then **generic daily traffic** — system gain may be small (~0.2%) while a specific microservice improves a lot (~30%); find bottleneck services where RetryGuard does nothing.
- Use **TopFull topology** to explain *where* RetryGuard changes behavior; keep the diagram simple.
- **RetryGuard implementation** can be simple (e.g. controller reads state, sends more/less retry commands) — no need for a heavy or fancy design; mentors do not expect it to consume meaningful resources or hurt other services.
- **Baseline vs experiment** must use the **same** Locust scenario; only retry policy changes (Phase 5 → Phase 6).

### Workloads and overload

- Use TopFull’s **synthetic workload generator** (same deployment / load / autoscaling as the paper) for apples-to-apples comparison.
- Plan **at least two load types**: (A) RetryGuard should **not** help, (B) RetryGuard **should** help — plus cases where RetryGuard runs but **fails** at specific microservice boundaries.
- **RetryGuard reacts faster than TopFull** (local vs. system-wide); design scenarios for: no overload, overload where RetryGuard should fire, and overload where RetryGuard is active but ineffective (after TopFull also engages).
- TopFull’s traffic model should create **periodic overload** (not flat load); coordinate **two overload scenarios** with mentors.
- Under sustained failure: after **X seconds** of retries/latency/rejections, **stop retrying**, wait, then retry — model chain effects across microservices.
- Use **TopFull’s built-in collectors** (`metric_collector.py`, `overload_detection.py`) for metrics — no need for a separate Prometheus deployment.

### Infrastructure

- **Do not rely on local laptops** for the full stack — local VM simulation needs a very powerful machine; mentors were skeptical. **GCP is the practical path**; note Azure/AWS as alternatives if lab prefers.
- **GCP**: ~**$300 student credits**; mentor estimate **$5–15/day** for the K8s app stack; runs are a **few days**, not weeks. Email mentors (include **Chanok** in CC) to confirm setup and which GCP configuration they recommend (another student group is on similar work).
- **Start small**, request extra budget only with justification after initial modules run.

### Security

- Treat **security** as an explicit workstream (access, cluster exposure) — mentors flagged it alongside topology and overload behavior.

### People / follow-up

- Loop in mentors on GCP access, budget, and recommended **next steps** before heavy spend (same email thread as GCP questions).
- **Technical Q&A**: prefer an **email thread with Itai** for day-to-day questions rather than waiting for meetings.
- **Next meeting**: when you hit a **decision point** (e.g. setup done, unsure how to integrate RetryGuard), not on a fixed schedule.
- **Ron** (prior student) may have reusable code — mentor will ask him; don’t assume it will be shared.
- Share presentation outline early if mentors want to steer content before the meeting.

---

## Notes

**RetryGuard code:** You implement Algorithm 1 from `RetryGuard.pdf` — mentors do not need to give you source. The integration point is **Istio VirtualService retry policies** (controller patches `retries.attempts` per service via Kubernetes API, matching paper Sec. 4).

**Baseline vs experiment:** Confirm both runs use the same Locust scenario; only retry policy changes (Phase 5 baseline -> Phase 6 RetryGuard).

**Out of scope unless mentors say otherwise:** DAGOR, DiffTry, extra overload-control baselines.

**Per-microservice analysis:** Mentors want to know not only whether system metrics improve, but **which** microservices benefit and under which overload conditions.

---

## Suggested message to mentors

> We're preparing the project plan presentation for testing RetryGuard on TopFull + Online Boutique. We'll show milestones, VM/K8s setup, baseline (Phase 5) vs RetryGuard (Phase 6) experiments, and metrics at system and per-microservice level. We propose using **Istio VirtualService retry policies** as the RetryGuard integration point — this matches the paper's architecture (Sec. 4) and gives us per-service retry control at the mesh level. Before we provision GCP: can you confirm student credits / lab billing, preferred overload scenarios, and approve the Istio approach (any guidance on version compatibility with K8s 1.26)? We'll start with a minimal cluster and scale only if needed.
