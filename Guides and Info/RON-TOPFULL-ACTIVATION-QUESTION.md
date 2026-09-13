# Asking Ron: how to make TopFull actually engage

> **Purpose:** record the problem we want to ask Ron Nezer about — in some scenarios TopFull's overload control never activates — and keep the outreach email in one place so it can be edited/resent without rewriting it. Ron provided the original 3-VM TopFull environment this cluster was copied from ([MENTOR-UPDATE.md](mentor-update/MENTOR-UPDATE.md) §1).

---

## 1. The issue

In some scenarios **TopFull never really "turns on."** The proxy stays in the request path, but its admission control never engages:

- **Layer A (admission cap):** every *fresh* `/thresholds` scrape reads `threshold = 10000` — the uncapped sentinel. It never drops. (`threshold = 0` rows are stale reads with `threshold_fresh = 0`, not a real cap.)
- **Layer B (overload detector):** `overloaded = 0` for every service, every second. Frontend CPU utilization peaks at ~0.73 against an α of 0.80, so nothing crosses the detection bar.

Meanwhile the *client* view looks overloaded, which is what makes this confusing:

- Locust reports high `Fail` — but Locust's `Fail` means **"took longer than 1 s" (TopFull's goodput SLO) or non-OK HTTP**, not "the pod rejected it."
- Mesh HTTP status is effectively all **2xx**: inbound `5xx = 0` and `4xx = 0` on all 11 services.
- Because Istio retries need 5xx, **Envoy `retry` stayed 0** — so we also cannot show a retry storm, which is the thing RetryGuard is supposed to suppress.

So we get **SLO-miss without overload control**: slow, but not throttled and not failing.

### Evidence

2026-09-13 full-collector baseline holds (not campaign repeats):

| Run | Folder | Result |
|---|---|---|
| S1 normal op, 300 s | `campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run20` | PASS; frontend util peak **0.727** |
| S2 sustained overload, 600 s | `campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run17` | getcart Fail **161.17** / RPS ~163, P95 **2197.8 ms**; frontend util peak **0.737**; `overloaded = 0`; `retry = 0` |

Full write-up: [2026-09-13-s1-s2-baseline-metric-checkpoint.md](../docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md) §10. Related analysis of why `Fail` ≠ rejection: [2026-09-11-slo-fail-and-mu-estimator-design.md](../docs/superpowers/specs/2026-09-11-slo-fail-and-mu-estimator-design.md).

S2 is the clearest case: a flat 10-minute hold at peak user counts with **no** CPU limit, and TopFull still never caps.

### Why we don't just raise the load

Raising Locust users is the obvious lever, but we deliberately have not: we first need to decide whether S2 is supposed to hit **SLO-miss**, **CPU-quota overload**, or **HTTP 5xx** — they are three different targets and they calibrate differently. Getting Ron's working recipe is cheaper and more defensible than guessing a new load. (Same reasoning as the "no load calibration in this work" note in the μ̂/ρ spec.)

---

## 2. Our current load, for reference

Locust user counts, spawn rate 90 (S1 uses 45). These are the `online_boutique_create.sh` / `create2.sh` defaults, exported by `run_scenario.py` (`emptycart` → `CART`).

| API | Peak (S2 / S3 / S4, first 5 min of S5/S6) | S1 "normal" (half) | S5/S6 after drop (~25%) |
|---|---|---|---|
| `getproduct` | 100 | 50 | 25 |
| `postcheckout` | 20 | 10 | 5 |
| `getcart` | 100 | 50 | 25 |
| `postcart` | 100 | 50 | 25 |
| `emptycart` (`CART`) | 300 | 150 | 75 |
| **total users** | **620** | **310** | **155** |

Cluster shape: 1 worker node, **1 replica per service** (`instance_scaling.py`). S3/S4 pin one service to 10% of its paper CPU quota; S2 has no CPU limit.

---

