# Loadgen layer migration: adopt Ron's swarm shape, defer numbers (2026-09-21)

> Closes the "loadgen layer" bullet deferred in
> [2026-09-20-ron-nezer-base-migration-design.md](2026-09-20-ron-nezer-base-migration-design.md)
> §8 ("task-weight remix, GETPRODUCT=600, dropped `-t 15m`, split-cart
> `frontend.sh` launcher... are all 'adopt eventually' per decision 1, but
> not designed here"). This doc designs the loadgen layer's **shape**
> (mechanism). Loadgen **numbers** (per-tag user counts, spawn rate) and
> the S1–S6 scenario methodology rework are explicitly out of scope — see
> §5.

Related: [RON-NEZER-SETUP-VS-WORKSHOP.md](../../../Guides%20and%20Info/RON-NEZER-SETUP-VS-WORKSHOP.md),
[2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md](2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md)
(its §4 numbers are already flagged stale by the CPU/replica migration and
stay stale here too — see §5), `experiments/loadgen/online_boutique_create_v2.sh`,
`CONTEXT.md` (Loadgen section).

---

## 1. What changed since the "adopt eventually" note was written

The 2026-09-20 migration design assumed a single candidate: "the split-cart
`frontend.sh` launcher." Re-auditing `topfull-load` for this doc (fresh SSH
read of `/home/user/.bash_history`, both loadgen scripts, and
`locust_online_boutique.py` in both trees) found the situation is less
settled:

- **Two different launcher families exist on Ron's disk**, not one:
  - `online_boutique_create.sh` + `online_boutique_create2.sh` — a
    merged `$CART` swarm for getcart/postcart/emptycart, dated Nov 2025,
    invoked as a pair exactly twice in the visible history.
  - `frontend.sh` (alias `runfrontend`, edited via `vifrontend`) — three
    **independent** swarms for getcart/postcart/emptycart (own `-u`/`-r`
    each), plus independently sharded getproduct/postcheckout, `-t 6m`,
    dated June 2025 but re-run **dozens of times**, including as the very
    last sustained activity in the whole history.
  - Going by actual invocation frequency and recency, `frontend.sh`'s
    **shape** — not `create.sh`'s — is the dominant, most-exercised
    pattern, contradicting `RON-NEZER-SETUP-VS-WORKSHOP.md`'s characterization
    of `frontend.sh` as an unused leftover.
  - Neither script's literal numbers look "final": the history interleaves
    both launcher families with raw ad-hoc single-tag capacity probes
    (`locust --tags getproduct -u 3000 -r 3000 -t 2m`), i.e. Ron was mid
    calibration, not running a settled recipe, when this history was captured.
- **The `@task()` weight remix is real and independent of either launcher.**
  `locust_online_boutique.py` is one shared file; Ron's copy has
  postcheckout 50→500, getcart 30→100, postcart 15→1, emptycart 15→1,
  getproduct 150→100 versus the paper/workshop weights. This only ever
  matters when multiple tags share one Locust swarm.
- **`experiments/loadgen/online_boutique_create_v2.sh`** (built 2026-09-20,
  *before* this audit, to fix the `count/RATE` inversion and the dead
  `GETCART`/`POSTCART` env vars) independently arrived at the same shape as
  `frontend.sh`: every one of the five tags gets its own single-tag swarm
  (with light `--master`/`--worker` sharding kept only for
  getproduct/postcheckout). This was not built to imitate Ron — it was
  built to fix our own bugs — but the grilling in this doc concluded on the
  same shape independently, before treating v2 as part of the answer (see
  decision 4).

---

## 2. Decisions

### Decision 1 — adopt the shape, not either script's literal numbers

**Adopt Ron's loadgen *shape*: every Locust tag runs in its own
independent single-tag swarm, never sharing a pool where `@task` weight
would arbitrate between tags.** Do not freeze `frontend.sh`'s numbers
(100/50/100/100/100 @ RATE=50, `-t 6m`) or `create.sh`'s
(600/20/100/100/300 @ RATE=90) as ground truth — the archaeology in §1
shows neither is a settled, final recipe; both are snapshots from an
active tuning process, same as our own CPU-quota archaeology in
[2026-09-20-ron-nezer-base-migration-design.md](2026-09-20-ron-nezer-base-migration-design.md)
found for his Detector/YAML CPU numbers.

**Considered:**
- Freeze `frontend.sh`'s literal numbers — rejected, no stronger evidence
  it was "final" than any other point in his tuning history.
- Freeze `create.sh`'s literal numbers — rejected, same reason, and it's
  the less-exercised launcher per §1.
- Block on asking Ron which was final — rejected for now; doesn't unblock
  us, and the *shape* question doesn't need his answer (both his launchers
  and our independent v2 fix converge on the same shape for 4 of 5 tags;
  only the cart family differs, and Ron's more-used script also
  independently splits it).

### Decision 2 — adopt the task-weight remix, even though it will be inert

