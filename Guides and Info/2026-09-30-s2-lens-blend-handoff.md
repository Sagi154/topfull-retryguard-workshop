# Handoff: S2 both-off holds that blend Lens A and Lens B

Goal: find one CPU table plus one Locust user mix whose both-off hold shows elements of both lenses in [2026-09-30-s2-candidate-ranking-runs-1-79.md](2026-09-30-s2-candidate-ranking-runs-1-79.md): an independent pair (checkout and recommendations, Lens A) and a chain (checkout with email or payment, Lens B). Magnitudes may be well below either lens alone. A variant is three knobs: per-pod CPU limits, replica counts, and Locust user counts. This handoff fixes all three for four holds.

## What you decided

- **Retries are not a target.** Do not chase 100k frontend to recommendations retries. Retry edges are recorded but do not pass or fail a hold.
- **Mix size.** Configured users sum to about 600. 50-100 over is the ceiling. 720 (run 69) is out.
- **Frozen μ is ignored.** Both-off holds never used it.
- **Pass bar is streaks and overloaded ticks only** (below).

## Where things stand

Last series was Hybrid-1 (runs 74-79). `experiments/configs/scenario_2_baseline_no_topfull.yaml` is unused **run80**, `scale_constraints: []`, paper CPU, leftover counts 250/350/150/10/10 (not a scheduled hold). Next free both-off slot is **run80**. Per `AGENTS.md` the VMs were left **RUNNING** after run79. Confirm that first: they may have been stopped since.

Do not overwrite any run 1-79, in particular the anchors run6, run10, run11, run34, run69.

**Sampling caveat.** Runs 74-79 had 2 s `service_inbound.csv` polls and are excluded from the ranking. This series must have 1 s polls, or a streak of 30 does not mean 30 s. The sampling gate below is hard. If it fails, capture the collector state and stop the series; do not score that hold.

## Pass bar

Scored with `python experiments/s2_both_off_canon.py <first> <last>` (writes `s2_canon_<first>_<last>.json` into the current directory) and `python experiments/s2_both_off_abc.py <run_dir>`. Streak = `(Δ5xx + Δresets)/Δtotal > 0.20`, consecutive 1 s polls, last 5 dropped, nine controlled backends. Overloaded tick = `topfull_detect.csv` `overloaded=1`.

| Element | Requirement |
|---|---|
| Recommendations | streak ≥ 10 and ≥ 10 overloaded ticks |
| Checkout | streak ≥ 10 and ≥ 10 overloaded ticks |
| Chain leaf | email or payment with ≥ 10 overloaded ticks; streak ≥ 10 is better |
| Not counted | retry volume, goodput, max utilization |

A hold that clears all four rows is a **blend**. Two rows clear with the third close is a near-miss worth a tweak. Because the same mix has landed differently before (runs 3 vs 5, 4 vs 7, 42 vs 60), a blend is not accepted until one replay also clears it.

## The variants

Counts are getproduct / postcheckout / getcart / postcart / emptycart. Every hold: 600 s, `spawn_rate` 50, both controllers off, Istio `attempts: 3`, `per_try_timeout_ms: 500`, script `online_boutique_create_v2.sh`, `proxyCPULimit` absent.

Millicores per pod. Request equals limit. Frontend is 4 replicas on every hold; every other service is 1. Paper is the restored table these holds start from. Bold cells are the overrides.

| Service | Paper | C1 run80 | C3 run81 | C2 run82 |
|---|---:|---:|---:|---:|
| frontend | 1150 × 4 | 1150 × 4 | 1150 × 4 | 1150 × 4 |
| checkoutservice | 615 | **800** | **800** | **800** |
| recommendationservice | 1150 | 1150 | 1150 | 1150 |
| productcatalogservice | 1535 | **800** | **800** | **600** |
| cartservice | 1920 | **800** | **800** | **600** |
| currencyservice | 770 | 770 | 770 | **650** |
| shippingservice | 770 | 770 | 770 | **400** |
| adservice | 1150 | 1150 | 1150 | **600** |
| paymentservice | 155 | 155 | **120** | **200** |
| emailservice | 155 | **120** | **120** | **150** |
| redis-cart | 540 | 540 | 540 | **300** |
| **Deployment total** | **13360** | **11655** | **11620** | **10050** |
| Sidecar request | | 100 m | 100 m | 100 m |

C1 and C3 cut catalog 1535 → 800 and cart 1920 → 800. On paper holds run6 and run7 those two peaked at 613 m and 601 m, so 800 m stays above what they used and does not add a new hot service. The cuts also pay for checkout 615 → 800: C1 is 11,655 m and C3 is 11,620 m, both under the 13,360 m ceiling by more than the 140 m a 100 m sidecar costs over a 90 m one across 14 pods. Sidecar request is **100 m** on every hold. C2 is the Hybrid shape from run 69 with checkout at 1 replica instead of 2 and email at 150 m.

