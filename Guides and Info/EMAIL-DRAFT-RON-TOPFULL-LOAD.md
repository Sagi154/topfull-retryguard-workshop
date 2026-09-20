# Draft email to Ron Nezer — how to make TopFull actually engage

> **Status: HELD, not sent (2026-09-14).** Written after the 2026-09-13 S1/S2 checkpoint showed
> TopFull's admission cap never dropping below the `10000` sentinel and Layer B `overloaded = 0`.
> Decision was to try solving it ourselves first. Send this only if our own load/quota
> calibration fails. Context: [../docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md](../docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md) §10.
>
> **2026-09-20:** this draft assumes we cloned his 3-VM setup *and* his Locust/`instance_scaling` recipe.
> The VM copy is true; the recipe is not. See [RON-NEZER-SETUP-VS-WORKSHOP.md](RON-NEZER-SETUP-VS-WORKSHOP.md)
> before sending — rewrite the "we use create.sh defaults" paragraph if this email ever goes out.
>
> **2026-09-20 update:** rewrote the "ask" section below to be specific and evidence-grounded, based on
> a full archaeology of his still-present `/home/user/` home directory on the shared VMs (`.bashrc`,
> `.bash_history`, on-disk YAMLs) — see
> [docs/superpowers/specs/2026-09-20-ron-nezer-base-migration-design.md](../docs/superpowers/specs/2026-09-20-ron-nezer-base-migration-design.md)
> §2/§3 for the full findings. His config turned out to be a ~5-month, hands-on-tuned moving target
> with several internally-contradictory on-disk snapshots (two HPA files, a namespace quota he kept
> editing, live-patched frontend/productcatalog CPU via shell functions), not one static recipe — so
> instead of asking generically "how did you get it to engage," we ask him to pin down which specific
> values were live at the moment he actually saw it happen.

---

**Subject:** TopFull load recipe — how did you get the RL/admission to actually engage?

Hi Ron,

We're the TAU workshop group running RetryGuard on top of TopFull + Online Boutique. We cloned your
3-VM setup (master / worker-1 / loadgen, 1 replica per service, `instance_scaling.py`) into our GCP
project and have been driving Locust from the usual `online_boutique_create.sh` / `create2.sh` scripts.

We've hit a problem we hope you already solved: **in some of our scenarios TopFull never really
"turns on."** The proxy is in the path, but the RL admission cap does not drop (it stays at the
uncapped `10000` sentinel), and the detector never marks services as overloaded. Locust can still
look bad (P95 well above 1s, high `Fail` because of the 1-second SLO), while HTTP stays mostly 2xx
and CPU stays under the detector's α. So we get SLO-miss, but not the overload-control behavior we
need to compare against RetryGuard.

Our current Locust **user counts** (same as the create-script defaults, spawn rate 90):

| API | Peak (S2 / S3 / S4, and first 5 min of S5/S6) | S1 (half, "normal") | S5/S6 after drop (~25%) |
|---|---|---|---|
| getproduct | 100 | 50 | 25 |
| postcheckout | 20 | 10 | 5 |
| getcart | 100 | 50 | 25 |
| postcart | 100 | 50 | 25 |
| emptycart (`CART`) | 300 | 150 | 75 |
| **total users** | **620** | **310** | **155** |

S3/S4 also pin one service to 10% of the paper CPU quota; S2 is a flat 10-minute hold at the peak
counts above, **no** CPU limit. S2 is the one where we most clearly see TopFull not throttling.

We poked around your old home directory on the shared VMs (`/home/user/`, still there from your
sessions — hope that's fine) trying to reconstruct what was running when TopFull actually engaged for
you, and it turns out there isn't one clean answer sitting on disk. A few things we found, and where
we'd love your memory (or any notes) to fill the gaps:

**Frontend/productcatalog CPU.** Your `.bashrc` has `fcpu()`/`pcpu()` helpers that live-patch the
running frontend/productcatalog Deployments' CPU directly (not just a YAML edit), and `.bash_history`
shows you swept a huge range with them — frontend from 100m up to 3000m (100, 200, 300, 350, 400, 450,
1900, 2000, 2300, 2400, 2600, 3000), productcatalog from 0 to 700m (0, 200, 300, 600, 700). Do you
recall (or have notes on) roughly which value(s) were actually live when you saw TopFull visibly
throttling/engaging?

**The namespace quota.** We also found `compute-resources.yaml`, a ResourceQuota capping the whole
namespace at 2600m — and history shows you were repeatedly creating/deleting/reapplying it,
interleaved with the `fcpu`/`pcpu` sweeps above, like you were hunting for where frontend gets
throttled against a quota you kept adjusting. Was that quota active (and at what value) at the moment
things worked?

**Which bigger setup was live together, if any.** There's also a later, larger combination on disk —
`instance_scaling.py` scaling frontend to 8 replicas, plus a custom Boutique YAML
(`online_boutique_original_custom.yaml`) with checkoutservice=800m, cartservice=2500m,
productcatalogservice=2000m, frontend/adservice/recommendationservice=1500m each. Were the 8×
frontend replicas and those specific YAML CPU values actually running at the same time as whichever
`fcpu`/quota values you land on above, or are they from a separate, unrelated session? And relatedly:
we found two different frontend HPA files (one from August 2025 capping `maxReplicas` at 2, one from
September 2025 allowing 20) — any idea which (if either) was actually applied when it worked?

Totally understand if a lot of this is hard to reconstruct exactly — if you happen to have any saved
notes, screenshots, or logs from a run where you saw it engage, that would settle all of the above at
once and save you from digging through memory. Otherwise, best-guess ballparks are still very useful
to us.

We're trying to mimic your working recipe rather than guess a new load. Happy to hop on a short call
if that's easier.

Thanks a lot,
Yoav
(and Sagi / Ido)
