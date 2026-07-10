# Gemini Prompt — RetryGuard on TopFull Slide Deck (visual-rich)

Use this prompt with **Gemini** (Gemini app, Gemini in Google Slides, or Gemini Canvas) to generate the
project-plan slide deck. It is the visual-first companion to `NOTEBOOKLM-PROMPT.md`: same content and
section order, but with an **explicit visual specification for every slide** so Gemini produces purposeful
diagrams and charts instead of generic stock photos or empty slides.

---

## Why this prompt exists

Gemini tends to skip visuals or drop in decorative stock imagery when a prompt only describes text. This
prompt fixes that by telling Gemini, for each slide, **exactly what diagram or chart to draw, what each
element represents, and how to lay it out**. Treat every `VISUAL:` block below as a direct instruction to
generate that specific graphic on that slide.

---

## Sources to attach (upload to Gemini if supported)

1. `RetryGuard.pdf` — the paper we implement (Algorithm 1, Sec. 4, Sec. 6.2; TAU Deepness Lab, arXiv:2511.23278, Nov 2025).
2. `TopFull.pdf` — the overload-control system (SIGCOMM 2024) RetryGuard runs on top of.
3. `TAU-workshop -26 retryGuard.pptx` — existing deck (style/formatting reference only).
4. `PRESENTATION-GUIDE.md` — the authoritative slide flow and section order.
5. `PRESENTATION-ACTION-ITEMS.md` — slide checklist and mentor expectations.
6. `NOTEBOOKLM-PROMPT.md` — the detailed per-slide content (the text source of truth).
7. TopFull GitHub README: https://github.com/kaist-ina/TopFull/tree/main

---

## The prompt