| Slot | Name | Table | Sidecar request | Mix | Sum |
|---|---|---|---|---|---:|
| run80 | C1 | Paper-C1 | 100 m | 325 / 80 / 100 / 90 / 5 | 600 |
| run81 | C3 | Paper-C3 | 100 m | 250 / 100 / 100 / 100 / 5 | 555 |
| run82 | C2 | Hybrid-C2 | 100 m | 170 / 210 / 200 / 10 / 10 | 600 |
| run83 | replay | best of run80-82 | as that run | as that run | |
| run84 | replay or tweak | see decision rule | as that run | as that run | |

Why these values:

- **C1** takes run 10's mix (recommendations streak 56, checkout 21 at 610 users) and changes only what starved the leaves. Paper checkout at 615 m × 1 latched and gave email 15 req/s in run 6. Checkout at 800 m should pass about 60-70 req/s of first attempts. Email costs about 1.6 m per req/s, so at 120 m it saturates near 60 req/s. Payment (about 0.9 m per req/s) probably stays cold at 155 m; that is acceptable because email is the long-streak leaf in runs 42, 54 and 61.
- **C3** is C1's table with both leaves capped and run 11's lighter mix (recommendations streak 22, checkout 38 at 555 users). It runs on the same table as C1 with no reshape.
- **C2** is run 69's Hybrid (recommendations streak 19, checkout 23) with the mix scaled from 720 to 600. Its browse load is about 17% lower than run 69's, so the recommendations streak is the risk. Checkout 800 × 1 has no valid 1 s score (runs 74-79 used it at 2 s sampling).

All per-service CPU costs above come from runs 35-52 (see the Runs 30-56 section of [the calibration spec](../docs/superpowers/specs/2026-09-25-s2-overload-user-count-calibration.md)). They are predictions, not measurements of these tables.

## How to run it

