# Researcher conclusions on the final matrix and the S2/S3 replays (2026-10-17, updated 2026-10-18)

Corpus: `experiments/results/final_runs_results/` (60 holds plus the three clean `run3` re-runs) and the **replay holds for S2 and S3** (10 holds, `run3`, S2 `both_normal` is `run4`). The replay holds sit in the `analysis-runs-replay` worktree (`.worktrees/analysis-runs-replay/experiments/results/final_runs_results/`, branch `analysis-runs-replay`, last commit `a1dcd1f0`), not yet on `main`. All ten are logged clean in the replay log (`docs/superpowers/plans/2026-10-17-analysis-runs-replay-log.md` in that worktree) and I re-checked each (`health: ok`, throttle `ok` or `N/A: TopFull off`). **The S4A unconstrained replay was still running (1 of 5 done) and is not in this guide.** Deck: the WIP workshop deck, read with `.cursor/skills/project-researcher/extract_deck.py` on 2026-10-17. Clean rule: `health: ok` and throttle table not FLAGGED ([AGENTS.md](../../AGENTS.md) §6). Every number below is from `python experiments/analysis_score.py "<run_dir>"`, `python experiments/locust_goodput.py`, the TopFull cap tools (`experiments/topfull_cap_avg.py`, `topfull_cap_median.py`), or a file in the run folder. A verifier re-ran 58 cells of the first pass and 43 cells of the replay pass, and found no mismatch. The cap-tool numbers come from one subagent run and a second pass has not re-checked them.

**Status of the evidence.** S3 now has three repeats per arm and a reading I trust. S2 has two sessions that are **not poolable** (see "Finding: the S2 replay is a different system state"). S1, S4A and S4B are unchanged: two repeats per arm. Treat those verdicts as provisional.

## How to read the numbers

- **The scorer prints per-API numbers only** (goodput req/s, P95 ms, fail rate). There is no system total, so claims are per entry API. `postcheckout` and `getproduct` carry most of them. `locust_goodput.py` gives the same mean plus the median, and its mean equals the scorer's goodput in all 20 cells checked.
- **Reference scenarios.** S1 is the unconstrained version of S3 and S4B (same mix 175 / 30 / 70 / 90 / 5, checkout 800m instead of 200m, email at table value instead of 50m). It is the ceiling for both. The only other manifest difference is duration (S1 300 s, S3 and S4B 600 s), so compare steady-state rates, not totals. S4A unconstrained is the reference for S4A constrained.
- **`admitted_rps` in `topfull_throttle.csv` is the offered rate, not the admitted rate.** In `TopFull/.../proxy_online_boutique.go` each `Reject<api>` handler calls `logRequest()` before `limiter.Allow()`. Median `admitted_rps` is about 30 even when the cap is 6, in all holds checked. Entry rejections are therefore estimated as offered minus cap on capped seconds (an estimate, not a measurement). The throttle docs may need a correction; I did not edit them.
- **Flagged holds.** `analysis_s2_both_normal_run1` (RL STALL), `analysis_4a_constrained_both_normal_run1` (RL STALL) and `analysis_s1_both_burst_run2` (throttle FLAGGED) are not quoted as clean. Their clean `run3` re-runs are used.
- **Two S2 sessions.** "Session A" is the original S2 holds (run1, run2, and `both_normal` run2 and run3, 2026-10-16 and the morning of 2026-10-17). "Session B" is the S2 replay (2026-10-17 evening, after the VMs were restarted).
- **No both-off baseline exists in this matrix.** "RetryGuard helps" is relative to `tf_only`, and "TopFull costs goodput" is relative to `rg_only` (or S1).

## Finding: the S2 replay is a different system state

All five S2 replay holds ran the same YAML as the first two repeats (only `run_number` and `log_folder` differ), the same quotas (`effective_cpu_quotas` equals `paper_cpu_quotas`), the same four frontend replicas, and the same target rates. They still look different:

