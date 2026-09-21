# S1–S6 methodology rework + recalibration battery design (2026-09-21)

> Closes the decisions needed by
> [2026-09-21-s1-s6-loadgen-numbers-remaining-work.md](2026-09-21-s1-s6-loadgen-numbers-remaining-work.md)
> §1 (fresh calibration pass), §2 (S1–S6 methodology rework), and §3
> (YAML rewiring mechanics). Reached via an interactive grilling session
> (this doc is the write-up of that session's settled decisions), same
> pattern as the two prior migration design docs. **Nothing in this doc has
> been applied to `experiments/configs/`, `topfull_cpu_quotas.py`,
> `run_scenario.py`, or the live cluster — this is a design proposal.**
> §3/§3b (the recalibration battery) is explicitly the first thing to
> *execute*, not something this doc's writing already did.

Related: [RON-NEZER-BASE-MIGRATION.md](../../../Guides%20and%20Info/RON-NEZER-BASE-MIGRATION.md),
[2026-09-20-ron-nezer-base-migration-design.md](2026-09-20-ron-nezer-base-migration-design.md)
§8 (the deferral this doc resolves),
[2026-09-21-loadgen-shape-ron-migration-design.md](2026-09-21-loadgen-shape-ron-migration-design.md)
§3 (the other half of the deferral — loadgen numbers, bundled with this),
[experiments/capacity/README.md](../../../experiments/capacity/README.md)
(the frozen-capacity table this doc's §3 battery replaces),
`CONTEXT.md` (Capacity beliefs / Targeted-bottleneck sizing — new terms this
doc settles).

---

## 1. Decision summary

| # | Decision | Answer |
|---|---|---|
| 1 | Calibration methodology | **Hybrid**: a rough model-based starting guess (from `mu_sat`, but only reused *at the exact CPU value it was measured at* — never extrapolated across CPU values), always confirmed with a live ramp-and-observe check before locking a number. |
| 2 | `capacity_frozen.json` | **Full re-freeze required.** All four existing 50m freezes predate the Ron-Nezer migration (dated 2026-09-19) and measured the target service in isolation against paired services still at old paper-quota headroom values that no longer exist. Not reusable as-is. |
| 3 | Per-tag calibration independence | Calibrate all five Locust tags independently per scenario — matches the already-adopted independent-swarm loadgen shape. |
| 4 | Locust throughput model | Confirmed live on `topfull-load`: `WebsiteUser.wait_time = constant_throughput(1)`. Under closed-loop load, `user_count` for a tag ≈ its target offered rps — calibration is "pick a target rps per tag," not a search procedure. |
| 5 | S3/S4A/S4B bottleneck mechanism | Switch from `cpu_limit_fraction` (a fraction of an already-shrunk, migration-trimmed number) to a real **absolute `cpu_limit_millicores: 50`** constraint kind — reuses the one CPU point each target service has trustworthy `mu_sat` data for, applied identically across all three targets ("limit different services in a similar way"). See [ADR-0006](../../adr/0006-absolute-bottleneck-cap-not-fraction.md). |
| 6 | S4A vs. `productcatalogservice` HPA | **Enable HPA on productcatalog, universally** (not S4A-only) — matches Ron's own setup more faithfully (he had an HPA file for it too, same family as frontend's) and is orthogonal to how the CPU cap is applied (K8s CPU limits are always per-pod-template; a bottleneck cap already applies identically to however many replicas exist). `maxReplicas: 2`, **no pre-emptive CPU re-trim** — see §4 and [ADR-0005](../../adr/0005-productcatalog-hpa-max-replicas-2.md). |
| 7 | Recalibration battery scope | **Two halves.** Bottleneck-cap half: 5 live runs (frontend, checkoutservice, productcatalogservice, paymentservice refrozen at 50m under the current topology, plus one unconstrained reference run). System-load half: up to 3 dry-run iterations each for S1/S2/S6. Order and specifics in §3/§3b. |
| 8 | Reference-load strategy | Try **one shared** bottleneck reference load across S3/S4A/S4B first (cheaper — one verification run); fall back to three separate per-scenario reference loads only if the shared one doesn't satisfy "target saturates when capped, others stay healthy when not" for all three. |
| 9 | Session scope | Design-only for this doc; live VM runs happen in a following execution session (this project's established grill → design → implementation pattern), except where a decision genuinely can't be settled without one — none were, this time; all live checks done during grilling (SSH facts, `kubectl` reads) were read-only. |
| 10 | S1/S2/S6 calibration methodology | **Empirical-only** (no `mu_sat` model — none trustworthy exists at full, uncapped CPU). Start from each scenario's current YAML numbers, run live, check against target criteria (§3b), adjust, repeat — capped at **3** tries per scenario this session. |
| 11 | S1's target criterion | **Unchanged from the eval deck** (Slide 11): zero Layer A `overloaded`, zero RetryGuard-kind overload on any service, baseline≈RetryGuard statistically. Not redefined as "normal traffic that can trip thresholds" — that would contradict the deck's own stated objective for this scenario. |
| 12 | S2's target criterion | **Qualitative combination, no fixed service count.** RetryGuard-kind overload on "several" services (no target number — Online Boutique's topology may not support a specific count), TopFull Layer A engaging heavily, and real (non-trivial) retry volume on the stressed edges. Judged by comparing several live candidate loads against each other, not a single pass/fail threshold. |
| 13 | S6's target criterion | Derived from S2's (decision 12), reached within the shorter 300s peak window instead of 600s; recovery phase (≈25% of peak) drops rejection back under threshold so `OFF→ON` can fire. |
| 14 | Old-number reuse risk | Frontend's HPA (1→4 replicas) is new since the old S1/S2/S6 numbers were chosen — those numbers might no longer produce the intended load character at all (e.g. S2's old load might no longer reach ρ>1 once frontend can scale out). Flagged explicitly (§3b), handled as a normal part of the live-adjustment loop, no special mechanism. |
| 15 | YAML rewiring — what's decidable now vs. number-blocked | Script-pointing (`online_boutique_create_v2.sh`, drop `create2.sh`), the `cpu_limit_millicores` mechanism swap, and dropping the trickle pattern are decidable now (§6 below) — none depend on calibration results. Only the real `user_counts`/`spawn_rate` values and the `run_number`/`log_folder` bump are genuinely blocked on the battery's results. |

