# Loadgen redesign: fixing GETCART/POSTCART and re-sizing user counts/rate (2026-09-20)

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Our Locust launch scripts silently merge `getcart`/`postcart`/`emptycart`
> into one `$CART` knob (GETCART/POSTCART env vars do nothing), compute
> spawn rate backwards (`-r $((count / RATE))`, so a bigger `RATE` is a
> *slower* ramp), and default to trickle-scale counts inherited from a
> smoke test. This doc explains what TopFull's own authors did, why their
> numbers don't transfer to our cluster, what we're proposing instead, and
> exactly what would need to change in `run_scenario.py` / scenario YAMLs to
> adopt it. **Nothing in this doc has been applied to `run_scenario.py`,
> `experiments/configs/`, or the live cluster — this is a proposal.**
>
> **Amendment (2026-09-22):** `online_boutique_create_v2.sh` no longer passes
> `RATE` through as Locust users/sec. Spawn math matches Ron's launchers:
> `-r = count / RATE`, computed with awk so the result is a float. The
> independent-swarm fix in §5 still stands. §4's "RATE=50 used directly"
> ramp example does not describe the script.

Related: [2026-09-17-s2-frontend-2x-quota-design.md](2026-09-17-s2-frontend-2x-quota-design.md),
[2026-09-18-locust-spawn-rate-fix.md](2026-09-18-locust-spawn-rate-fix.md),
[2026-09-18-s2-load-scaling-investigation-summary.md](2026-09-18-s2-load-scaling-investigation-summary.md),
[experiments/capacity/README.md](../../../experiments/capacity/README.md),
[RON-NEZER-SETUP-VS-WORKSHOP.md](../../../Guides%20and%20Info/RON-NEZER-SETUP-VS-WORKSHOP.md)
(Ron already split getcart/postcart/emptycart into separate Locust swarms in `/home/user/TopFull/TopFull_loadgen/frontend.sh`; that launcher is not what `run_scenario.py` uses).

---

## 1. The two problems, precisely

### 1a. GETCART / POSTCART are dead env vars

`run_scenario.py`'s `ENV_MAP` (`_launch_locust()`, around line 920) exports
per-scenario-YAML `locust.user_counts` as:

```
getproduct   -> GETPRODUCT
postcheckout -> POSTCHECKOUT
getcart      -> GETCART
postcart     -> POSTCART
emptycart    -> CART          # <-- the actual bug
```

But `TopFull/TopFull_loadgen/online_boutique_create.sh` (and `create2.sh`)
never read `$GETCART` or `$POSTCART` as a `-u` value. They launch **one**
combined Locust process/swarm per script:

```bash
locust -f locust_online_boutique.py ... --tags getcart postcart emptycart \
       --headless -u $((CART+0)) -r $((CART / RATE)) -t 15m
```

Locust splits `$CART` users across the three tags according to
`locust_online_boutique.py`'s fixed `@task(weight)` decorators — `getcart`
(30), `postcart` (15), `emptycart` (15) — a **30:15:15** ratio, always,
regardless of what `GETCART`/`POSTCART` say. So today, every scenario
YAML's `getcart:`/`postcart:` values under `locust.user_counts` are
cosmetic; only `emptycart:` (via `CART`) has any real effect, and even that
effect is diluted 4× (emptycart is only 15 of the 60 weight-units in that
merged session).

### 1b. Spawn rate is inverted and rounds to near-zero at our scale

`-r` in Locust is the ramp-up rate in **users spawned per second** — bigger
should mean faster. But these scripts compute it as:

```bash
-r $((POSTCHECKOUT / RATE))
-r $((GETPRODUCT / RATE))
-r $((CART / RATE))
```

i.e. `-r = count / RATE`. A **bigger** `RATE` constant produces a
**smaller** (slower) `-r`. This is backwards from the name and, at our
counts, catastrophic: `experiments/configs/scenario_2_baseline.yaml` sets
`postcheckout: 20` with `spawn_rate: 90` (exported as `RATE=90`), giving
`-r = 20/90 = 0` under bash integer division — a spawn rate of **zero**,
which Locust silently treats as "spawn instantly" for small pools but which
[`2026-09-18-locust-spawn-rate-fix.md`](2026-09-18-locust-spawn-rate-fix.md)
independently found produced ~100s ramps for the cart swarm under similar
math. **Confirmed by re-reading the scripts for this doc:** yes, this
reading is correct — every `run_fig*`/`online_boutique_create*.sh` script
in `TopFull/TopFull_loadgen/` uses this same `count / RATE` formula, and our
own prior investigation already independently found and worked around it
(see §3).

