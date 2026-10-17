# Researcher conclusions on the 60-hold matrix (2026-10-17)

Corpus: `experiments/results/final_runs_results/` (60 holds plus the three clean `run3` re-runs). Deck: the WIP workshop deck, read with `.cursor/skills/project-researcher/extract_deck.py` on 2026-10-17. Clean rule: `health: ok` and throttle table not FLAGGED ([AGENTS.md](../AGENTS.md) §6). Every number below is from `python experiments/analysis_score.py "<run_dir>"` or a file in the run folder. A verifier re-ran 58 cells from this guide's tables and found no mismatch. Skeptic and cap-statistics passes are folded in.

**This is a two-repeat matrix.** The replay plan ([2026-10-17-analysis-runs-replay.md](../docs/superpowers/plans/2026-10-17-analysis-runs-replay.md)) adds a third hold per variant for S2, S3 and S4A unconstrained (run 4 for S2 `both_normal`). Treat every verdict as provisional until that data is in. S1, S4B and S4A constrained are not replayed.

## How to read the numbers

- **The scorer prints per-API numbers only** (goodput req/s, P95 ms, fail rate). There is no system total, so claims are per entry API. `postcheckout` and `getproduct` carry most of them.
- **Reference scenarios.** S1 is the unconstrained version of S3 and S4B (same mix 175 / 30 / 70 / 90 / 5, checkout 800m instead of 200m, email at table value instead of 50m). It is the ceiling for both. The only other differences in the manifests are duration (S1 300 s, S3 and S4B 600 s), so compare steady-state rates, not totals. S4A unconstrained is the reference for S4A constrained.
- **`admitted_rps` in `topfull_throttle.csv` is the offered rate, not the admitted rate.** In `TopFull/.../proxy_online_boutique.go` each `Reject<api>` handler calls `logRequest()` before `limiter.Allow()`. Median `admitted_rps` is about 30 even when the cap is 6, in all 20 holds checked. Entry rejections are therefore estimated as offered minus cap on capped seconds (an estimate, not a measurement). The throttle docs may need a correction; I did not edit them.
- **Flagged holds.** `analysis_s2_both_normal_run1` (RL STALL), `analysis_4a_constrained_both_normal_run1` (RL STALL) and `analysis_s1_both_burst_run2` (throttle FLAGGED) are not quoted as clean. Their clean `run3` re-runs are used. The `both_normal` S2 arm is therefore run2 and run3, and run3 ran a day later (2026-10-17) than the rest of that block.
- **No both-off baseline exists in this matrix.** "RetryGuard helps" is relative to `tf_only`, and "TopFull costs goodput" is relative to `rg_only` (or S1).

---

# Part 1: per deck question

## Deck hypothesis (slide 3)

*Dynamic per-service retry control reduces retry storms and protects global goodput and resource use significantly better than static retries.*

- **Verdict:** partly supported.
- **Strength:** weak to moderate.
- **Evidence:** retry volume drops sharply where retries storm: S3 `frontend → checkoutservice` retry delta 214 and 251 for `both_burst` against 3,503–3,994 for `both_normal` and `tf_only` (`final_runs_results/S3_targeted_bottleneck_*`). S4A constrained, `productcatalogservice` retry delta 5,508 and 2,712 for `both_normal` run2 and run3 against 52,292 and 222,472 for `tf_only`. "Significantly better global goodput" is not supported: the gains are per API, and in S1 and S4A unconstrained nothing changes. No CPU or memory saving is shown (checkout CPU is at its cap in S3 in every arm).
- **Rivals left:** run-to-run noise at n=2; which retry edge was shed (see Q1 rival).
- **Missing:** a both-off baseline, and the replay holds.

## 1. System-level gains

- **Verdict:** supported in S3, inconclusive in S2, unsupported (no effect to find) in S1 and S4A unconstrained.
- **Strength:** moderate for S3, inconclusive for S2.
- **Evidence, S3 against the S1 reference.** S1 `postcheckout` is 27.6 req/s with fail rate 0.000, P95 175–223 ms, retry delta 0, in every arm (`S1_normal_operation_*`, 11 holds). S3 (`checkoutservice` at 200m, mean CPU 116–156m, max 191–198m of 200m, so the cap binds) recovers a fraction of that:

| S3 arm (runs 1, 2) | `postcheckout` goodput req/s | Share of S1's 27.6 | P95 ms | Fail rate |
|---|---|---|---|---|
| TopFull only | 3.9, 3.6 | 13–14% | 892, 884 | 0.836, 0.841 |
| TopFull + RetryGuard, normal | 4.1, 3.7 | 13–15% | 880, 892 | 0.826, 0.842 |
| TopFull + RetryGuard, burst | 7.8, 8.2 | 28–30% | 535, 534 | 0.718, 0.697 |
| RetryGuard only, normal | 0.3, 0.4 | about 1% | 615, 613 | 0.959, 0.959 |
| RetryGuard only, burst | 0.2, 0.2 | about 1% | 597, 606 | 0.964, 0.966 |

Burst mode doubles TopFull's recovery, but both TopFull arms stay far below the S1 ceiling (best case 30% of goodput, P95 still about 2.4–3.1 times S1's). The other four APIs match S1 within noise (getproduct 167.8–168.1 here against 161 in S1; the S1 hold is half the length, cause not checked).
- **Evidence, S2** (no unconstrained reference, the load is above capacity by design): `getproduct` goodput `tf_only` 188.3 and 156.4; `rg_only` normal 219.4 and 178.5; `rg_only` burst 203.7 and 206.5; `both` normal (clean runs 2 and 3) 229.1 and 171.0; `both` burst 235.5 and 207.8 (`S2_sustained_overload_*`). All ranges overlap.
- **Evidence, S1 and S4A unconstrained:** all arms identical, zero toggles, retry delta zero. RetryGuard is quiet when nothing is overloaded, and that includes burst mode (all 11 S1 holds, all 10 S4A unconstrained holds).
- **Rival explanations left:**
  - S3's gain comes from RetryGuard turning off `frontend → checkoutservice` retries about 36 s into the hold, not from burst mode as such. `both_normal` never toggled, so the comparison cannot separate "burst mode" from "RetryGuard acted at all".
  - The two burst holds ran back to back (15:26Z and 15:45Z), so one good stretch of node conditions cannot be ruled out.
  - S2 `getproduct` goodput tracks how many seconds TopFull capped `getproduct` (31–100 capped reads across `both` holds, goodput 229 to 171), not which arm ran.
- **Missing:** a TopFull-only S3 hold with `frontend → checkoutservice` retries statically off. If it reaches about 8 req/s, the gain is retry removal, not the controller. For S2, at least five interleaved holds per arm, or goodput regressed on cap fraction. The replay plan's third hold per arm is the first step.

## 2. Controller interaction