---

## 2. Why the old numbers/mechanism don't carry over

### 2a. `cpu_limit_fraction` on an already-shrunk table produces untested absolutes

`scale_constraints` computes `millicores_from_fraction(paper_limit_for(dep), fraction)`, where `paper_limit_for()` now returns the **Ron-config trimmed** value (checkout 615m, productcatalog 1535m, payment 155m — confirmed live via `kubectl get deploy`, matches `topfull_cpu_quotas.py` exactly). The existing S3/S4A/S4B YAMLs still carry `cpu_limit_fraction: 0.1` with docstrings citing pre-migration paper numbers ("checkout 1000m→100m", "productcatalog 500m→50m", "payment 1000m→100m") — stale comments describing a calculation the code no longer performs. The code path already computes the *new*, smaller absolutes (61.5m / 153.5m / 15.5m) — but those specific values have **no calibration data behind them at all**. Switching to an absolute `cpu_limit_millicores: 50` for all three instead deliberately lands on the one CPU point each service already has trustworthy, non-`low_confidence` saturation data for (§2b), and applies the "similar treatment across services" the targeted-bottleneck design always wanted, without inventing three new untested numbers.

### 2b. `mu_per_millicore` doesn't extrapolate across CPU values — but is directly usable at the exact value it was measured at

Two independent two-point comparisons in `capacity_frozen.json`'s history: checkoutservice `10.82` (at 50m) vs. `0.1615` (at 1000m) — 67×; paymentservice similarly ~37×. Both diverge in the *same direction* (much higher throughput-per-millicore at the smaller CPU limit), which is too consistent to be measurement noise — most likely a real Linux CFS CPU-quota nonlinearity at very small limits (a 50m limit gets a much smaller, burstier slice of each 100ms scheduling period than a 615m or 1000m limit does). **Consequence**: `mu_per_millicore` cannot be trusted to predict saturation at a *different* CPU value than it was frozen at — but it's exactly the right tool for predicting saturation *at* the value a scenario is actually going to cap the service to. Since decision 5 puts all three targets at the same 50m cap the existing calibration YAMLs already used, that calibration data is directly reusable *as a starting guess*, not as something to extrapolate.