---

## 2. How TopFull's own authors sized their scripts

### 2a. Hardware: genuinely multiple physical machines, not just processes

`context/TopFull.pdf` §5 "Experimental Setup" (re-read in full for this
doc):

> "We deploy microservices on Azure cloud environment and dynamically scale
> up to **10 VMs** for Kubernetes worker nodes on demand. We conduct
> experiments on Azure VM **D48ds_v5** with **48 vCPUs**... For traffic
> generation, we use Locust and **two additional Azure virtual machines
> (D48ds_v5)** for large-scale traffic generation."

So: up to **10** worker-node VMs at 48 vCPUs each (up to 480 vCPUs of
Online Boutique/Train Ticket pods), plus **2 dedicated 48-vCPU loadgen
VMs** (96 vCPUs just for Locust), separate from the TopFull control-plane
node. That is a fundamentally different scale from our fixed 3-VM lab
(`topfull-master`/`topfull-worker-1`: 8/16 vCPUs, `topfull-load`: 8 vCPUs).
The `--master`/`--expect-workers=N` pattern in `online_boutique_create.sh`
(10-20 **Locust worker processes**, all on one machine) is a way to get
around a single Python process's throughput ceiling — it is *not* evidence
of, or a substitute for, the paper's actual multi-VM loadgen setup. Both
things are true simultaneously in the original TopFull evaluation: many
processes, distributed across (at least) 2 physical loadgen VMs. We only
have 1 loadgen VM (`topfull-load`), so we can only reproduce the
"many processes on one machine" half of that setup.

### 2b. Target load level: Figure 8 vs Figure 9 vs Figure 15

The paper text (§6.1): *"The overload is generated from **2600 Locust
users** invoking 1 request per second."* This number lines up with the
x-axis maximum in **Figure 9** ("User Demand (rps)": 200, 800, 1400, 2000,
**2600**) — i.e., Figure 8's single overload snapshot sits at the top of
the demand sweep plotted in Figure 9. `run_fig8_loadgen.sh` in our
submodule copy sums to `1500+500+200+200+600 = 3000` users (its own
`GETPRODUCT/POSTCHECKOUT/CART` values) — in the right ballpark for "near
Fig 9's max demand," though it does not reproduce the paper's number
exactly (expected: our checked-in scripts are whatever configuration state
the KAIST repo happened to be in, not necessarily the literal snapshot used
for the printed figures, and the sweep itself needed several different
demand levels, not just 2600).

`run_fig15_online_boutique.sh` (traffic surge + autoscaler, Figure 15) uses
much larger counts (`GETPRODUCT=6100`, `CART=9000`, total ≈ 20,000+ users)
matching Figure 15b's y-axis, which goes up to **25,000 rps** — a
qualitatively different, much larger experiment (autoscaler catching up
during a surge, not a flat overload hold), consistent with it needing far
more offered load than Figure 8's static overload snapshot.

**Bottom line for our project:** the paper's absolute numbers (2600,
9000, 20000+ users) are sized for a **10-worker-VM, 480-vCPU** cluster with
**2 dedicated 48-vCPU loadgen VMs**. They are meaningless lifted directly
onto our fixed single-worker-VM lab; we need our own capacity-based
numbers (§4).

### 2c. The `-r` math, confirmed

Re-reading all five scripts (`run_fig15_online_boutique{,_base}.sh`,
`run_fig8_loadgen.sh`, `online_boutique_create{,2}.sh`): every one of the
three sharded (`--master`/`--worker`) sessions computes `-r` as
`$((count / RATE))`. `create2.sh`'s three single-process sessions instead
hardcode `-r 3` / `-r 90` / `-r 100` directly (not derived from `RATE`), so
`create2.sh`'s ramp behavior was never affected by this bug — only
`create.sh`'s three sharded sessions were. This matches and confirms
[`2026-09-18-locust-spawn-rate-fix.md`](2026-09-18-locust-spawn-rate-fix.md)'s
finding from the live loadgen VM.

### 2d. `run_scenario.py`'s env-var contract

`_launch_locust()` exports `GETPRODUCT`/`POSTCHECKOUT`/`GETCART`/`POSTCART`/
`CART`/`RATE` before running whatever `locust.scripts:` a scenario YAML
lists (default `[online_boutique_create.sh, online_boutique_create2.sh]`).
Per `Guides and Info/PHASE5-EXPERIMENTS-GUIDE.md` §7, the **deployed**
copies of these two scripts on `topfull-master`/`topfull-load` (not the
pristine upstream copies mirrored in this git submodule) were patched to
`${VAR:-default}` so exported env vars actually override the hardcoded
defaults shown in the submodule files. Our new script (§5) follows the
same convention so it slots into this contract unchanged.