1. Confirm VM state with `gcloud compute instances list --project=networks-workshop`. Start any that are stopped and refresh `HostName` in `~/.ssh/config`. SSH aliases only. Confirm `kubectl get nodes` on `topfull-master`.
2. Copy the three tables above into [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md) before the first hold. All three totals (11,655 / 11,620 / 10,050 m) are under the 13,360 m paper ceiling.
3. **Paper tables (run80, run81).** Put only `method: cpu_limit` / `cpu_limit_millicores` entries in `scale_constraints` for the overridden services (run80: checkout 800, catalog 800, cart 800, email 120; run81 adds payment 120). Set `paper_cpu_reconcile: false` so the runner does not reset those four to paper before the hold. Containers are `server` (redis-cart's is `redis`). Every other service stays at its paper limit because the cluster is restored to paper at the start. Verify in `service_capacity.json`.
4. Patch CPU while every backend is still 1 replica. Then pin: frontend HPA `minReplicas = maxReplicas = 4`. For the Paper tables the only replica pin is frontend. Sidecar `sidecar.istio.io/proxyCPU=100m` on all 11 Deployments, `proxyCPULimit` unset. The catalog and cart cuts are what lets the fourth frontend schedule at 100 m; do not drop the sidecar to 90 m.
5. Wait until ready counts match and pending is 0. Cool off 360 s. Launch run80. Between holds: cool off 360 s, bump only `run_number`, `log_folder`, `description` and `locust.user_counts`, clear `/tmp/rg_*.sh` and `/tmp/envoy_retry_params.json` on master, launch.

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

6. **Reshape to Hybrid (run82).** Restore paper CPU first, then write `scale_constraints` for the Hybrid limits (checkout 800, email 150, catalog 600, cart 600, currency 650, shipping 400, ad 600, payment 200, redis-cart 300 with `container: redis`) with `paper_cpu_reconcile: false`. Recommendations at 1150 is the paper value, so it is not listed. Keep frontend pinned at 4 and set the sidecar request to 100 m. If a pod is Pending with `Insufficient cpu`, lower `sidecar.istio.io/proxyCPU` on all 11 Deployments only until it schedules, and record the value. Cool off 360 s, then launch.
7. **Gates per hold** (a failed gate means the hold is not scored; see failure handling):
   - `service_capacity.json` millicores match the table.
   - `resource_usage.csv` replica counts equal the pin on every sample (frontend 4; everything else 1). A leaf dropping Ready on the 1 s `grpc_health_probe` is an overload symptom: record it, keep the data.
   - All collector files present; `total.csv` rows ≥ 500; mesh span about 600 s.
   - **Sampling:** at least 90% of `service_inbound.csv` gaps are under 1.5 s.
8. Score each hold as it lands with the canon script (`python experiments/s2_both_off_canon.py 80 82` for the first three) and read the pass-bar rows. Decide the next hold by the rule below.
9. Restore before stopping: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, extra replicas back to 1, `reconcile_paper_cpu_limits`, sidecar request 100 m with no limit. Point the YAML at the next free slot with `scale_constraints: []` and no `paper_cpu_reconcile` key. Update `TestBothOffYamlRestored` in `experiments/test_topfull_cpu_quotas.py` to that slot. Commit everything this series changed, push the branch, then stop the three VMs.

PowerShell here-strings piped to `ssh ... bash -s` leave a trailing CR on the last line. If a command fails with `\r`, reissue it, or write the script with LF.

## Decision rule after run80-run82

| Result | Next hold |
|---|---|
| Exactly one hold is a blend | replay it as **run83**, then run84 as a second replay |
| More than one is a blend | replay the one with the larger chain-leaf overloaded ticks; run84 replays the other |
| No blend, at least one near-miss | run83 is one tweak on the nearest near-miss (below); run84 replays whichever of run83 or the near-miss looks better |
| Nothing close | stop; write up the three holds and the missing row |

Tweaks, one knob at a time:

- **Recommendations streak lost:** raise getproduct or getcart by 25-50 within the 650-700 ceiling, or drop checkout to 615 × 1 to stop its retries feeding recommendations.
- **Checkout streak lost:** lower checkout to 700 m, or raise postcheckout by 25-50.
- **Leaf cold with checkout hot:** lower email to 100 m, or payment to 100 m. Below 100 m the limit risks a pod that fails its readiness probe under normal load, which shows up as a replica-count gate failure.
- **Leaf hot but checkout starved (run 6 pattern):** raise checkout to 900 m or add one replica.

If run84 is a replay that also clears, stop. If a replay of a blend fails, the blend is not stable and the write-up says so.

## Failure handling

- **A gate fails:** capture `kubectl get events -n default --sort-by=.lastTimestamp` and `kubectl describe pod` for the pod, keep the folder, and do not relaunch on that slot. Bump to the next free slot and update the slot table here.
- **Infrastructure failure** (Pending pods, SSH death before Locust): stop the series until fixed.
- **`duplicate session: envoyretry`:** kill the stale tmux session on master and relaunch the same slot.
- **Sampling gate fails:** treat it as a collector problem (run 74-79 pattern), not a load result. Do not compare it to the ranking.

## Post-run analysis

Write one dated guide in `Guides and Info/`, copying the layout of [2026-09-27-s2-replica-cpu-runs-35-38.md](2026-09-27-s2-replica-cpu-runs-35-38.md) as described in [2026-09-27-s2-cpu-variant-handoff.md](2026-09-27-s2-cpu-variant-handoff.md). Read (a), (b), (c) from [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md) and leave that file unchanged. Add a **pass-bar table** at the top: one row per hold, columns for the four rows above with their values, and a blend / near-miss / miss verdict. Include run69, run10, run11 and run6 as reference columns, each with its own quota and replica count. Then:

1. Add a status bullet to `AGENTS.md` §4 and update the free-slot lines.
2. Add the blend (if any) to the ranking guide as a third lens entry, or note that no blend was found.

## Read next

- Ranking and lens definitions: [2026-09-30-s2-candidate-ranking-runs-1-79.md](2026-09-30-s2-candidate-ranking-runs-1-79.md).
- Terms (both-off hold, rejection streak, overloaded tick, independent pair, chain, valid sampling): [CONTEXT.md](../CONTEXT.md).
- Per-tag to service load model and the checkout retry-latching mechanism: [2026-09-25-s2-overload-user-count-calibration.md](../docs/superpowers/specs/2026-09-25-s2-overload-user-count-calibration.md).
- Hybrid table and run 69: [2026-09-29-s2-runs-60-70.md](2026-09-29-s2-runs-60-70.md).
- CPU tables: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).
- The procedure this follows: [2026-09-27-s2-cpu-variant-handoff.md](2026-09-27-s2-cpu-variant-handoff.md).
- Task-sized run plan: [2026-09-30-s2-lens-blend-holds.md](../docs/superpowers/plans/2026-09-30-s2-lens-blend-holds.md).

## Landed

run80 (C1, 325/80/100/90/5): recommendationservice streak 0, ov 17; checkoutservice streak 549, ov 579; emailservice streak 8, ov 17; paymentservice streak 1, ov 0.