Checked directly: `scenario_calibration_checkout_constrained_50m.yaml` / `scenario_calibration_payment_constrained_50m.yaml` ran `postcheckout: 500` (heavy, everything else light) against the 50m cap; `scenario_calibration_productcatalog_constrained.yaml` ran `getproduct: 800` (heavy) against its own 50m cap. These aren't synthetic probes — they're the same real call-path traffic S3/S4A/S4B already use, already demonstrated (via the `mu_sat` gate firing, non-`low_confidence`) to drive those services past saturation at exactly the cap value decision 5 adopts. So `postcheckout: 500` / `getproduct: 800` are the right **starting guesses** for the recalibration battery (§3) and, if they still saturate under the current topology, likely close to final numbers for S3/S4A/S4B's targeted tag.

### 2c. Why the old freezes still don't carry over, even at the same 50m target value

All four existing freezes are dated 2026-09-19 — before the Ron-Nezer migration (2026-09-20→21). Two things changed since, independent of the target service's own cap:

- **Every *other* service's CPU also shrank** ~77% in the migration. The old checkout-at-50m freeze ran with paymentservice deliberately held at old "paper 1000m" (artificial headroom, to isolate checkout's own ceiling) — but paymentservice's real Ron-config production value is now 155m. If S3 actually runs with payment at its real 155m (not an artificial 1000m), payment itself might become a secondary bottleneck under the same `postcheckout: 500` load, changing what genuinely saturates checkout first. This can only be found by re-measuring under the real topology, not by reusing the old number.
- **Frontend now has a live HPA** (created during the migration, after all four September freezes) — the frontend freeze was measured single-replica, pre-HPA. Reusing it without re-checking risks silently contaminating a single-replica ceiling reading with mid-calibration autoscaling if the calibration YAML doesn't explicitly pin HPA off.

So: full re-freeze (decision 2), and specifically **not** re-inflating the paired/helper service back to an artificial "old paper" headroom value during the checkout/payment calibrations — measure under the real Ron-config topology (§3b) so the numbers describe the same conditions S3/S4A/S4B will actually run under. If a helper service also saturates, that's a compound-bottleneck finding to report, not something to engineer away.

### 2d. Why productcatalog HPA doesn't need a different bottleneck mechanism

Considered and rejected during grilling: building a CPU-independent bottleneck (Istio fault-injection delay/abort, or a `DestinationRule` circuit breaker) specifically so HPA "can't just cancel out" a CPU-based cap. Rejected — not because it's technically wrong, but because it changes what the scenario is *about*, which was never in scope for this rework; S3/S4A/S4B stay "cap one service's CPU and watch it saturate," identically to each other. Kubernetes CPU limits are inherently per-pod-template regardless of replica count, so the *existing* `cpu_limit_millicores: 50` cap already applies to every productcatalog replica HPA might add — no new mechanism needed for that. The open part was only ever "should productcatalog be allowed to scale out at all," which is decision 6/§4, not a bottleneck-mechanism question.

---

## 3. The recalibration battery

