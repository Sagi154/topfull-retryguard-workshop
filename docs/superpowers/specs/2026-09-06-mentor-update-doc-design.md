# Mentor Update Doc — Design Spec

**Date:** 2026-09-06
**Status:** Approved (pending implementation)

## 1. Purpose

Produce a doc for the workshop mentors that brings them up to date on the "RetryGuard on TopFull" project: what infrastructure/environment we ran on, what Online Boutique is, what scenarios we ran, and — the main event — the results gathered so far from the `campaign_48` dataset, shown as charts with brief factual observations. This is **not** the final presentation or written report. Its purpose is to let mentors judge what's sufficient and flag what's missing, before we move to the polished deliverable.

Data source: **`experiments/results/campaign_48/` only.** The historical `august_38/` dataset is not referenced anywhere in this doc, not even as a footnote.

"Dry results" in this context means: chart + short factual observation bullets, not a polished narrative, not conclusions/recommendations, and not a verdict on sufficiency (that's for the mentors to give us).

## 2. Deliverables & file layout

```
Guides and Info/mentor-update/
  MENTOR-UPDATE.md          ← the doc itself
  charts/                   ← curated charts embedded in the doc (subset, see §4)
    S1/*.png
    S2/*.png
    S3/*.png
    S4/*.png
    S6/*.png
  charts_gallery/           ← full gallery: every (scenario x metric x endpoint/service) chart, for reference
    S1/*.png ... S6/*.png   ← includes everything in charts/ plus every non-curated combination

experiments/
  mentor_charts.py          ← standalone, rerunnable script. Reads campaign_48 CSVs, writes both
                               charts/ (curated subset) and charts_gallery/ (everything).
```

`mentor_charts.py` is a plain script (not a notebook), rerunnable if the campaign later gets more repeats or S6/S5 configs are bumped and re-run.

## 3. Doc outline (`MENTOR-UPDATE.md`)

### Section 1 — Infrastructure & Environment (exposition, short)

- The 3 GCP VMs and their roles: `topfull-master` (K8s control plane, Istio control plane, TopFull proxy/RL controller, RetryGuard), `topfull-worker-1` (Online Boutique pods with Envoy sidecars), `topfull-load` (Locust).
- The stack: self-managed `kubeadm` Kubernetes + Istio service mesh + Locust load generation.
- Where TopFull and RetryGuard sit in the request path, at a conceptual level (no code/config detail).
- A **Mermaid diagram** (rendered directly in the markdown) showing: Locust → Istio ingress/Envoy sidecars on the worker (Online Boutique pods) ⟷ TopFull proxy + RL controller + RetryGuard (on master, which also hosts the K8s control plane) — annotated to show RetryGuard patches Istio VirtualServices on the worker's pods based on rejection-rate signals read from Envoy.

### Section 2 — Online Boutique: role & architecture (exposition, short)

- What Online Boutique is and why it was chosen as the test application.
- Embed `Online-Boutique-architecture.png` (already exists at repo root).
- A brief list of the services in play, calling out which ones we specifically constrain in later scenarios (`checkoutservice` in S3, `productcatalogservice` in S4A, `paymentservice` in S4B) so section 4 is easy to follow without re-explaining topology each time.

### Section 3 — Scenarios: high-level (exposition, short)

- A compact table covering all 6 scenarios: name, what changes (load shape / constraint), duration, and which open research question(s) it targets. Condensed from `SCENARIOS-GUIDE.md`'s quick-reference table.
- No results in this section — purely "what we ran and why," setting up section 4.

### Section 4 — Results: per-scenario deep dive (MAIN SECTION)

One subsection per scenario grouping:

1. **S1 — Normal Operation**
2. **S2 — Sustained Overload**
3. **S3 — Targeted Bottleneck**
4. **S4 — Topology Position** (S4A ProductCatalog + S4B Payment combined into one subsection, shown side-by-side per chart, since the scenario's whole point is comparing the two)
5. **S6 — Forced Recovery**, with the **S5 interval sensitivity sweep merged into this same subsection** (S5 has no baseline of its own and is only meaningful compared against S6)

Each subsection (except S4/S6 as noted) follows this fixed template:

- **1-line framing:** what this scenario does + which open research question(s) it targets (from `PHASE7-DATA-GAPS.md` / `context/Evaluating_RetryGuard_on_TopFull.md`).
- **Chart set.** All time-series charts plot two lines: baseline (mean of 3 repeats, pointwise-averaged per the method in `campaign_48/README.md` §2) vs RetryGuard (mean of 3 repeats), x-axis = seconds elapsed. Where a RetryGuard run has `retryguard.log`, its `ON→OFF` / `OFF→ON` events are overlaid as vertical dashed annotations on that line.
  - **Goodput over time** — system-wide, from `total.csv`. For S3/S4, add a second panel from the specific bottleneck endpoint (`postcheckout.csv` for S3/S4B, `getproduct.csv` for S4A).
  - **P95 latency over time** — same total/bottleneck-endpoint split as Goodput.
  - **Rejection rate over time** (derived: `Fail / RPS`) — same total/bottleneck-endpoint split.
  - **Retries per request** — derived by differencing consecutive cumulative rows in the Envoy CSVs (`envoy_retries_frontend.csv`, `envoy_retries_checkoutservice.csv`). Two views per caller: (a) one line per `target_service` it calls, (b) target services summed into a single line. So each scenario shows up to 4 retries charts (2 callers × 2 views), fewer where a caller has no traffic to show.
  - **CPU (millicores) and Memory (working-set bytes)** — all 6 Online Boutique services overlaid on one chart each (fall back to small multiples if a single overlay is unreadable).
- **S4 exception:** every chart above is drawn with S4A and S4B results shown side-by-side (e.g. two panels, A left / B right, same y-axis scale) rather than as separate subsections, since the point of S4 is a direct A-vs-B comparison.
- **S6 exception (S5 merge):** after S6's standard chart set, an additional block:
  - Recovery-phase Goodput and Rejection charts with 6 lines: baseline, RetryGuard, and the 4 interval variants (10s/20s/30s/60s), all referenced against S6's load shape.
  - A toggle-event timeline table: disable (`ON→OFF`) and re-enable (`OFF→ON`) timestamps per interval variant and per S6 baseline/RG run, to make oscillation (e.g. the known 10s-run3 5-disable/5-re-enable case) visible at a glance.
- **"What we observe"** — 2 to 4 short factual bullets per subsection. Describe what the charts show (e.g. "goodput separates after t=X," "checkoutservice CPU drops within Ys of the first ON→OFF"). No conclusions, no recommendations, no sufficiency verdicts.
- **Gallery pointer** — one line: "Additional per-endpoint/per-service charts for this scenario: `Guides and Info/mentor-update/charts_gallery/S<N>/`."

## 4. Curated vs gallery chart split

- **Gallery (`charts_gallery/`):** exhaustive. For every scenario, every metric (Goodput, P95, Rejection, Retries/request, CPU, Memory), and every endpoint/service combination that exists in the data (all 5 Locust endpoints + total, all target services per caller, all 6 Online Boutique services) — one PNG each. Nothing is filtered out here.
- **Curated (`charts/`, embedded in the doc):** exactly the subset described in §3's chart-set bullets per scenario (system-wide + bottleneck-endpoint panels only, summed + per-target retries views, all-services CPU/mem overlay). This keeps the doc itself readable while leaving the full picture available one click away.
- Both are produced by the same script in one run — the curated set is not manually copied, it's generated by a second, narrower pass over the same helper functions.

## 5. `mentor_charts.py` — script design

Location: `experiments/mentor_charts.py`. Plain Python (matplotlib), rerunnable.

Core pieces:

- **Repeat-averaging helper** — given a scenario + condition (baseline/RG) + CSV filename, globs the matching run folders under `experiments/results/campaign_48/<scenario_dir>/`, reads each CSV, truncates all repeats to the shortest length, and returns the pointwise mean (and min/max band) per column.
- **Time-series plot helper** — draws baseline vs RetryGuard mean lines (+ optional band) for a given metric column, x-axis in elapsed seconds; if a `retryguard.log` exists for the RG run group, parses `ON→OFF`/`OFF→ON` lines and draws vertical dashed annotations at those elapsed-second offsets.
- **Rejection-rate derivation** — computes `Fail / RPS` per row (0 where `RPS == 0`) before averaging.
- **Envoy retries-per-request helper** — reads `envoy_retries_{frontend,checkoutservice}.csv`, groups by `target_service`, diffs consecutive cumulative rows (`upstream_rq_retry`, `upstream_rq_total`) per repeat, averages across repeats, produces both the per-target-service and summed views.
- **Resource usage helper** — reads `resource_usage.csv`, groups by `service`, averages `cpu_millicores` and `memory_working_set_bytes` across repeats, one line per service.
- **Gallery pass** — loops every scenario x every metric x every applicable endpoint/service/target combination, saving to `charts_gallery/<Sx>/`.
- **Curated pass** — calls the same helpers with the narrower file list from §4, saving to `charts/<Sx>/`.
- **S4 side-by-side composer** — after generating S4A/S4B charts individually (or directly as combined subplots), arranges each metric as a two-panel figure (A | B) for both the gallery and curated sets.
- **S5/S6 merge composer** — a dedicated function that overlays S6 baseline/RG with the four S5 interval variants' recovery-phase Goodput/Rejection, plus a function that extracts disable/re-enable timestamps from each group's `retryguard.log` files into the timeline table (written out as a small markdown-table snippet or CSV that gets pasted into `MENTOR-UPDATE.md`).

No CLI flags are required beyond running the whole script; it always regenerates both `charts/` and `charts_gallery/` for all 6 scenario groupings in one invocation.

## 6. Explicit scope boundaries (to avoid ambiguity later)

- Only `campaign_48/` data is used. `august_38/` is not loaded, plotted, or mentioned anywhere in the doc.
- `Latency99` is never plotted (documented campaign-wide as always-zero/unused).
- `num_agent.csv` and `replica_count` are not plotted (documented as uninformative in this workshop's fixed-replica, non-wired-RL-agent-count setup).
- The doc does not include a written conclusions section, a recommendations section, or an assessment of whether results are "sufficient" — that judgment is explicitly left to the mentors reading it.
- Chart images are static PNGs embedded via markdown image syntax, not interactive.