Update `locust_online_boutique.py`'s `@task()` weights to match Ron's
(postcheckout 500, getcart 100, postcart 1, emptycart 1, getproduct 100),
for fidelity with his tree. Document plainly (in the file and in
`CONTEXT.md`) that under decision 1's shape, no scenario ever merges tags
into one swarm, so these weights currently have **no effect on any real
run** — they only matter if a future scenario deliberately chooses to
merge tags again.

**Considered:** skip the remix entirely (functionally equivalent today,
less file churn) — rejected; the team's explicit call was fidelity to
Ron's setup as the base across all layers, and the remix is a one-line-per-tag,
zero-risk change now that decision 1 makes it inert rather than
behavior-changing.

### Decision 3 — `experiments/loadgen/online_boutique_create_v2.sh` is the implementation vehicle

Treat v2 (already built, already matching decision 1's shape) as the base
to adjust, not something to discard or a brand-new script to write from
scratch. Concretely, in the follow-up implementation:
- Fix the known `ENV_MAP` bug already documented in
  [2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md](2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md) §6.1
  (`"emptycart": "CART"` → `"emptycart": "EMPTYCART"` in `run_scenario.py`'s
  `ENV_MAP`), which is required for v2's independent `EMPTYCART` env var to
  do anything.
- Apply decision 2's weight remix to the shared `locust_online_boutique.py`.
- Leave v2's own per-tag env-var defaults as placeholders — they are not
  the loadgen numbers this doc is deferring (see §5); a later calibration
  pass sets the real per-scenario values.

**Considered:** write a fresh launcher — rejected, would duplicate v2's
already-working port bookkeeping, sharding, and `${VAR:-default}`
convention for no benefit, and the user was explicit that v2 should not be
assumed correct *during grilling* but is fine to adopt now that the
grilled conclusion happens to match it.

### Decision 4 — duration stays scenario-governed, not a hardcoded launcher flag

Keep v2's existing behavior: the launcher itself stays untimed
(`DURATION_MIN` empty by default), and `run_scenario.py`'s
`stop_locust()` remains the sole authority for stopping Locust at each
scenario's `duration_seconds`. Do not adopt `frontend.sh`'s hardcoded
`-t 6m`.

**Considered:** add a `-t` flag sized per-scenario as a "belt and
suspenders" safety valve matching Ron's convention — rejected as
unnecessary; `run_scenario.py` already owns this responsibility and a
second, independently-sized stop mechanism only adds a place for the two
to disagree.

### Decision 5 — drop `create2.sh`'s trickle pattern; no replacement needed

`create2.sh` (small continuous-rate companion processes, run immediately
after `create.sh`) is specific to the create.sh launcher family, which
decision 1 does not adopt. Ron's more-exercised `frontend.sh` has no
companion trickle step at all — it is a single, complete script for all
five tags. Under the shape this doc adopts, there is nothing to port for
the trickle pattern; drop it, and do not add an equivalent to v2.

**Considered:** keep `create2.sh` running alongside v2 anyway — rejected;
it would inject small extra continuous load through a third, differently
governed launcher family for a pattern that isn't part of the shape being
adopted, adding complexity with no source recipe behind it.

---

## 3. What is NOT decided here (deferred, tracked separately)

- **Loadgen numbers** — the actual `getproduct`/`postcheckout`/`getcart`/
  `postcart`/`emptycart` user counts and spawn rate for each of S1–S6.
  Neither Ron's numbers (unsettled per §1) nor the existing
  [2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md](2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md)
  §4 numbers (calibrated against the now-superseded paper-quota
  `capacity_frozen.json`) are reused. **A fresh calibration pass must run
  under the Ron-config regime** (post CPU/replica/HPA migration) before
  any scenario YAML's `locust.user_counts`/`spawn_rate` change. Per the
  team's explicit decision, this happens together with the S1–S6 scenario
  methodology rework (§8 of the migration design doc), not before it and
  not in this doc.
- **Rewiring the 16 scenario YAMLs** — none of them are repointed at v2 or
  given new numbers by this doc. That is explicitly bundled with the
  deferred item above.
- **Deploying v2 (or the weight-remixed locustfile) onto `topfull-load`** —
  an operational step for the implementation plan, not a design decision.
- **S1–S6 methodology rework** — unchanged from migration doc §8; still
  open, still bundled with the recalibration above.

---

## 4. What this doc does not do

- Does not modify `TopFull/` (submodule) or any live cluster/VM state —
  all findings in §1 came from read-only SSH audits (`cat`, `grep`,
  `.bash_history`), no writes.
- Does not modify `experiments/run_scenario.py`, `experiments/configs/`,
  `locust_online_boutique.py`, or `online_boutique_create_v2.sh` — those
  are follow-up implementation, covered by decisions 2–3 but not applied
  by this doc.
- Does not set any loadgen numbers or touch scenario YAMLs (§3).
- Does not resolve which of Ron's two launcher scripts was "the" final one
  historically — only which **shape** we adopt going forward, which does
  not require that historical answer (§1, decision 1).

---

## 5. Next step

Invoke `writing-plans` for an implementation plan covering decisions 2–3
(weight remix + `ENV_MAP` fix + v2 deployment), scoped separately from the
deferred recalibration/S1–S6 work in §3.
