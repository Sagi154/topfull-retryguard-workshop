# Replica-scaling probe results (2026-09-24)

## Answer

Frontend 6 + checkout 2 (CPU request halved so the pods fit today's 16-vCPU worker) did **not** raise the number of services overloaded at once: the reference max was 2 (checkout), Hold A dropped to 1, and Hold B's only hot service was recommendationservice. The extra Locust users never raised storefront RPS; they piled up at frontend (failure 0.03 → 0.19 → 0.30, sojourn 358 → 659 → 809 ms) and checkout received *less* traffic. Worker (~12 of 16 cores) and master (~6.7 of 8) were not the limit. Hold C was not run — TopFull stayed at the 10000 passthrough threshold on both holds.

## Setup

| Run | Folder | Frontend / checkout | `cpu_request_fraction` | Locust counts (getproduct / postcheckout / getcart / postcart / emptycart) | TopFull RL |
|---|---|---|---|---|---|
| ref | `baseline_topfull_no_retryguard_sustained_overload_run28` | 4 / 1 | 1.0 | 300 / 60 / 210 / 50 / 50 | on |
| A | `probe_replicas_f6c2_sustained_overload_run1` | 6 / 2 | 0.5 | 300 / 60 / 210 / 50 / 50 | on |
| B | `probe_replicas_f6c2_sustained_overload_run2` | 6 / 2 | 0.5 | 420 / 85 / 295 / 50 / 50 | on |

All 600 s, RetryGuard off, catalog HPA max 1, `spawn_rate` 50. Steady window: drop first 60 s and last 10 s. Raw side-by-side: [`experiments/results/campaign_48/S2_sustained_overload/_replica_probe_compare.md`](../../../experiments/results/campaign_48/S2_sustained_overload/_replica_probe_compare.md). These folders are a sizing probe, not campaign or frozen-μ data.

## Headline

| Run | Services overloaded at once | Hot services (util p95 >= 0.85) |
|---|---|---|
| ref | max 2, mean 1.018 | checkoutservice |
| A | max 1, mean 0.123 | (none >= 0.85) |
| B | max 1, mean 0.696 | recommendationservice |

## Rows

**1. Load sent.** Hold A already delivered less getproduct / getcart RPS than the reference (226 / 164 vs 274 / 196) at much higher P95 (~2100 ms vs 725 / 461). Hold B's +40% users did not raise those RPS numbers (219 / 164); postcheckout RPS stayed ~46. The extra users did not become extra offered load.

**2. TopFull cap.** Reference was capped on every API (share-capped ~0.99). Holds A and B were not: threshold stayed 10000 and admitted RPS matched the Locust RPS. TopFull did not absorb Hold B, so Hold C (TopFull off) was not run.

**3. Backend arrivals.** Checkout arrivals fell from 69 req/s (ref, failure 0.30) to 33 then 29 (failure 0). Recommendations arrivals rose (430 → 608 → 706) and its failure / sojourn rose with them (0 / 146 ms → 0.16 / 457 ms → 0.22 / 469 ms). Frontend inbound failure and sojourn rose in the same steps. Outbound retry Δ went 20k → 128k → 189k. The extra replicas unblocked checkout and moved pressure onto recommendations and the frontend.

**4. Utilization.** Reference checkout p95 util 0.99 (overloaded 99% of ticks). Hold A/B checkout ~0.50 / 0.00 overloaded. Frontend stayed ~0.23–0.30 even at 6 replicas. Recommendations p95 util 0.74 → 0.79 → 0.89 (overloaded share 0.03 → 0.12 → 0.70). No other service reached 0.85.

**5. Machines.** Master 6.05–6.70 of 8 cores (same band as the reference). Worker 11.8 / 16 p95, 12.2 max — busy but not pegged. Load VM ~1 of 8 cores; Locust process max ~28% CPU. The reservation cut (Option 2) placed every pod; the node was not the bottleneck.

## Decision

**Do not buy larger VMs for more frontend / checkout replicas.** Option 2's scheduling trick worked (6+2 fit; worker stayed under ~14 cores; master under 7), but it reduced simultaneous overloads instead of increasing them. The next limit is the storefront / recommendationservice path, not node CPU.

- More services overloaded, node under ~14, master under 7: **partially true on machines, false on overloads.**
- Worker or master pegged → Option 1 (highcpu-16 / highcpu-32, ~56 vCPU quota): **no.**
- TopFull cap or Locust stopped the load: **Locust RPS did not rise with +40% users; TopFull did not cap A/B.** Fix is mix / recommendationservice, not VMs.

HPAs restored after the probe (frontend 1–4, catalog max 2). CPU requests restored to equal limits. Probe YAML next-free: `probe_replicas_f6c2_sustained_overload_run3`. No ADR — Option 2 is not adopted as the experiment base.