- **Verdict:** supported, in the sense that the two loops are complementary and neither broke the other. Whether they "improve each other" is only shown for S3 burst.
- **Strength:** moderate.
- **Evidence:** in S3, TopFull alone survives (3.6–3.9 req/s) and RetryGuard alone collapses (0.2–0.4, fail rate 0.96), and the two together in burst mode are best (7.8, 8.2). In S2, `tf_only` is the weakest arm on `postcheckout` (21.6, 22.4 req/s; fail 0.700 and 0.685) and `rg_only` burst the best (50.7, 50.2). No hold shows oscillation caused by the pair: `topfull_health.py` is `ok` for every quoted hold, and TopFull cap direction changes per minute for `postcheckout` are in the same range with RetryGuard on (S2 `postcheckout`: 4.4 and 4.3 for `both` normal, 5.8 and 3.3 for `both` burst, against 4.3 and 3.9 for TopFull only).
- **Surprise, S4B against the S1 reference.** S1 `postcheckout` is 27.6 for every arm, including TopFull only. In S4B (S1's load, `emailservice` at 50m) it is 27.6 and 27.6 for `rg_only` normal, 28.3 and 28.2 for `rg_only` burst, but 24.4 and 21.8 for `tf_only` (79–88% of S1). RetryGuard never toggled in S4B, so `rg_only` is effectively a no-controller arm and it equals S1. TopFull alone loses 12–21% of the goodput S1 shows it does not need to lose. The cap-statistics pass shows why: TopFull's `postcheckout` cap sat below the 28.4 req/s offered load for 35% and 49% of seconds, and offered minus cap estimates 3.3 and 5.5 rejected req/s against 3.0 and 5.5 req/s more failures than `rg_only` (`S4B_topology_position_normal/tf_only/analysis_4b_tf_only_run1`, `run2`). With RetryGuard on, TopFull is uncapped more often (71–80% of seconds against 50–65%) and fails less (fail rate 0.059 and 0.102 normal, 0.079 and 0.062 burst). Even though RetryGuard never toggled, TopFull plus RetryGuard recovers part of the loss. That is not understood and needs the both-off hold below.
- **Rival explanations left:** `rg_only` normal and burst differ 2x in fail rate (0.040 against 0.017) with no toggles, which sets a noise floor of about 0.6 fail/s; the normal pair sat at the ends of the session (23:51Z and 02:49Z).
- **Missing:** an S4B both-off hold, and a split of `postcheckout` failures into proxy 403 rejections and 5xx errors.

## 3. Combined equilibrium

- **Verdict:** supported as a correlation: with RetryGuard on, TopFull settles at a higher cap without losing the gain. Not shown to be causal.
- **Strength:** weak.
- **Evidence** (mean fresh `postcheckout` cap, runs 1 and 2, `topfull_throttle.csv`):

| Scenario | TopFull only | Both, normal | Both, burst |
|---|---|---|---|
| S3 | 7.4, 6.7 | 7.7, 6.3 | 12.5, 12.7 |
| S2 | 33.1, 36.4 | 45.1, 47.5 (runs 2, 3) | 56.1, 48.7 |
| S4B | 20.3, 19.1 | 23.3, 23.8 | 21.1, 22.0 |

The goodput that went with the higher cap is in Q1. The cap stayed higher with std 3.3 and 2.9 in S3 burst, against 4.8 and 4.2 for TopFull only. Higher admission did not re-trigger the overload and undo the gain in S3 burst. The `getproduct` and `getcart` caps show no consistent RetryGuard effect. Cap means weight each fresh read equally.
- **Rival explanations left:** fewer retries lower the load TopFull sees and the cap rises for that reason, with RetryGuard's own action secondary; n=2.
- **Missing:** the replay holds for S2 and S3, plus per-second (not per-read) cap averages.

## 4. Topology beneficiaries

- **Verdict:** supported that the benefit is uneven. Only partly answered about position.
- **Strength:** weak.
- **Evidence:** RetryGuard acted in S2 (recommendations and checkout edges), S3 (checkout, mid-path), and S4A constrained (catalog edges and recommendations). It never toggled in S1, S4A unconstrained or S4B (`emailservice`, a leaf behind checkout). The S4B edge `frontend → checkoutservice` mean rpr was 0.023–0.106 in the eight holds the scorer captured, well below the 0.4 shed bar (per-tick maxima reached 1.04–1.57, short spikes that never held for the 20 s window), so there was no sustained storm to shed. S3 gave the largest goodput change (Q1). S4A constrained saturates (catalog at 77–82m mean of 100m): `getproduct` goodput is 1.1–7.2 req/s against 47.7–48.0 in S4A unconstrained (2–15% of the reference), and no arm rescues it. The benefit follows retry volume more than position: services that saturated and produced retry storms benefited, leaf `emailservice` did not need it.
- **Rival explanations left:** position and capacity are confounded: S3 and S4A constrained differ in which service is capped, the capped value (200m, 100m) and the API mix, so position alone is not isolated.
- **Missing:** the same constraint applied at different positions on one load mix.

## 5. Chain propagation

- **Verdict:** not answerable from the matrix. A hint exists.
- **Strength:** weak.
- **Evidence:** in S4A constrained, `both_normal` toggled only on the `frontend → recommendationservice` edge, yet the retry delta to `productcatalogservice` fell to 5,508 and 2,712 (`tf_only` 52,292 and 222,472). `postcart` goodput was 557.2 and 550.2 req/s (96–97% of the unconstrained 568–575 reference), against 325.2 and 213.2 for `tf_only` (37–57%). `both_burst` did not repeat it (275.7 and 494.4). Four of five arms use two holds, and the arm spread is large (`rg_only` normal 438.0 and 232.5).
- **Rival explanations left:** the shed recommendation edge calls the catalog, so that is one-hop retry reduction, not upstream propagation of savings; `both_normal_run1` (not clean) scored 358.9.
- **Missing:** per-service CPU on callers of the shed edge (only five Locust APIs exist, so "upstream" is coarse); a hold with RetryGuard acting on exactly one downstream edge.

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

- **What it did:** sustained overload from t=0, mix 275 / 90 / 100 / 90 / 5, 600 s, Paper-C1.
- **Answers:** Q1, Q2, Q3.
- Findings (folder `S2_sustained_overload_{normal,burst}/`):
  - TopFull only: getproduct 188.3 and 156.4, postcheckout 21.6 and 22.4 req/s, postcheckout fail 0.700 and 0.685 (`tf_only/analysis_s2_tf_only_run1`, `run2`).
  - RetryGuard only, normal: getproduct 219.4 and 178.5, postcheckout 42.9 and 34.2 (`rg_only/analysis_s2_rg_only_normal_run1`, `run2`).
  - RetryGuard only, burst: getproduct 203.7 and 206.5, postcheckout 50.7 and 50.2; tightest arm; ON→OFF 10 on the checkout edge in both holds.
  - Both, normal (clean runs 2 and 3): getproduct 229.1 and 171.0, P95 519 and 958 ms; toggles only on the recommendations edge (1 and 3 ON→OFF), none on checkout.
  - Both, burst: getproduct 235.5 and 207.8, P95 489 and 588 ms; 11 and 5 ON→OFF on the checkout edge.
  - Burst against normal: more reliable toggling, tighter `rg_only` spread. With two holds a spread is not an estimate (the `both` burst spread of 28 is close to `tf_only`'s 32).
  - Flagged: `analysis_s2_both_normal_run1` (RL STALL, 6 s after load end) is not quoted; its numbers are getproduct 186.4, P95 719.
- **Chart:** `python experiments/multi_graphs_tool.py "…/S2_sustained_overload_normal/tf_only/analysis_s2_tf_only_run1" "…/S2_sustained_overload_burst/both/analysis_s2_both_burst_run1"`.

## Slide 32, Scenario 3

- **What it did:** S1's load with `checkoutservice` capped at 200m, 600 s.
- **Answers:** Q1, Q2, Q3, Q4. Reference: S1 `postcheckout` 27.6 req/s.
- Findings (folder `S3_targeted_bottleneck_{normal,burst}/`, table in Q1):
  - `both_burst` recovers 28–30% of the S1 goodput with fail rate 0.718 and 0.697, against 13–15% for `tf_only` and `both_normal`.
  - `both_normal` is indistinguishable from `tf_only` (zero toggles in both holds).
  - RetryGuard turns off `frontend → checkoutservice` retries about 36 s into each `both_burst` hold; outbound retry delta 214 and 251 against 3,503–3,994.
  - `rg_only` collapses to about 1% of the S1 goodput (fail rate 0.96) with one ON→OFF per hold.
  - TopFull's `postcheckout` cap is higher and more stable in `both_burst` (mean 12.5 and 12.7, std 3.3 and 2.9) than in `tf_only` (7.4 and 6.7, std 4.8 and 4.2).
  - All ten holds are clean.
- **Chart:** `python experiments/multi_graphs_tool.py "…/S3_targeted_bottleneck_normal/tf_only/analysis_s3_tf_only_run1" "…/S3_targeted_bottleneck_burst/both/analysis_s3_both_burst_run1" "…/S1_normal_operation_normal/tf_only/analysis_s1_tf_only_run1"` (S1 as the reference panel).

## Slide 33, Scenario 4

- **What it did:** an overview slide for the topology pair: 4A (gateway-adjacent catalog) and 4B (checkout-mediated email).
- **Answers:** Q4. Use slides 34–36 for numbers. One sentence is supported by the matrix: RetryGuard acted only where retries stormed (4A constrained), and not in 4A unconstrained or 4B.

## Slide 34, Scenario 4A constrained

- **What it did:** mix 50 / 20 / 50 / 600 / 5 with `productcatalogservice` at 100m, 600 s. Reference: 4A unconstrained.
- **Answers:** Q4, Q5.
- Findings (folder `S4A_topology_position_{normal,burst}/`, runs `analysis_4a_constrained_*`):
  - Catalog saturates in all 11 holds (mean 77–82m, max 101–104m); `getproduct` goodput is 1.1–7.2 against 47.7–48.0 unconstrained.
  - `postcart` goodput: `both_normal` 557.2 and 550.2 (about 96–97% of the unconstrained 568–575); `tf_only` 325.2 and 213.2; `rg_only` normal 438.0 and 232.5; `rg_only` burst 491.3 and 294.9; `both_burst` 275.7 and 494.4.
  - Retry delta to the catalog: `tf_only` 52,292 and 222,472; `both_normal` 5,508 and 2,712.
  - `both_normal_run1` is RL STALL and not quoted; `both_normal_run3` replaces it.
  - Run-to-run spread is large; treat all but the retry-delta contrast as inconclusive.
- **Chart:** `python experiments/multi_graphs_tool.py "…/S4A_topology_position_normal/tf_only/analysis_4a_constrained_tf_only_run2" "…/S4A_topology_position_normal/both/analysis_4a_constrained_both_normal_run3"`.

## Slide 35, Scenario 4A unconstrained

- **What it did:** the same mix with plain Paper-C1, 600 s. It is the control for 4A constrained.
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
- Findings (folder `S4B_topology_position_{normal,burst}/`):
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
- **Slide 28:** "several" runs is 2 per arm (3 for the three re-run cells), and `tf_only` runs only under normal mode.
- **Slide 20:** zero toggles holds for the checkout edge in S2 `both_normal`. The recommendations edge did toggle (1–3 ON→OFF per category). Say "checkout".
- **Slides 19 and 21:** all twelve values match [ADR 0008](../docs/adr/0008-locked-retryguard-parameters.md). Normal mode omits the three burst keys.
- **Slide 25:** the title still reads "fix this title".

## Findings the questions did not ask about

- **`admitted_rps` is the offered rate** (proxy code, see top). Any earlier write-up that reads it as admitted traffic is wrong.
- **TopFull alone costs goodput in S4B** relative to S1 and to `rg_only` (Q2). This is the strongest surprise in the matrix.
- **S2 goodput follows TopFull's capping time** more than the arm: among TopFull-on holds, 31 capped `getproduct` reads gave 229, 100 gave 171.
- **S1 duration is 300 s**, S3 and S4B 600 s. S1's getproduct (161) sits below S3 and S4B (168) for a reason not checked.
- **Run order:** each scenario ran as a mirrored block (run1s, then run2s in reverse). S2 `both_normal_run3` ran the next day. Time-of-day effects are cancelled for most arms, not for that one.
- Three S4B cells are not captured: `both` normal and burst run2 edge rpr, and `emailservice` CPU in `rg_only` burst run1.

## Next holds

The replay plan covers S2, S3 and S4A unconstrained (run 3, S2 `both_normal` run 4, under `experiments/configs/analysis_runs_replay/`). Beyond it, in priority order (none has a slot yet; STATUS "Next free slots" shows `final_configs/` S4B at run 3 and S1 at run 3):

1. S3 `tf_only` with `frontend → checkoutservice` retries statically off (separates retry removal from the controller). Needs a new config; no existing YAML does this.
2. S4B both-off (separates TopFull's cap cost from the 50m email cap). Needs a both-off config.
3. A third S4A constrained hold per arm, to test the chain-propagation hint.
4. A third S4B and S1 hold only if the above shows them changing.

## Challenge it

Hand this file to grill-me in a second chat. The skeptic pass covered claims A (S3 gain), B (S4B cap cost) and C (S2 ordering); the verdict labels above are its output.