| S2 hold | `getproduct` goodput req/s | `getproduct` fail | `postcheckout` goodput req/s |
|---|---|---|---|
| Session A, `tf_only` run1, run2 | 188.3, 156.4 | 0.258, 0.368 | 21.6, 22.4 |
| Session B, `tf_only` run3 | 264.0 | 0.000 | 45.8 |
| Session B, `rg_only` normal run3 | 200.1 (mixed, see below) | 0.232 | 40.7 |
| Session B, `both_normal` run4 | 264.0 | 0.000 | 51.1 |
| Session B, `rg_only` burst run3 | 264.2 | 0.000 | 68.2 |
| Session B, `both_burst` run3 | 264.0 | 0.000 | 61.6 |

What changed is `recommendationservice`, not the load, the config or the controllers:
- In every session A hold it was slow and erroring at the same request rate (mean latency 365–485 ms, 27–99 errors/s, CPU about 930m of 1150m). TopFull's detector marked it overloaded 11–33% of the time, and TopFull then capped `getproduct` and `getcart` (31–100 capped reads, mean cap 186–225).
- In session B it was in the same slow state for the first five minutes of `rg_only_normal_run3` (latency 491–497 ms, 72–120 errors/s). RetryGuard turned `frontend → recommendationservice` retries off at 19:33:51 (rpr 2.88), the service recovered about three minutes later (19:37, latency 33–39 ms, 0 errors, CPU about 740m), and it **stayed healthy through the next four holds**, including `tf_only_run3` with retries on all the time. In those four, TopFull never marked `recommendationservice` overloaded and only capped `postcheckout`.
- `analysis_s2_both_normal_run3` ran the morning of 2026-10-17, before the VM stop, and was still in the slow state, so time of day is not the explanation.

**Interpretation, not proven from the files:** the service has two stable states (slow with retry amplification, healthy), and shedding recommendation retries tipped it into the healthy one for the rest of that VM session. Why the 2026-10-16 pods stayed slow through every 120 s cool-off is not explained.

**Consequences:**
1. **Do not pool session A and session B.** Compare variants within a session. Session B is the single-hold-per-arm comparison; session A is the two-hold comparison.
2. **`rg_only_normal_run3` mixes both states** inside one hold. Quote it as mixed, or split it at 19:37; keep it out of means.
3. **Session B's S2 is a different experiment.** `getproduct` and `getcart` are never the bottleneck there. The overload reduces to the checkout and email path, so S2 resembles S3 in session B.
4. **The persistence is a result in its own right** (retry suppression may push a service out of a slow state, and the effect outlasts the hold). One observation, not repeated.

---

# Part 1: per deck question

## Deck hypothesis (slide 3)

*Dynamic per-service retry control reduces retry storms and protects global goodput and resource use significantly better than static retries.*

- **Verdict:** partly supported.
- **Strength:** moderate.
- **Evidence:** retry volume drops sharply where retries storm. S3 `frontend → checkoutservice` retry delta is 214, 251 and 138 for `both_burst` against 3,954, 3,632 and 4,571 for `tf_only` (`final_runs_results/S3_targeted_bottleneck_*`, runs 1–3). S4A constrained, `productcatalogservice` retry delta 5,508 and 2,712 for `both_normal` run2 and run3 against 52,292 and 222,472 for `tf_only`. "Significantly better global goodput" is not supported: the gains are per API, and in S1 and S4A unconstrained nothing changes. No CPU or memory saving is shown (checkout CPU is at its cap in S3 in every arm: max 190–198m of 200m).
- **Rivals left:** which retry edge was shed (Q1 rival); in S2 the largest effect in the data was RetryGuard's side effect on `recommendationservice`'s state, not a goodput gain in the same session.
- **Missing:** a both-off baseline.

## 1. System-level gains