**Order** (300s+ cool-off between runs, matching the September battery's precedent):

1. **Frontend, 50m, HPA pinned off for the hold.** Single-replica isolation — the calibration is measuring one replica's ceiling; that's a different question from "how does frontend behave with HPA on," which is answered separately by just running real scenarios once frontend's normal cap (1150m) and HPA are both live.
2. **Checkoutservice, 50m, paymentservice at its real 155m** (not artificially bumped). Starting load guess: `postcheckout: 500` (from §2b), everything else light, matching the existing calibration YAML's shape.
3. **Paymentservice, 50m, checkoutservice at its real 615m.** Same load shape, mirrored target.
4. **Productcatalogservice, 50m, HPA pinned off for this specific hold** (even though decision 6 enables it generally — same single-replica-isolation reasoning as frontend). Starting load guess: `getproduct: 800`.
5. **Bottleneck reference load, unconstrained (`scale_constraints: []`).** Starting candidate (decision 8's shared-first attempt): `postcheckout: 500, getproduct: 800, getcart: 50, postcart: 50, emptycart: 50` — the two heavy tags pulled directly from runs 2–4's starting guesses, cart family left light so it doesn't dominate. Check: does everything *other* than checkout/productcatalog/payment stay healthy at this load with nothing capped? If yes, this one recipe becomes the shared reference for S3/S4A/S4B. If something else (most likely cartservice, since checkout calls it) gets pulled into overload as a side effect of combining two heavy tags, fall back to three separate reference loads instead (decision 8).

Each run's `mu_sat` (or, for run 5, plain rejection/goodput/CPU health per service) determines whether the starting guesses need adjusting before they become the real S3/S4A/S4B `locust.user_counts`.

### 3a. What this half of the battery does not determine

- S1, S2, S6's numbers — no `mu_sat` model exists at full (uncapped) CPU for any service, so this is a genuinely different method, covered separately in §3b (this was previously "deferred" — see §5 for why that changed).
- Whether `capacity_frozen.json`'s numbers are worth trusting for a full-CPU (non-bottleneck) rho diagnostic — that's a different, larger battery (one full-CPU hold per service, no target-service constraint at all) and stays out of scope here, same as the prior recalibration's scope decision. Note this is a *different* question from §3b: §3b sizes S1/S2/S6's load levels empirically without ever needing a per-service `mu_per_millicore` number; a rho *diagnostic* for the eventual written report is a separate, optional effort.

### 3b. System-load calibration: S1, S2, S6 (empirical-only, no model input)

No trustworthy `mu_sat`/`mu_per_millicore` number exists at any service's *normal* (uncapped) Ron-config CPU — the only prior full-CPU freezes (`calibration_checkout_payment_full_cpu_run1`) are flagged in `experiments/capacity/README.md` as reset-timeout artifacts, not real saturation, and predate the migration regardless. So S1/S2/S6 skip the model-based starting guess entirely and go straight to live ramp-and-observe, per decision 10.

**Method, per scenario:**

1. Run at the scenario's **current** (soon-to-be-legacy) YAML numbers, unchanged, as the first try.
2. Check the result against that scenario's target criterion (below).
3. If it misses, adjust and re-run. **Capped at 3 tries per scenario this session** (decision 20/Q20); if still unresolved after 3, leave it as an open item for a follow-up session rather than open-ended VM time.

**Target criteria** (decisions 11–13):

- **S1 — unchanged from the eval deck** (`context/Evaluating_RetryGuard_on_TopFull.md` Slide 11): zero Layer A `overloaded` (no service's `topfull_detect.csv` ever flags it), zero RetryGuard-kind overload on any service (no service's `Δ(5xx+resets)/Δtotal` on `service_inbound.csv` sustains > 0.20 for 30 consecutive samples), baseline and RetryGuard arms statistically indistinguishable. Explicitly **not** redefined as "normal traffic that occasionally trips a threshold" — that would contradict the deck's own stated objective, and TopFull's Layer A doesn't have a "soft throttle" distinct from the binary `overloaded` flag to hang a looser definition on anyway.
- **S2 — qualitative combination, no fixed service count.** Online Boutique's topology may not support a specific "N services overloaded" target, so judge candidates against each other rather than a single pass/fail number:
  - **(a)** RetryGuard-kind overload (as defined above) fires on "several" of the 9 `CONTROLLED_SERVICES` — no fixed target count.
  - **(b)** TopFull's Layer A engages heavily — `topfull_detect.csv` shows `overloaded=1` for multiple services across a large fraction of the 600s hold, and `topfull_throttle.csv`'s admitted rate sits meaningfully below the offered rate.
  - **(c)** Real, non-trivial retry volume on the stressed edges in `service_edges.csv` — a storm, not noise.
  - Pick the load level whose (a)/(b)/(c) picture looks most convincingly "overloaded" among the candidates actually tried, not the first one that clears an arbitrary bar.
- **S6 — derived from whatever S2 settles on**, reached within the shorter 300s peak window (S6's peak phase gets half the time S2's flat hold does, so needs to ramp faster to the same character), then the ≈25%-of-peak recovery phase drops rejection back under the RetryGuard threshold long enough for `OFF→ON` to actually fire.

**Explicit risk, flagged not hidden** (decision 14): frontend's HPA (1→4 replicas) postdates when the current S1/S2/S6 numbers were originally chosen. It's plausible the old S2/S6 peak numbers no longer produce ρ>1 at all once frontend can scale out — i.e. the first live try might come back suspiciously healthy, needing a much bigger jump than a normal "nudge the number a bit" adjustment. Handled as a normal part of the try-adjust-retry loop (step 3 above), not a special case.

---

## 4. Productcatalog HPA: budget and risk

ADR-0003's arithmetic already lands at **13,360m app-container demand against a ≈13,350m budget** at frontend's full 4-replica scale-out — already at the edge with zero spare headroom. Adding a 2nd productcatalog replica (+1,535m app + 100m sidecar) would only fit today if frontend simultaneously *isn't* at its own max — which, per the same logic that already governs S3/S4A/S4B ("moderate global load, one bottleneck saturated," not a full-system overload), is the expected case for S4A specifically.

**Decision: accept this without pre-emptive re-trim.** Options considered:

1. **(Adopted)** No re-trim; rely on S4A's load character keeping frontend's replica count low; validate empirically with `kubectl describe node topfull-worker-1` during the actual S4A dry run (the same validation habit the original HPA rollout already used).
2. Uniform re-trim of all 11 services (~89% of the current already-trimmed table) to guarantee headroom regardless of what else is happening — rejected: shrinks every scenario's headroom generally, including S1/S2 where we specifically don't want extra fragility, to guard against a combination (frontend maxed *and* productcatalog maxed *simultaneously*) that's unlikely to occur in the scenarios that would actually enable productcatalog's HPA.
3. Lower frontend's own ceiling to free room — rejected, would blunt frontend's own already-settled HPA design for a productcatalog-specific concern.

**Risk this creates, explicitly**: if a future scenario ever does drive both frontend and productcatalog to simultaneous max replica count, pods could go `Pending` (unschedulable) rather than actually scaling out — a silent capacity failure, not a crash, that could look like "the bottleneck held" when it's actually "the node ran out of room." **Action item**: once implemented, add a note to [RON-NEZER-BASE-MIGRATION.md](../../../Guides%20and%20Info/RON-NEZER-BASE-MIGRATION.md) (§4c/§5 area, alongside the existing frontend-HPA-ceiling caveat) flagging this specific overcommit risk, so a future agent debugging an unexplained "didn't scale" result checks node scheduling pressure before assuming the scenario mechanism itself failed. See [ADR-0005](../../adr/0005-productcatalog-hpa-max-replicas-2.md).

---

## 5. YAML rewiring (tracker §3) — what's decidable now vs. genuinely number-blocked

Revisited during grilling: most of tracker §3 doesn't actually depend on calibration results and can be decided now (decision 15).

**Decidable now, applies to all 16 scenario files uniformly:**

- Point every `locust.scripts` list at `online_boutique_create_v2.sh` only; drop `online_boutique_create.sh` + `online_boutique_create2.sh`. Already fully supported — `run_scenario.py`'s `_launch_locust()` already dual-exports `EMPTYCART` alongside the legacy `CART` (loadgen-shape migration), so this is a pure config change, no code change needed.
- No replacement for `create2.sh`'s trickle pattern — already decided (loadgen-shape [ADR-0004](../../adr/0004-loadgen-shape-not-literal-numbers.md)), unaffected by anything in this doc.
- S3/S4A/S4B's `scale_constraints` swap to `cpu_limit_millicores: 50` (decision 5) — mechanically part of this same YAML-rewiring pass, not a separate edit later.

**Genuinely blocked on the battery's results (§3/§3b):**

- The real `locust.user_counts`/`spawn_rate` values for all 16 files (S3/S4A/S4B from §3's starting guesses as adjusted; S1/S2/S6 from §3b's live iteration; S5's four files just inherit whatever S6 settles on, varying only `interval_samples`).
- `run_number`/`log_folder` — bump to "whatever's next-free at execution time" (per `AGENTS.md` §6's running list), not a number fixable today since other work may bump slots in between.

**Also on disk, not in the 16, not decided here** (tracker §3's own note, unchanged): `scenario_2_baseline_no_topfull.yaml` and the `scenario_calibration_*.yaml` files — decide their launcher rewire separately, later.

---

## 6. What's still deferred (not resolved by this doc)

- **Fresh campaign to replace `campaign_48/`** — tracker §5, last in the dependency order, unaffected by this doc beyond being one step closer.
- **Whether `capacity_frozen.json` is trustworthy for a full-CPU rho diagnostic** (as opposed to the bottleneck-cap value this doc's §3 battery targets, or §3b's model-free empirical sizing) — explicitly out of scope (§3a).
- **Deploying v2 for real use** (tracker §4) — mechanical follow-on once §5 above is actually applied to the YAMLs; not a design decision.

Everything else the original tracker listed as open (S1/S2/S5/S6 numbers' methodology, the full 16-file YAML rewiring plan) is now decided by §3b/§5 above — only the *execution* (running the battery, writing the resulting numbers in) remains.

---

## 7. Implementation checklist (designed here, not yet executed)

| # | Change | Where |
|---|---|---|
| 1 | Add `cpu_limit_millicores` as a new `scale_constraints` method (absolute, not fraction-derived) | `experiments/topfull_cpu_quotas.py` (`validate_scale_constraints`, `effective_cpu_quotas`), `experiments/run_scenario.py` wherever it dispatches on `method` |
| 2 | Switch `scenario_3_{baseline,retryguard}.yaml`, `scenario_4a_{baseline,retryguard}.yaml`, `scenario_4b_{baseline,retryguard}.yaml`'s `scale_constraints` from `cpu_limit_fraction: 0.1` to `cpu_limit_millicores: 50`; fix the stale pre-migration docstrings | `experiments/configs/scenario_{3,4a,4b}_*.yaml` |
| 3 | Create `productcatalogservice-hpa.yaml` (`minReplicas: 1, maxReplicas: 2`, same 85% CPU target shape as `frontend-hpa.yaml`); stop force-pinning productcatalog's replica count at run start, same treatment frontend already got | New manifest; `run_scenario.py` / `instance_scaling.py`-equivalent logic |
| 4 | Run the 5-run bottleneck-cap battery (§3); update `experiments/capacity/capacity_frozen.json` and `experiments/capacity/README.md` from the results | Live VM execution, follow-up session |
| 5 | Run the S1/S2/S6 system-load calibration (§3b), up to 3 tries each | Live VM execution, same session as #4 |
| 6 | Rewire all 16 scenario YAMLs per §5 above: point at `online_boutique_create_v2.sh`, drop `create2.sh`, apply the `cpu_limit_millicores` swap for S3/S4A/S4B, write the real `user_counts`/`spawn_rate` from #4/#5's results, bump `run_number`/`log_folder` to the then-current next-free slots | `experiments/configs/*.yaml` (all 16) |
| 7 | Add the productcatalog-HPA overcommit risk note to `RON-NEZER-BASE-MIGRATION.md` | Guide update, after #3 lands |
| 8 | Pin frontend/productcatalog HPA off specifically during their own bottleneck-cap calibration runs (battery runs 1 and 4) — a calibration-YAML-only override, not a change to their normal-scenario HPA config | `experiments/configs/scenario_calibration_*_50m.yaml` (new versions under the current regime) |

Suggested order: #1+#2 together (new mechanism, then point the YAMLs at it, so #4's battery runs against the real code path S3/S4A/S4B will use), #3 independently, #8 before #4 (the battery needs the pinned-off calibration YAMLs to exist), #4+#5 together (same live session, same cool-off pattern), #6 once #4/#5 have real numbers, #7 last (documentation, no dependency).

---

## 8. What this design-writing session did not do

- Did not modify any `experiments/configs/*.yaml`, `topfull_cpu_quotas.py`, `run_scenario.py`, or `RON-NEZER-BASE-MIGRATION.md` — all of §7 is future work.
- Did not create `productcatalogservice-hpa.yaml` or apply anything to the live cluster (the HPA/CPU-limit reads done during grilling were all `kubectl get`, read-only).
- Did not run any part of the §3/§3b recalibration battery — the VMs were found `TERMINATED` mid-session and were not restarted.
- Did not decide S1/S2/S6's actual final numbers (only their methodology and target criteria) or plan the fresh campaign (§6 above — still open, last in the dependency order).