---

## 3. Why we can't just reuse TopFull's numbers — our own capacity data

We do **not** have 10 worker VMs or 2 dedicated 48-vCPU loadgen VMs. We
have one `e2-standard-16` worker (`topfull-worker-1`) running every Online
Boutique service at **1 replica**, fronted by one `e2-standard-8` loadgen
VM. `experiments/capacity/capacity_frozen.json` (frozen 2026-09-19,
`cluster_shape: topfull-worker-1=e2-standard-16`) gives real, measured
`mu_per_millicore` (saturated throughput per Kubernetes CPU millicore) for
the four services that matter most for entry-level sizing:

| Service | `mu_per_millicore` | Paper CPU limit (unconstrained S1/S2) | Extrapolated capacity |
|---|---|---|---|
| frontend | 0.3 req/s/millicore | 1000m | **≈300 rps** |
| checkoutservice | 10.82 | 1000m | ≈10,800 rps (see caveat below) |
| productcatalogservice | 8.95 | 500m | ≈4,475 rps |
| paymentservice | 0.72 | 1000m (no paper entry; `DEFAULT_PAPER_LIMIT_MILLICORES=1000`) | ≈720 rps |

**Caveat, stated explicitly (carried over from
`experiments/capacity/README.md`):** `mu_per_millicore` was frozen at a
**50m** CPU-constrained calibration run and is being linearly extrapolated
here to a 20× larger CPU limit (1000m). The README itself flags this for
checkoutservice specifically ("`mu_per_millicore` 10.82 vs historical
0.1615 is a linearity check only — the constrained value is the freeze").
Treat the checkout/productcatalog/payment extrapolations as directional,
not load-bearing; **frontend's ≈300 rps is the number this doc actually
relies on**, because:

1. Frontend is the literal front door for **all five** Locust APIs (every
   request passes through it once), so it is the tightest, most relevant
   single-number constraint for sizing *total* offered load, regardless of
   how the backend numbers extrapolate.
2. `experiments/capacity/README.md`'s own sanity check already computed
   live `rho_hat` (offered λ ÷ frozen μ at the run's actual CPU limit) for
   frontend on our two most recent real S1/S2 baseline runs:
   - **S1 baseline `run24`: frontend `rho_hat = 1.295`**
   - **S2 baseline `run23`: frontend `rho_hat = 1.837`**

   S1 is supposed to be "comfortably under capacity" (`scenario_1_baseline.yaml`'s
   own description). A ρ of 1.295 means **the current S1 scenario is
   already at or above the frontend's calibrated capacity**, using its
   *current* (bug-diluted) load. `AGENTS.md` itself flags this exact
   mismatch as still open ("Informal S1 0.5–0.8 band still not met on
   frontend"). This is independent evidence — not our extrapolation — that
   today's Locust sizing is off in **both directions at once**: too low to
   be "comfortably under" per the frozen capacity number, and, per §1a/§1b,
   not even actually applying the YAML's own `getcart`/`postcart` values
   the way the YAML author intended.

### What's already been ruled out for pushing load higher on this cluster

Three 2026-09-17/09-18 specs already explored raising offered load and hit
dead ends worth not repeating:

- **Uniform Locust user-count scaling is a closed, dead lever** under a
  live-TopFull, frontend-2×-quota S2 variant
  ([`2026-09-18-s2-load-scaling-investigation-summary.md`](2026-09-18-s2-load-scaling-investigation-summary.md)):
  1.5×/2×/6× user-count probes all *lowered* measured frontend λ instead of
  raising it, even after fixing the same `count/RATE` spawn bug we fix here
  (§1b) with a probe-only launcher. Root cause left standing (not fully
  proven): Locust's `wait_time = constant_throughput(1)` is a **closed-loop**
  model — a fixed pool of N users, each doing at most 1 req/s, means
  throughput is capped near `N / mean_response_time`; once latency rises,
  adding more users does not straightforwardly add more offered rps if
  something else (not user count) is the limiter in that specific
  configuration.
- That investigation's target scenario (frontend quota doubled to 2000m,
  trying to force a *backend* to become the bottleneck) is **not** the
  scenario this doc is sizing. Our default S1/S2 (`scale_constraints: []`,
  paper CPU limits) has **frontend itself** as the intended global entry
  bottleneck — exactly the ρ>1-at-the-frontend regime the closed-loop model
  should still express normally as N rises toward `mu_this_run ≈ 300 rps`
  worth of concurrent frontend work. We are not relying on backend
  saturation the way the ruled-out lever was.
- **Do not** re-attempt: raising `topfull-load` VM count, changing
  Locust's `wait_time`/load model (explicitly flagged team-discussion-only
  in `AGENTS.md`), or patching the shared `create.sh`/`create2.sh` in place
  (would affect every teammate's S1–S6 runs without a decision).
- The closed-loop caveat above is exactly why the recommended S2 number
  below (§4) deliberately overshoots frontend's ≈300 rps capacity by
  ~2× rather than aiming for a marginal ρ≈1.05–1.2: at a small margin over
  ρ=1, the same closed-loop dynamics that flattened λ in the ruled-out
  probe could make S2's overload look weaker than intended even though the
  entry bottleneck is real. This is a hypothesis this doc's numbers are
  designed to survive, not a guarantee — validate with a short live run
  before trusting them for the full campaign (see §6).

---

## 4. Recommended numbers

Distributing total offered users across the five tags using the *paper's
own* relative task weights (`getproduct:postcheckout:getcart:postcart:emptycart`
= `150:50:30:15:15`, i.e. `57.7%:19.2%:11.5%:5.8%:5.8%` of the total) keeps
the API mix consistent with what TopFull's own paper (and our existing
scenario YAMLs) intends, while only changing the *total* to match our
cluster's calibrated frontend capacity (≈300 rps).

| Scenario | Target vs. frontend capacity (300 rps) | Total users | getproduct | postcheckout | getcart | postcart | emptycart | `RATE` |
|---|---|---|---|---|---|---|---|---|
| **S1** (normal op) | **~0.53×** — comfortably under ρ=1 | 160 | 90 | 30 | 20 | 10 | 10 | 50 |
| **S2** (sustained overload) | **~2.0×** — clearly ρ>1, not marginal | 600 | 350 | 120 | 70 | 30 | 30 | 50 |

For comparison, today's YAML-nominal values are S1 = 310 total
(`50/10/50/50/150`) and S2 = 620 total (`100/20/100/100/300`) — coincidentally
close in raw *sum*, but, per §1a, those sums were never actually what got
sent: `getcart`/`postcart` were ignored and the cart family's actual
population was governed by `emptycart`'s value (`CART`) split 30:15:15 by
task weight, not by the YAML's per-tag intent. The new numbers above both
(a) fix that routing bug via three independent processes (§5) and (b) move
the *total* to sit on either side of frontend's calibrated ρ=1 line
instead of both scenarios landing near/above it as they do today.

`RATE=50` (used **directly** as Locust `-r`, not divided) ramps the
largest single tag (S2's `getproduct: 350`) to full population in 7
seconds, and S1's largest tag (`getproduct: 90`) in under 2 seconds — both
trivial relative to `duration_seconds: 300`/`600`, versus today's
documented ~100s ramp for the cart swarm.

**This is a starting point, not a finished calibration.** The frontend
number it's built on is itself only as good as a 26-tick, 50m-CPU
calibration run linearly extrapolated to 1000m (§3). Recommend one short
(~2 min) live validation pass with the new script before trusting these
numbers for a full campaign re-run — see §6.

---

## 5. The new script

**File:** [`experiments/loadgen/online_boutique_create_v2.sh`](../../../experiments/loadgen/online_boutique_create_v2.sh)

Design:

- **Fixes §1a** by giving `getcart`, `postcart`, and `emptycart` three
  independent, single-process Locust sessions (`v2_getcart`, `v2_postcart`,
  `v2_emptycart` tmux sessions), each driven by its own env var
  (`GETCART`/`POSTCART`/`EMPTYCART`) and its own `-u`/`-r`. No shared
  `$CART` variable exists in this script at all.
- **Spawn math matches Ron, not the original draft of this section.**
  `RATE` (and optional per-tag `RATE_*` overrides) is a divisor: Locust
  `-r` = `count / RATE`, computed with awk so the result is a float. The
  2026-09-20 draft of this bullet said to pass `RATE` through as users/sec;
  that was reverted on 2026-09-22. Bash integer `$((count / RATE))` is
  still wrong — it truncates small ratios to 0.
- **Keeps** the `--master`/`--expect-workers` sharding pattern from
  `create.sh` for `getproduct` and `postcheckout` (the two tags most likely
  to need >1 Python process worth of throughput), with lower default
  worker counts (`WORKERS_GETPRODUCT=4`, `WORKERS_POSTCHECKOUT=2` vs.
  TopFull's 20/10) — our recommended totals (§4) are two to three orders of
  magnitude below the paper's, so a handful of workers is plenty of
  headroom, not a compromise.
- **Drops** `create2.sh`'s separate "untimed low continuous trickle"
  pattern — with real independent per-tag knobs and a working spawn rate,
  one properly-sized script covers both roles (steady low load *and*
  overload), so there is no longer a reason to run two scripts back-to-back
  the way the current `locust.scripts:` default does.
- Every knob follows the `${VAR:-default}` convention already used on the
  *deployed* copies of `create.sh`/`create2.sh` (§2d), so `run_scenario.py`'s
  existing `export VAR=...; bash <script>` launch mechanism needs zero
  changes to work with it, other than the one `ENV_MAP` line below.
- Self-contained port bookkeeping: rather than depend on the checked-in
  `TopFull/TopFull_loadgen/ports/` file range (shared with the upstream
  scripts, capped at 8930), the script creates its own `ports_v2/<port>`
  files on demand in a private 91xx–93xx range that can never collide with
  a concurrently running upstream script.
- Verified locally (no SSH, no live cluster — per this task's constraints):
  `bash -n` syntax check passes, and a dry run with `tmux`/`locust_online_boutique.py`
  stubbed out confirms it emits exactly one `-u`/`-r` pair per tag
  (`getcart -u 150 -r 50`, `postcart -u 150 -r 50`, `emptycart -u 150 -r 50`
  by default — three different processes, not one merged `-u 150` split
  30:15:15).

---

## 6. Proposed follow-up changes (NOT applied — for review)

To actually adopt this script for a scenario, two small, well-isolated
changes would be needed. Neither has been made:

1. **`experiments/run_scenario.py`, `_launch_locust()`, `ENV_MAP`** (around
   line 926): change

   ```python
   "emptycart":    "CART",      # create scripts use CART, not EMPTYCART
   ```

   to

   ```python
   "emptycart":    "EMPTYCART",
   ```

   This is the only code change required. It is backward compatible with
   the *existing* `online_boutique_create.sh`/`create2.sh` only in the
   sense that those scripts simply won't see an `EMPTYCART` var they never
   read (harmless) — but it does mean any scenario YAML still pointing at
   the old scripts would silently stop setting `CART` at all, reverting
   those scripts' cart-family session to its own $CART default (300, per
   `create.sh`). **So this line should only land in the same change that
   also updates every `locust.scripts:` list still using the old scripts**,
   or be made conditional/dual-key if a transition period is wanted.

2. **Per-scenario YAML `locust:` block** — point `scripts:` at only the new
   script, e.g. for a trial S1/S2 re-run:

   ```yaml
   locust:
     user_counts:
       getproduct:   90     # S1 example, from §4
       postcheckout: 30
       getcart:      20
       postcart:     10
       emptycart:    10
     spawn_rate: 50
     scripts:
       - online_boutique_create_v2.sh
   ```

   No other YAML schema change needed — `user_counts`/`spawn_rate`/`scripts`
   already exist as keys today.

3. `online_boutique_create_v2.sh` needs to be deployed onto `topfull-load`
   next to the existing scripts (same mechanism `run_scenario.py` already
   uses to sync `retryguard.py`/collectors onto `topfull-master` would need
   a small addition for the loadgen host, or a one-time manual `scp` —
   out of scope for this doc to specify further since it's an operational
   step, not a design decision).

4. **Recommend a short live validation run before wide adoption:** a ~2
   minute S1-shaped smoke test with the new script and §4's S1 numbers,
   checking (a) `pgrep -c locust` reports 3 single-process + 2 master + 6
   worker = 11 processes as expected, (b) `service_inbound.csv`/mesh λ for
   frontend lands near the intended ~160 rps (not near 300+, which would
   mean the closed-loop dynamics or some other factor pushed real offered
   load higher than nominal), and (c) `rho_frozen_report.py` on the
   resulting run shows frontend `rho_hat` meaningfully lower than the
   current `run24`'s 1.295. This is exactly the kind of check the several
   2026-09-17/18 investigations ran before trusting a new load level, and
   should be repeated here rather than skipped.

---

## 7. What this doc does not do

- Does not modify `TopFull/` (submodule).
- Does not modify `experiments/run_scenario.py` or any file under
  `experiments/configs/`.
- Does not SSH into or run anything against `topfull-master`,
  `topfull-worker-1`, or `topfull-load`.
- Does not touch any `experiments/results/campaign_48/calibration_*`
  folders.
- Does not change Locust's `wait_time`/closed-loop model — flagged
  team-discussion-only in `AGENTS.md`, unchanged here.
- Does not re-litigate the ruled-out S2-frontend-2× user-scaling lever —
  cited as background only (§3).