- **Verdict:** supported in S3 and for `postcheckout` in S2; unsupported (nothing to find) in S1 and S4A unconstrained.
- **Strength:** moderate to strong for S3 (3 of 3 repeats, 5 of 5 arms same order), moderate for S2 `postcheckout`, inconclusive for S2 `getproduct`.
- **Evidence, S3 against the S1 reference.** S1 `postcheckout` is 27.6 req/s with fail rate 0.000, P95 175–223 ms, retry delta 0, in every arm (`S1_normal_operation_*`, 11 holds). S3 (`checkoutservice` at 200m, mean CPU 115–156m, max 190–198m of 200m, so the cap binds) recovers a fraction of that:

| S3 arm (runs 1, 2, 3) | `postcheckout` goodput req/s | Share of S1's 27.6 | P95 ms | Fail rate |
|---|---|---|---|---|
| TopFull only | 3.9, 3.6, 5.0 | 13–18% | 892, 884, 889 | 0.836, 0.841, 0.790 |
| TopFull + RetryGuard, normal | 4.1, 3.7, 4.8 | 13–17% | 880, 892, 874 | 0.826, 0.842, 0.793 |
| TopFull + RetryGuard, burst | 7.8, 8.2, 9.7 | 28–35% | 535, 534, 494 | 0.718, 0.697, 0.639 |
| RetryGuard only, normal | 0.3, 0.4, 0.8 | 1–3% | 615, 613, 601 | 0.959, 0.959, 0.941 |
| RetryGuard only, burst | 0.2, 0.2, 0.5 | 1–2% | 597, 606, 607 | 0.964, 0.966, 0.951 |

  Per repeat, `both_burst` is 2.0, 2.3 and 1.9 times `tf_only`. Run3 is about 1 req/s higher in every arm (session effect), but the ratio and the order hold. Both TopFull arms stay far below S1: the best case is 35% of S1 goodput, and `postcheckout` P95 is still 2.2–3.1 times S1's. The other four APIs match S1 within noise (S3 `getproduct` 167.7–168.1 here against 161 in S1; the S1 hold is half the length, cause not checked). `both_normal` equals `tf_only` in all three repeats (zero toggles in all three), which sets the noise floor between two equal arms at up to about 1 req/s here.
- **Evidence, S2 (session B, same-session comparison; no unconstrained reference)** `postcheckout` goodput req/s, P95 ms, fail: `tf_only` 45.8, 796, 0.424; `both_normal` 51.1, 786, 0.370 (zero toggles); `both_burst` 61.6, 674, 0.261; `rg_only` burst 68.2, 718, 0.197. The order matches session A (`tf_only` 21.6 and 22.4 lowest, `rg_only` burst 50.7 and 50.2 highest, `both_burst` 43.0 and 35.3 in between). Burst arms beat `tf_only` in both sessions. `getproduct` goodput is **not** a usable comparison across arms in session B (264.0 to 264.2 in four arms) and in session A it tracks how often TopFull capped it (31 capped reads gave 229, 100 gave 171).
- **Evidence, S1 and S4A unconstrained:** all arms identical, zero toggles, retry delta zero. RetryGuard is quiet when nothing is overloaded, and that includes burst mode (all 11 S1 holds, all S4A unconstrained holds scored so far).
- **Rival explanations left:**
  - The S3 gain comes from RetryGuard turning off `frontend → checkoutservice` retries (first ON→OFF 14.1, 25.5 and 33.3 s after Locust started in runs 1–3), not from burst mode as such. `both_normal` never toggled, so the comparison cannot separate "burst mode" from "RetryGuard acted at all". Run3 shows one toggle was enough: it logged a single ON→OFF and still reached 9.7 req/s.
  - A repeat shifted by a session effect (run3 up about 1 req/s everywhere).
  - S2 session B is in the healthy `recommendationservice` state (see above), so it speaks for the checkout and email path only.
- **Missing:** a TopFull-only S3 hold with `frontend → checkoutservice` retries statically off. If it reaches about 8–10 req/s, the gain is retry removal, not the controller. For S2, a second hold in the slow state, or both-off holds in session B.

## 2. Controller interaction