```
You are designing a PROJECT-PLAN slide deck for a student team at a TAU Workshop in Communication
Networks and Information Security. The project: self-implement RetryGuard (from the RetryGuard paper)
and evaluate it on a Kubernetes microservice stack running TopFull overload control (Online Boutique
app), on Ron Nezer's existing lab environment. This is a PLAN, not a results talk — we have no results
yet. The deck must be self-explanatory: it may be read as a standalone document with nobody presenting.

Produce roughly 20–25 content slides following the exact section order in PRESENTATION-GUIDE.md.

============================================================
GLOBAL VISUAL DIRECTION — APPLY TO EVERY SLIDE
============================================================

Your most important job, beyond correct text, is to GENERATE A STRONG, PURPOSEFUL VISUAL ON EVERY
CONTENT SLIDE. Do not leave slides as text-only. Do not use generic stock photos, clip art, abstract
"technology" backgrounds, photos of people, or decorative imagery. Every visual must encode real
information from the slide: a system diagram, a flow, a topology, a feedback loop, a timeline, or a
labeled chart. If you cannot make a visual that adds meaning, make a clean labeled diagram of the
slide's core idea — never filler.

DESIGN SYSTEM (reuse consistently across all slides so the deck feels like one system):
- Layout: split layout. Text/bullets occupy the left ~55%; the diagram or chart occupies the right ~45%.
  For full-diagram slides (topology, feedback loops), use a centered diagram with a short text band on top.
- Color roles (use these meanings consistently everywhere):
    • TopFull components ........ deep blue (#1E3A8A)
    • RetryGuard components ..... teal/green (#0D9488)
    • Online Boutique services .. neutral slate gray (#475569)
    • Istio / Envoy sidecars .... purple (#7C3AED)
    • Load generator (Locust) ... amber (#D97706)
    • Problem / overload / retry storm states ... red (#DC2626)
    • Healthy / recovered states ............... green (#16A34A)
- Typography: large bold slide titles; concise bullets (max ~6 words per bullet line where possible);
  every diagram element must be LABELED with text — no unlabeled boxes or arrows.
- Iconography: use simple flat line icons (Kubernetes pods as hexagons/cubes, services as rounded
  rectangles, arrows for request flow, a lightning/loop glyph for retries). Keep icons monochrome
  within their color role.
- Arrows: solid arrows = request/response flow; dashed arrows = control/metrics signals (e.g., a
  controller reading metrics or patching config). Always label what flows along each arrow.
- Consistency: the SAME architecture diagram style must reappear (simplified) on the topology slide,
  the scenario slides, and the metrics slide, so the audience re-recognizes the system each time.

TONE: present the plan clearly and scientifically. No meta-commentary ("this is not a sales pitch",
"we don't know yet"). No phase numbers on slides — use "TopFull only" and "TopFull + RetryGuard".

============================================================
PER-SLIDE CONTENT + VISUAL SPECIFICATION
============================================================

--- SLIDE 0 — Opening ---
TEXT: Title "RetryGuard on TopFull — TAU Communication Networks Workshop". Participants: Yoav Binyamin
Naaman, Sagi Eisenberg, Ido Zacharia. Nothing else.
VISUAL: A clean title slide. A single minimal hero diagram: a small node labeled "TopFull" (deep blue)
with a teal "RetryGuard" shield/badge layered on top of it, sitting above three stacked Kubernetes pod
hexagons (slate). No stock imagery, no people. Subtle, professional, lots of whitespace.

--- SLIDE 1 — Goal and Hypothesis ---
TEXT: Measure self-implemented RetryGuard on TopFull + Online Boutique under overload — where it helps,
where it doesn't, what trade-offs emerge. Hypothesis: dynamic retry control reduces retry storms and
protects goodput vs. default retries (RetryGuard paper Table 1 style metrics: retries/request, billing,
rejection rate). Note: system-wide gain may be small while specific microservices improve a lot —
surface both. Deliverables: (1) working setup, (2) TopFull only vs TopFull + RetryGuard data,
(3) evaluation report with time-series charts.
VISUAL: A two-panel "before vs after" conceptual mini-chart on the right.
  • Left panel labeled "Default retries": a rising red line labeled "retries/request" climbing steeply
    (a retry storm).
  • Right panel labeled "RetryGuard on": the same line flattening to near-zero (teal/green), with
    "goodput" holding steady.
  Make clear these are HYPOTHESIZED/illustrative shapes, not measured data (small italic caption:
  "illustrative — hypothesis, not results"). Axes labeled, no numbers required.

--- SLIDES 2–3 — What is TopFull? ---
TEXT (mechanism first, numbers last):
Problem: per-service overload controls (DAGOR, Breakwater) act in isolation; when multiple APIs share an
overloaded downstream service, some requests are partially processed then rejected → starvation, wasted
work. How TopFull works: top-down, API-wise load control at the entry; clusters interdependent APIs into
parallel sub-problems; RL-based rate controller (PPO, Sim2Real) adjusts admission every 1 second from
end-to-end goodput + percentile latency; respects business priority. Results (compact footnote only):
1.82x goodput vs DAGOR, 2.26x vs Breakwater; up to 3.91x with autoscaler; up to 57% fewer resources;
converges in 5s vs 27s.
VISUAL (slide 2 — the starvation problem): a small topology diagram. Two API entry points (API 1, API 2)
on the left. Both route through "Microservice A (cap 10k rps)"; API 1 also continues to "Microservice B
(cap 3k rps)". Show API 1 requests getting REJECTED at B (red X) after consuming capacity at A, and API 2
being STARVED at A (red). Label the wasted work. This makes "starvation" visual.
VISUAL (slide 3 — how it works): a horizontal control-flow diagram. Left: "External APIs" (amber). Center:
a deep-blue "TopFull entry proxy + RL controller" box with a circular feedback-loop arrow labeled
"adjust admission rate every 1s". A dashed arrow loops back from the cluster labeled "goodput + latency
signals". Right: the microservice cluster (slate pods). Put the benchmark numbers in a small gray footnote
strip at the bottom, NOT as big callouts.

--- SLIDES 4–5 — What is RetryGuard? ---
TEXT (plain language, NO "Algorithm 1" / no pseudocode):
Problem: default retries (exponential backoff, jitter, budgets) are built for instantaneous failures.
During prolonged miscoordination (e.g., fast upstream autoscaler vs slow downstream DB), retries become
counterproductive → retry storms: failed retries amplify load on an already-overloaded service
(load factor ρ > 1 → rejection rate rises sharply, paper Sec. 5) → self-inflicted Denial-of-Wallet.
How it works: each microservice has a small controller watching its own HTTP rejection rate (503/429)
from the local Istio/Envoy sidecar. If rejections stay above ~20% for several consecutive ~30s windows →
turn OFF retries for that service only (patch Istio VirtualService). When rejections stay below threshold
for the same number of windows → turn retries back ON. Distributed: each service decides independently,
no central coordinator. Quiet under normal load. Results (compact footnote): AWS retries/req 2.09→0.05
(98% less), billing 1029%→100%; Istio 0.31→0.01, billing 224%→100%; up to 65% less resources, >90% latency
improvement; mitigates DDoS amplification.
VISUAL (slide 4 — the retry storm): a "snowball" amplification diagram. One user request (amber) hits an
overloaded service (red); on failure it spawns 2–3 retry arrows, each of which fails and spawns more —
draw it as a widening red fan/cascade of retry attempts piling onto the red service. Annotate "ρ > 1:
each retry multiplies the load." This is the single most important visual in the deck — make it vivid.
VISUAL (slide 5 — how it works): a per-service controller diagram + a small state machine.
  • One Online Boutique service (slate) with its Istio/Envoy sidecar (purple) beside it. A teal
    "RetryGuard controller" reads (dashed arrow) "rejection rate" from the sidecar and writes (dashed
    arrow) "patch VirtualService: retries off/on".
  • Below it, a compact 2-state machine: state "Retries ON (healthy)" (green) → arrow labeled
    ">20% rejections for N×30s windows" → state "Retries OFF (suppressed)" (red) → arrow labeled
    "<20% for N×30s windows" → back to ON. Benchmark numbers in a gray footnote strip.

--- SLIDE 6 — Stack & Topology ---
TEXT: Run on Ron Nezer's existing lab environment (pre-provisioned K8s cluster, TopFull + Online Boutique
already set up; K8s 1.26, Istio, Locust). RetryGuard runs on the master node: reads per-service rejection
rates from Istio/Envoy sidecar metrics, patches Istio VirtualService retry policies via the Kubernetes
Python client. Online Boutique is the test app (representative call chain), not the subject of study.
VISUAL (centered, the canonical architecture diagram — reused later in simplified form):
  Left → right flow:
  [Locust load gen (amber)] --solid "user traffic"--> [Master node (deep blue box) containing: "TopFull
  Go proxy + RL controller" and a teal "RetryGuard script"] --solid "admitted requests"--> [Worker nodes:
  Online Boutique pods (slate hexagons), each with a purple Istio/Envoy sidecar].
  Control signals as DASHED arrows: RetryGuard <-- "rejection metrics" -- sidecars; RetryGuard --
  "patch VirtualService (retries on/off)" --> sidecars. Keep it clean and uncluttered; label every box
  and arrow. This is a reference architecture, not eye candy.

--- SLIDES 7–9 — How We Test ---
TEXT: 
TopFull only: TopFull active, Istio default retries on, RetryGuard OFF; fixed workload/duration/replicas;
save CSVs as the reference run.
TopFull + RetryGuard: identical load/topology/duration; only addition RetryGuard ON; controller settings
from paper Sec. 6.2 (~20% threshold, ~30s interval); implemented as a Python script on master using the
Kubernetes Python client to patch Istio VirtualService CRDs.
Repeated runs: Locust is non-deterministic, so run each arm multiple times; compare averages/medians;
isolates RetryGuard's effect from noise.
VISUAL (the experiment design — an A/B comparison diagram): two side-by-side identical stack columns.
  • Left column titled "TopFull only": the simplified architecture with the RetryGuard box GRAYED OUT /
    crossed out.
  • Right column titled "TopFull + RetryGuard": same stack with the RetryGuard box ACTIVE (teal, glowing).
  Between/below them a band: "Same load · same topology · same duration · multiple runs each →
  averages/medians." Use a small "×N runs" repeat icon under each column. This visual must instantly
  communicate "only one thing changes."

--- SLIDES 10–12 — What We Want to Find Out (intellectual core) ---
TEXT: Opening frame — central question: does RetryGuard add value ON TOP of TopFull, or is TopFull's
entry-point control already sufficient? RetryGuard was validated in AWS and standalone Istio/K8s, never
alongside a top-down overload controller. Once TopFull admits a request, Istio's internal retries fire
inside the cluster, invisible to TopFull's proxy. Then list each open question as a FULL SENTENCE with a
one-line explanation (do NOT render as a 2×2 grid of boxes): System-level gains; Topology beneficiaries;
Chain propagation; Controller interaction; Combined equilibrium; Topology position sensitivity; Interval
parameter sensitivity. (See NOTEBOOKLM-PROMPT.md for the exact wording of each.)
VISUAL (opening frame slide): a "blind spot" diagram. Show TopFull controlling the ENTRY (deep blue gate
at the cluster boundary, dashed coverage area around the entry). Inside the cluster, show internal
service-to-service retry arrows (red) happening BELOW/behind TopFull's coverage, labeled "internal Istio
retries — invisible to TopFull's proxy." A teal RetryGuard marker sits next to an internal service,
labeled "operates here." The visual should make the gap obvious: TopFull sees the door, RetryGuard sees
inside the rooms.
VISUAL (the questions slides): do NOT box them in a grid. Instead, lay the questions vertically as a
numbered list on the left, and on the right draw a single small recurring diagram that highlights, per
question, WHERE in the architecture the question lives (e.g., for "topology beneficiaries" highlight
specific pods; for "controller interaction" show the TWO feedback loops overlapping). If one diagram per
question is too much, use one shared annotated topology with colored pins numbered to each question.
SPECIAL VISUAL for "Controller interaction": draw TWO interlocking feedback loops — a deep-blue 1-second
loop (TopFull: admission rate ↔ goodput/latency) and a teal ~30-second loop (RetryGuard: retries on/off ↔
local rejection rate) — overlapping on a shared "cluster load" node, with a "?" where they meet (cooperate
or interfere?). This is a key conceptual visual.

--- SLIDES 13–18 — Load Scenarios (1 intro + 5 scenario slides, each its own slide) ---
Each scenario MUST be its own numbered slide. Describe the system behavior in prose first; the traffic
graph supports it. Tie each scenario to the open question(s) it answers.

SLIDE 13 — Scenarios Intro:
TEXT: scenarios are derived from the open questions, not chosen independently; all use TopFull's synthetic
workload generator (Locust + TopFull scripts); RetryGuard decisions come from Istio/Envoy sidecar metrics
(a separate measurement point from TopFull's entry proxy) — cross-reference both.
VISUAL: a mapping diagram — left column "Open questions" (the 7 questions, short labels), right column
"Scenarios 1–5", with connector lines showing which scenario answers which question(s). This makes the
"derived from questions" logic literally visible.

For SLIDES 14–18, every scenario slide gets a TRAFFIC-SHAPE TIMELINE CHART on the right:
  • X-axis = time, Y-axis = offered load (RPS). Draw the load curve characteristic of that scenario.
  • Overlay a horizontal dashed line = "capacity (ρ = 1)".
  • Shade regions where ρ > 1 in light red ("overload").
  • Where relevant, mark with a teal vertical marker when RetryGuard would trigger (retries OFF) and a
    green marker when it re-enables.
  • Caption "illustrative traffic shape — not measured data".

SLIDE 14 — Scenario 1: Normal Operation:
TEXT: flat, manageable RPS within capacity; tests that RetryGuard stays non-intrusive (rejections < ~20%,
no Istio changes). Answers system-level gains (sanity-check side).
VISUAL: timeline chart = a FLAT load line entirely BELOW the capacity dashed line (no red shading). A
small "RetryGuard: idle, 0 changes" green badge.

SLIDE 15 — Scenario 2: Sustained Overload (core experiment):
TEXT: step RPS up until ρ > 1 and HOLD 5–10 min; TopFull throttles entry but admitted requests still fail
downstream and Istio retries internally (retry storm). Why 5–10 min not 1–2: (1) triggering alone needs
~1–2 min (several consecutive ~30s windows >20%) so short tests only measure detection latency; (2) the
effect appears only AFTER suppression once load drops and TopFull's 1s RL re-settles; (3) the
disable→recover→re-enable cycle must fire repeatedly to prove stable behavior; (4) matches RetryGuard's
real target (prolonged miscoordination, not brief spikes). Tests TopFull only vs + RetryGuard. Answers:
system-level gains, topology beneficiaries, chain propagation, controller interaction.
VISUAL: timeline = ramp up, then a long HIGH plateau above capacity (large red overload band), then
recovery. Annotate the plateau with several ~30s window ticks and teal RetryGuard trigger markers showing
the repeated disable/re-enable cycle. This is the flagship scenario chart — make the "long hold" obvious.

SLIDE 16 — Scenario 3: Targeted Bottleneck:
TEXT: full-chain traffic while ONE downstream service is constrained (reduced replicas / CPU limit) so it
hits ρ > 1 even under TopFull's throttled entry. Differs from Sustained Overload: stress is engineered at
one node (overall load need not exceed total capacity) → clean attribution + watch relief propagate
upward. TopFull can only throttle whole entry APIs routing through it (blunt); RetryGuard acts surgically
at the hot spot. Analogous to RetryGuard Bookinfo case study. Answers: topology beneficiaries, chain
propagation, controller interaction.
VISUAL: a topology diagram (reuse the call-chain) with ONE service marked red/"constrained (ρ>1)" while
the rest are healthy (green/slate). Show TopFull throttling the whole entry API path (blunt, wide blue
arrow) vs RetryGuard's narrow teal action pinpointed AT the red service. Optional small inset traffic
timeline showing only that service saturating.

SLIDE 17 — Scenario 4: Topology Position Comparison:
TEXT: two Targeted Bottleneck runs, same load + constraint method, differing only in WHICH service is
constrained (hold RetryGuard logic constant, vary position). Run A — Gateway-adjacent (e.g.,
ProductCatalog, called directly from Frontend; TopFull maps overload to entry APIs quickly). Run B —
Deep leaf (e.g., Payment, only via Frontend→Checkout→Payment; TopFull's signal most attenuated; retries
stack at Checkout→Payment). Tests whether RetryGuard matters more when TopFull's entry signal is strong
(A) vs attenuated (B). Answers: topology position sensitivity, topology beneficiaries, chain propagation.
VISUAL: TWO small side-by-side copies of the Online Boutique call tree.
  • Run A: highlight ProductCatalog (shallow, near Frontend) in red, with a SHORT path from entry.
  • Run B: highlight Payment (deep, under Checkout) in red, with a LONG path from entry.
  Use a fading blue gradient from the entry to show TopFull's signal getting WEAKER with depth (strong at
  ProductCatalog, attenuated at Payment). This makes "position" the visual subject.

SLIDE 18 — Scenario 5: Re-enable Interval Tuning:
TEXT: repeat Sustained Overload; keep load/replicas/threshold fixed; vary only the re-enable interval
(10s, 20s, 30s [paper default], 60s). Too short → retries restart before recovery; too long → delays
goodput recovery. Paper tuned 30s without a co-running top-down controller; TopFull adjusts admission
every ~1s. Tests which interval gives best combined goodput + stability. Answers: interval parameter
sensitivity, combined equilibrium.
VISUAL: a small multiples chart — 4 mini timeline panels (10s / 20s / 30s / 60s). In each, show retries
re-enabling at that interval after suppression and the resulting goodput curve: short intervals show
oscillation/re-overload (red wobble); long intervals show a flat low-goodput gap; 30s shows a balanced
recovery. Label the trade-off under each panel. (Illustrative shapes, not data.)

--- SLIDES 19–20 — Metrics ---
TEXT: three measurement layers. Layer 1 — System & API performance (TopFull metric_collector.py → CSVs):
goodput + latency per API (getcart, getproduct, postcheckout...), latency SLO 1s; rejection rate per API
(the signal RetryGuard reads); retries per request (most direct measure; vs paper Table 1, 0.31→0.01 for
Istio). Layer 2 — Infra resource usage (cAdvisor via resource_collector.py): CPU + memory per pod; pod
instance counts over time (num_instances.csv) → over-scaling. Layer 3 — Controller logic & state (our
RetryGuard logs): which services toggled off and when; time-to-recovery; business priority context from
overload_detection.py. All synthesized into comparative TopFull only vs TopFull + RetryGuard time-series
charts.
VISUAL: a 3-layer stacked diagram mapped onto the architecture. Draw three horizontal bands:
  • Layer 1 (top, blue) pinned to the TopFull proxy — icon: line chart (goodput/latency/retries).
  • Layer 2 (middle, slate/purple) pinned to the pods + sidecars — icon: CPU/memory gauge + pod-count
    bars.
  • Layer 3 (bottom, teal) pinned to the RetryGuard script — icon: a small event log / state-timeline.
  Each band shows WHERE the data is collected and a tiny example chart thumbnail. Add one example
  "TopFull only vs TopFull + RetryGuard" side-by-side time-series thumbnail (two overlaid lines, blue vs
  teal) captioned "report output (illustrative)".

--- SLIDE 21 — Timeline & Milestones ---
TEXT (no phase numbers, no blocker callouts):
  Infrastructure setup — Ron Nezer's environment, Istio, app running — Week 1–2
  Baseline experiment — TopFull only — Week 2–3
  RetryGuard implementation and Istio integration — Week 3
  Experiment — TopFull + RetryGuard — Week 3–4
  Evaluation, comparison, and final report — Week 4
VISUAL: a clean horizontal GANTT-style timeline (weeks 1–4 on the X-axis), one colored bar per milestone,
bars overlapping where weeks overlap. Color the two experiment bars to match their arm (TopFull only =
blue, TopFull + RetryGuard = blue+teal). No warning icons, no blocker flags.

--- SLIDE 22 (optional) — Summary / Deliverables ---
TEXT: recap what we build, test, deliver. Deliverables: (1) working TopFull + RetryGuard setup on Ron
Nezer's environment; (2) TopFull only vs TopFull + RetryGuard data across all scenarios; (3) evaluation
report with time-series charts (goodput, latency, retries/request, resources, autoscaler behavior).
VISUAL: three deliverable cards in a row, each with a distinct icon: (1) a stack/cluster icon "working
setup"; (2) a dual-dataset icon "two experiment arms"; (3) a report-with-charts icon "evaluation report".
Keep it minimal and confident.

============================================================
HARD RULES (do not violate)
============================================================
- Generate a meaningful, labeled visual on EVERY content slide as specified above. Never output a
  text-only slide and never substitute a decorative stock photo for a specified diagram.
- Any chart that is not real measured data MUST be captioned "illustrative — not results". We have no
  results yet; never fabricate numbers as if measured.
- Keep the design system colors/meanings consistent across all slides.
- Do NOT reorder sections. Do NOT add agenda/background/future-work slides. Slide 0 has ONLY the project
  name and participants.
- Do NOT use phase numbers. Use "TopFull only" and "TopFull + RetryGuard".
- Ground all text in the attached sources; prefer PRESENTATION-GUIDE.md wording. Do not invent claims.
- No meta-commentary ("not a sales pitch", "we don't know yet").
```

---

## Tips for running this in Gemini

- **Generate in batches.** If Gemini struggles to render all 20+ visuals at once, run it section by
  section (e.g., "now produce slides 13–18 with their traffic-shape charts as specified") so each diagram
  gets full attention.
- **If a slide still comes back text-only,** re-prompt with just that slide's `VISUAL:` block and the line:
  "Generate this exact diagram on the slide — labeled boxes and arrows, not a stock photo."
- **For Gemini in Google Slides:** ask it to insert the described diagram, then refine with follow-ups like
  "make the RetryGuard controller teal and add the dashed metrics arrow."
- **Reuse the architecture diagram:** once Gemini draws the Slide 6 topology well, tell it to reuse that
  same diagram (simplified) on the scenario and metrics slides for visual consistency.
