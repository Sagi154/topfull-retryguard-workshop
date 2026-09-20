# Draft email to Ron Nezer — how to make TopFull actually engage

> **Status: HELD, not sent (2026-09-14).** Written after the 2026-09-13 S1/S2 checkpoint showed
> TopFull's admission cap never dropping below the `10000` sentinel and Layer B `overloaded = 0`.
> Decision was to try solving it ourselves first. Send this only if our own load/quota
> calibration fails. Context: [../docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md](../docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md) §10.
>
> **2026-09-20:** this draft assumes we cloned his 3-VM setup *and* his Locust/`instance_scaling` recipe.
> The VM copy is true; the recipe is not. See [RON-NEZER-SETUP-VS-WORKSHOP.md](RON-NEZER-SETUP-VS-WORKSHOP.md)
> before sending — rewrite the "we use create.sh defaults" paragraph if this email ever goes out.

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

Could you tell us how you actually ran it when TopFull *did* engage?

1. **Which workloads / figures / scripts** — `online_boutique_create.sh`, `create2.sh`,
   `run_fig8_loadgen.sh`, `run_fig15_online_boutique.sh`, something else?
2. **Exact Locust user counts** per API (`GETPRODUCT`, `POSTCHECKOUT`, `GETCART`, `POSTCART`, `CART`)
   and spawn rate / how long you held the load.
3. **Cluster shape** — how many worker nodes, replica counts, any CPU limits, and whether you used
   `instance_scaling.py` the same way we did (1 replica each).
4. **How you knew TopFull had activated** — e.g. `/thresholds` dropping below 10000, detector
   overload, `num_agent.csv`, goodput flattening, etc.
5. Anything else that mattered (warmup, RL already trained vs cold, starting proxy/`deploy_rl` order,
   periodic vs flat load).

We're trying to mimic your working recipe rather than guess a new load. Happy to hop on a short call
if that's easier.

Thanks a lot,
Yoav
(and Sagi / Ido)