- **Verdict:** supported: the two loops are complementary and neither broke the other. They improve each other in S3 burst. In S2 the picture is mixed: TopFull on top of RetryGuard costs `postcheckout` goodput.
- **Strength:** moderate.
- **Evidence:** in S3, TopFull alone survives (3.6–5.0 req/s) and RetryGuard alone collapses (0.2–0.8, fail 0.94–0.97), and the two together in burst mode are best (7.8–9.7). In S2 `postcheckout`, `rg_only` burst beats `both_burst` in all three pairs (50.7 against 43.0, 50.2 against 35.3, 68.2 against 61.6), so adding TopFull to RetryGuard burst lowered `postcheckout` goodput by 7.6 to 14.9 req/s in S2, while `getproduct` goodput was equal or higher with TopFull on in session A (235.5 and 207.8 against 203.7 and 206.5). No hold shows oscillation caused by the pair: `topfull_health.py` is `ok` for every quoted hold.
- **Surprise, S4B against the S1 reference.** S1 `postcheckout` is 27.6 for every arm, including TopFull only. In S4B (S1's load, `emailservice` at 50m) it is 27.6 and 27.6 for `rg_only` normal, 28.3 and 28.2 for `rg_only` burst, but 24.4 and 21.8 for `tf_only` (79–88% of S1). RetryGuard never toggled in S4B, so `rg_only` is effectively a no-controller arm and it equals S1. TopFull alone loses 12–21% of the goodput S1 shows it does not need to lose. TopFull's `postcheckout` cap sat below the 28.4 req/s offered load for 35% and 49% of seconds, and offered minus cap estimates 3.3 and 5.5 rejected req/s against 3.0 and 5.5 req/s more failures than `rg_only` (`S4B_topology_position_normal/tf_only/analysis_4b_tf_only_run1`, `run2`). With RetryGuard on, TopFull is uncapped more often (71–80% of seconds against 50–65%) and fails less (fail rate 0.059 and 0.102 normal, 0.079 and 0.062 burst).
- **Rival explanations left:** `rg_only` normal and burst differ 2x in S4B fail rate (0.040 against 0.017) with no toggles, which sets a noise floor of about 0.6 fail/s; the S2 `rg_only` over `both` order is three pairs, and `rg_only` run3 holds one session B arm only.
- **Missing:** an S4B both-off hold, an S2 both-off hold in session B, and a split of `postcheckout` failures into proxy 403 rejections and 5xx errors.

## 3. Combined equilibrium

- **Verdict:** supported in S3 burst (with TopFull on, a higher cap that did not undo the gain). Not shown in S2 once the session effect is removed.
- **Strength:** moderate for S3 burst, weak for S2.
- **Evidence** (mean cap on capped seconds, `postcheckout`, runs listed, from `topfull_cap_avg.py`; cap tools exclude stale reads and no-cap seconds):

| Scenario | TopFull only | Both, normal | Both, burst |
|---|---|---|---|
| S3 (runs 1, 2, 3) | 7.3, 6.6, 9.3 | 7.6, 6.4, 8.6 | 12.4, 12.8, 15.9 |
| S2 (A: runs 1, 2; B: run3) | 31.5, 36.3, 53.0 | 45.1, 46.9, 56.6 (runs 2, 3, 4) | 58.1, 49.3, 67.2 |
| S4B (runs 1, 2) | 20.3, 19.1 | 23.3, 23.8 | 21.1, 22.0 |

  In S3 the burst cap is 1.7 to 2.0 times TopFull-only's and `both_normal` equals TopFull only, so the effect belongs to the shed, not to RetryGuard being on. Estimated entry rejections fall with it: 66–76% of postcheckout offered load (TopFull only) against 46–57% (burst); the cap explains 79–89% of `postcheckout` Fail in S3. Goodput rose with the higher cap and the overload was not re-triggered. In S2 the direction holds inside each session (A: 31–36 against 45–58, B: 53.0 against 56.6 and 67.2) but `tf_only` run3 (53.0) exceeds three of the six `both` runs, so the gap does not separate across sessions.
- **Rival explanations left:** fewer retries lower the load TopFull sees and the cap rises for that reason, with RetryGuard's own action secondary; the cap is a controller output, so correlation with goodput is not an equilibrium test.
- **Missing:** per-second cap averages and a hold with the cap forced, to see if goodput follows the cap.

## 4. Topology beneficiaries

- **Verdict:** supported that the benefit is uneven. Only partly answered about position.
- **Strength:** weak to moderate.
- **Evidence:** RetryGuard acted in S2 (recommendations and checkout edges), S3 (checkout, mid-path), and S4A constrained (catalog edges and recommendations). It never toggled in S1, S4A unconstrained (scored so far) or S4B (`emailservice`, a leaf behind checkout). The S4B edge `frontend → checkoutservice` mean rpr was 0.023–0.106 in the eight holds the scorer captured, well below the 0.4 shed bar (per-tick maxima reached 1.04–1.57, short spikes that never held for the 20 s window), so there was no sustained storm to shed. S3 gave the largest, best repeated goodput change (Q1). S4A constrained saturates (catalog at 77–82m mean of 100m): `getproduct` goodput is 1.1–7.2 req/s against 47.7–48.0 in S4A unconstrained (2–15% of the reference), and no arm rescues it. The benefit follows retry volume more than position: services that saturated and produced retry storms benefited, leaf `emailservice` did not need it.
- **Rival explanations left:** position and capacity are confounded: S3 and S4A constrained differ in which service is capped, the capped value (200m, 100m) and the API mix, so position alone is not isolated.
- **Missing:** the same constraint applied at different positions on one load mix.

## 5. Chain propagation

- **Verdict:** not answerable from the matrix. A hint exists, and the S2 replay adds an accidental one.
- **Strength:** weak.
- **Evidence:** in S4A constrained, `both_normal` toggled only on the `frontend → recommendationservice` edge, yet the retry delta to `productcatalogservice` fell to 5,508 and 2,712 (`tf_only` 52,292 and 222,472). `postcart` goodput was 557.2 and 550.2 req/s (96–97% of the unconstrained 568–575 reference), against 325.2 and 213.2 for `tf_only` (37–57%). `both_burst` did not repeat it (275.7 and 494.4). In S2 session B, shedding `frontend → recommendationservice` retries in the first replay hold coincided with `recommendationservice` leaving its slow state, and `getproduct` and `getcart` went from capped and failing to uncapped and clean in all four later holds. That is relief at one service reaching the callers' API goodput, but it is one event, and it outlived the hold.
- **Rival explanations left:** the shed recommendation edge calls the catalog, so S4A is one-hop retry reduction, not upstream propagation of savings; `both_normal_run1` (not clean) scored 358.9; the S2 recovery might have happened without the toggle (the data only shows it followed it).
- **Missing:** per-service CPU on callers of the shed edge (only five Locust APIs exist, so "upstream" is coarse); a repeat of S2 session A's slow state with and without the recommendation shed.

---

# Part 2: per scenario slide (slides 30–36)

## Slide 30, Scenario 1

- **What it did:** flat load inside capacity, 300 s, mix 175 / 30 / 70 / 90 / 5, all CPU at table value. This is the reference for S3 and S4B.
- **Answers:** a sensitivity check that RetryGuard stays quiet (supports Q1).
- Findings (folder `S1_normal_operation_{normal,burst}/`):
  - All 11 holds have `health: ok`; the throttle table is FLAGGED only for `analysis_s1_both_burst_run2`, replaced by `analysis_s1_both_burst_run3`.
  - Goodput is flat across variants: getproduct 160.8–161.3, postcheckout 27.6–27.7, getcart 64.4–64.5, postcart 82.7–82.9, emptycart 4.6–4.7 req/s, fail rate 0.000.
  - RetryGuard normal, burst and both: zero toggles, retry delta zero.
  - P95 varies more across repeats than across variants (postcheckout 175–223 ms; the widest repeat gap is 45 ms in `tf_only`), so P95 differences under about 45 ms are noise.
  - CPU shows no variant effect (frontend mean 825–920m).
- **Chart:** `python experiments/graphs_tool.py "experiments/results/final_runs_results/S1_normal_operation_normal/tf_only/analysis_s1_tf_only_run1"`.

## Slide 31, Scenario 2

- **What it did:** sustained overload from t=0, mix 275 / 90 / 100 / 90 / 5, 600 s, Paper-C1. Two sessions: A (original holds) and B (replay), which are not pooled.
- **Answers:** Q1, Q2, Q3 (and Q5 as a side observation).
- Findings (folder `S2_sustained_overload_{normal,burst}/`):
  - **Session A, `postcheckout` goodput:** `tf_only` 21.6 and 22.4 (fail 0.700 and 0.685); `rg_only` normal 42.9 and 34.2; `rg_only` burst 50.7 and 50.2; `both_normal` (runs 2, 3) 29.0 and 31.3; `both_burst` 43.0 and 35.3.
  - **Session A, `getproduct`:** `tf_only` 188.3 and 156.4; `rg_only` normal 219.4 and 178.5; `rg_only` burst 203.7 and 206.5; `both_normal` 229.1 and 171.0; `both_burst` 235.5 and 207.8. The ranges overlap and `getproduct` tracks TopFull's capping time.
  - **Session B (replay run3, `both_normal` run4), `postcheckout` goodput:** `tf_only` 45.8; `both_normal` 51.1 (no toggles, so about 5 req/s is noise); `both_burst` 61.6; `rg_only` burst 68.2; `rg_only` normal 40.7 (mixed states). `getproduct` is 264.0–264.2 with fail 0.000 in all four of the others.
  - **Same order in both sessions:** burst arms above `tf_only`, `tf_only` lowest on `postcheckout`. `rg_only` burst is above `both_burst` in all three pairs (7.6 to 14.9 req/s).
  - **The session B state change** (recommendation retries shed at 19:33:51, service healthy from 19:37 for the next four holds) is the S2 slide's main caveat. A figure that shows it: `recommendationservice` latency over time in `analysis_s2_rg_only_normal_run3`.
  - Flagged: `analysis_s2_both_normal_run1` (RL STALL, 6 s after load end) is not quoted; its numbers are getproduct 186.4, P95 719.
- **Charts:** session A against B, `python experiments/multi_graphs_tool.py "…/S2_sustained_overload_normal/tf_only/analysis_s2_tf_only_run1" "…/S2_sustained_overload_normal/tf_only/analysis_s2_tf_only_run3"` (the replay path is under the worktree until merged), and the session B comparison `…/tf_only/analysis_s2_tf_only_run3` against `…/S2_sustained_overload_burst/both/analysis_s2_both_burst_run3`.

## Slide 32, Scenario 3

- **What it did:** S1's load with `checkoutservice` capped at 200m, 600 s.
- **Answers:** Q1, Q2, Q3, Q4. Reference: S1 `postcheckout` 27.6 req/s.
- Findings (folder `S3_targeted_bottleneck_{normal,burst}/`, three repeats per arm, table in Q1):
  - `both_burst` recovers 28–35% of the S1 goodput (7.8, 8.2, 9.7) with fail rate 0.718, 0.697, 0.639, against 13–18% for `tf_only` and `both_normal` (3.6–5.0).
  - `both_normal` is indistinguishable from `tf_only` (zero toggles in all three holds).
  - RetryGuard turns off `frontend → checkoutservice` retries 14.1, 25.5 and 33.3 s after load start; outbound retry delta 214, 251 and 138 against 3,632–4,571.
  - `rg_only` collapses to 1–3% of the S1 goodput (fail rate 0.94–0.97) with one ON→OFF per hold.
  - TopFull's `postcheckout` cap is higher in `both_burst` (mean 12.4, 12.8, 15.9) than in `tf_only` (7.3, 6.6, 9.3); `both_normal` matches `tf_only` (7.6, 6.4, 8.6).
  - All fifteen holds are clean. Run3 sits about 1 req/s above runs 1 and 2 in every arm.
- **Chart:** `python experiments/multi_graphs_tool.py "…/S3_targeted_bottleneck_normal/tf_only/analysis_s3_tf_only_run1" "…/S3_targeted_bottleneck_burst/both/analysis_s3_both_burst_run1" "…/S1_normal_operation_normal/tf_only/analysis_s1_tf_only_run1"` (S1 as the reference panel).

## Slide 33, Scenario 4

- **What it did:** an overview slide for the topology pair: 4A (gateway-adjacent catalog) and 4B (checkout-mediated email).
- **Answers:** Q4. Use slides 34–36 for numbers. One sentence is supported by the matrix: RetryGuard acted only where retries stormed (4A constrained), and not in 4A unconstrained or 4B.

## Slide 34, Scenario 4A constrained

- **What it did:** mix 50 / 20 / 50 / 600 / 5 with `productcatalogservice` at 100m, 600 s. Reference: 4A unconstrained.
- **Answers:** Q4, Q5.
- Findings (folder `S4A_topology_position_{normal,burst}/`, runs `analysis_4a_constrained_*`; two repeats, no replay):
  - Catalog saturates in all 11 holds (mean 77–82m, max 101–104m); `getproduct` goodput is 1.1–7.2 against 47.7–48.0 unconstrained.
  - `postcart` goodput: `both_normal` 557.2 and 550.2 (about 96–97% of the unconstrained 568–575); `tf_only` 325.2 and 213.2; `rg_only` normal 438.0 and 232.5; `rg_only` burst 491.3 and 294.9; `both_burst` 275.7 and 494.4.
  - Retry delta to the catalog: `tf_only` 52,292 and 222,472; `both_normal` 5,508 and 2,712.
  - `both_normal_run1` is RL STALL and not quoted; `both_normal_run3` replaces it.
  - Run-to-run spread is large; treat all but the retry-delta contrast as inconclusive.
- **Chart:** `python experiments/multi_graphs_tool.py "…/S4A_topology_position_normal/tf_only/analysis_4a_constrained_tf_only_run2" "…/S4A_topology_position_normal/both/analysis_4a_constrained_both_normal_run3"`.

## Slide 35, Scenario 4A unconstrained

- **What it did:** the same mix with plain Paper-C1, 600 s. It is the control for 4A constrained. (Replay holds were still in progress when this was written; the two-repeat numbers below are unchanged.)
- **Answers:** Q1 (null case).
- Findings (folder `S4A_topology_position_{normal,burst}/`, runs `analysis_4a_unconstrained_*`):
  - All 10 holds identical: getproduct 47.7–48.0, postcheckout 19.0–19.2, getcart 47.9–48.0, postcart 568.1–575.4 req/s, fail rate 0.000.
  - No toggles; the only retry delta anywhere is 1 on `checkoutservice` in `both_burst_run1`.
  - Catalog CPU mean 209–259m of 800m.
  - P95 spread (getproduct 186–287 ms) is not ordered by variant.
- **Chart:** `python experiments/graphs_tool.py "…/S4A_topology_position_burst/both/analysis_4a_unconstrained_both_burst_run1"`.

## Slide 36, Scenario 4B

- **What it did:** S1's load with `emailservice` capped at 50m, 600 s. Reference: S1.
- **Answers:** Q2, Q4.
- Findings (folder `S4B_topology_position_{normal,burst}/`, two repeats, no replay):
  - RetryGuard never toggled in any of the 10 holds; email runs at its 50m ceiling in every arm.
  - `postcheckout` goodput: `rg_only` 27.6, 27.6 normal and 28.3, 28.2 burst (equals S1's 27.6); `tf_only` 24.4 and 21.8 (fail 0.142 and 0.218); `both` normal 26.9 and 25.5, burst 26.3 and 26.9.
  - TopFull's cap binds in `tf_only` (below the 28.4 req/s offered load for 35% and 49% of seconds) and explains about 80% of the failures.
  - Chart for the slide: the `postcheckout` fail-rate gap between `rg_only` and `tf_only`, with S1 as the ceiling.
  - Two repeats; `both` normal spreads (fail 0.059 and 0.102).
- **Chart:** `python experiments/multi_graphs_tool.py "…/S4B_topology_position_normal/rg_only/analysis_4b_rg_only_normal_run1" "…/S4B_topology_position_normal/tf_only/analysis_4b_tf_only_run2"`.

---

# Closing sections

## Deck against repo

- **Slide 23:** S4A constrained caps the catalog at **100m**; the deck says 50m (the superseded 2026-10-13 lock). The unconstrained variant has no cap.
- **Slide 26:** S4A caps `productcatalogservice`, which is gateway-adjacent, not downstream. The "downstream" framing fits S4B, where nothing happened.
- **Slide 28:** "several" runs is 2 per arm for S1, S4A and S4B, 3 for S3, and for S2 two sessions that are not pooled. `tf_only` runs only under normal mode.
- **Slide 20:** zero toggles holds for the checkout edge in S2 session A `both_normal`. The recommendations edge did toggle (1–3 ON→OFF per category). In session B, `both_normal_run4` and S3 `both_normal_run3` logged none.
- **Slides 19 and 21:** all twelve values match [ADR 0008](../../docs/adr/0008-locked-retryguard-parameters.md). Normal mode omits the three burst keys.
- **Slide 25:** the title still reads "fix this title".

## Findings the questions did not ask about

- **S2 is not a stable benchmark.** The same YAML gave two different system states 24 hours apart (above). Any S2 claim must name its session.
- **RetryGuard may change a service's state, not just the retry count.** In the first replay hold, shedding `recommendationservice` retries preceded a recovery that lasted four more holds.
- **`admitted_rps` is the offered rate** (proxy code, see top). Any earlier write-up that reads it as admitted traffic is wrong.
- **TopFull alone costs goodput in S4B** relative to S1 and to `rg_only`. In S2, adding TopFull to `rg_only` burst lowered `postcheckout` in 3 of 3 pairs.
- **S2 `getproduct` goodput follows TopFull's capping time** more than the arm in session A.
- **S1 duration is 300 s**, S3 and S4B 600 s. S1's getproduct (161) sits below S3 and S4B (168) for a reason not checked.
- **Run order:** each scenario ran as a mirrored block (run1s, then run2s in reverse). The S3 and S2 replays ran in a different order and after a VM restart, which is the likeliest source of S3's +1 req/s and S2's state change.
- Three S4B cells are not captured: `both` normal and burst run2 edge rpr, and `emailservice` CPU in `rg_only` burst run1.
- Two zero-toggle RetryGuard-on holds (S2 `both_normal_run4`, S3 `both_normal_run3`) had large retry deltas (11,262 and 4,412): RetryGuard on, retries not shed.

## Next holds

Replay holds for S4A unconstrained are in progress. After that, in priority order (none has a slot yet; STATUS "Next free slots" shows `final_configs/` S4B at run 3, S1 at run 3):

1. S3 `tf_only` with `frontend → checkoutservice` retries statically off (separates retry removal from the controller). Needs a new config; no existing YAML does this.
2. A repeat of S2 session A's slow state: a fresh restart of `recommendationservice` followed by a `tf_only` hold, then `rg_only` burst, to see whether the slow state returns and whether RetryGuard clears it again.
3. An S4B both-off hold (separates TopFull's cap cost from the 50m email cap), and an S2 both-off hold in the healthy state.
4. A third S4A constrained hold per arm, to test the chain-propagation hint.

## Challenge it

Hand this file to grill-me in a second chat. The skeptic pass (first version) covered the S3 gain, the S4B cap cost and the S2 ordering; its conclusions are folded into the strength labels, and the replay data raised the S3 label.