## 3. The email

**Subject:** TopFull load recipe — how did you get the RL/admission to actually engage?

Hi Ron,

We're the TAU workshop group running RetryGuard on top of TopFull + Online Boutique. We cloned your 3-VM setup (master / worker-1 / loadgen, 1 replica per service, `instance_scaling.py`) into our GCP project and have been driving Locust from the usual `online_boutique_create.sh` / `create2.sh` scripts.

We've hit a problem we hope you already solved: **in some of our scenarios TopFull never really "turns on."** The proxy is in the path, but the RL admission cap does not drop (it stays at the uncapped `10000` sentinel), and the detector never marks services as overloaded. Locust can still look bad (P95 well above 1 s, high `Fail` because of the 1-second SLO), while HTTP stays mostly 2xx and CPU stays under the detector's α. So we get SLO-miss, but not the overload-control behavior we need to compare against RetryGuard.

Our current Locust **user counts** (same as the create-script defaults, spawn rate 90):

| API | Peak (S2 / S3 / S4, and first 5 min of S5/S6) | S1 (half, "normal") | S5/S6 after drop (~25%) |
|---|---|---|---|
| getproduct | 100 | 50 | 25 |
| postcheckout | 20 | 10 | 5 |
| getcart | 100 | 50 | 25 |
| postcart | 100 | 50 | 25 |
| emptycart (`CART`) | 300 | 150 | 75 |
| **total users** | **620** | **310** | **155** |

S3/S4 also pin one service to 10% of the paper CPU quota; S2 is a flat 10-minute hold at the peak counts above, **no** CPU limit. S2 is the one where we most clearly see TopFull not throttling.

Could you tell us how you actually ran it when TopFull *did* engage?

1. **Which workloads / figures / scripts** — `online_boutique_create.sh`, `create2.sh`, `run_fig8_loadgen.sh`, `run_fig15_online_boutique.sh`, something else?
2. **Exact Locust user counts** per API (`GETPRODUCT`, `POSTCHECKOUT`, `GETCART`, `POSTCART`, `CART`) and spawn rate / how long you held the load.
3. **Cluster shape** — how many worker nodes, replica counts, any CPU limits, and whether you used `instance_scaling.py` the same way we did (1 replica each).
4. **How you knew TopFull had activated** — e.g. `/thresholds` dropping below 10000, detector overload, `num_agent.csv`, goodput flattening, etc.
5. Anything else that mattered (warmup, RL already trained vs cold, starting proxy/`deploy_rl` order, periodic vs flat load).

We're trying to mimic your working recipe rather than guess a new load. Happy to hop on a short call if that's easier.

Thanks a lot,
Yoav
(and Sagi / Ido)

---

## 4. Shorter variant

If the email feels too long, drop the table and keep only "we use `create.sh` defaults: 100 / 20 / 100 / 100 / 300" plus questions 1–4. Keeping the table is preferable — it is the part Ron can answer at a glance.

---

## 5. For context if he asks

TopFull's own loadgen scripts in the submodule run **far** heavier than we do, which may itself be the answer:

| Script | GETPRODUCT | POSTCHECKOUT | GETCART | POSTCART | CART |
|---|---|---|---|---|---|
| `online_boutique_create.sh` (what we use) | 100 | 20 | 100 | 100 | 300 |
| `online_boutique_create2.sh` | 10 | 2 | 10 | 10 | 30 |
| `run_fig8_loadgen.sh` | 1500 | 500 | 200 | 200 | 600 |
| `run_fig15_online_boutique_base.sh` | 900 | 30 | 5000 | 2600 | 1000 |
| `run_fig15_online_boutique.sh` | 6100 | 370 | 5000 | 2600 | 9000 |

Caveat: the paper's environment had **five** worker nodes; ours has one, so their absolute numbers are not directly transferable. That is exactly why we want Ron's numbers for *this* environment rather than the paper's.
