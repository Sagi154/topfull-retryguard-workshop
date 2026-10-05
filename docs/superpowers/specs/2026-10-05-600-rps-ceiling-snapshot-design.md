# Storefront ~600 req/s ceiling — snapshot design

## 1. Goal

Name the most likely limiter of the storefront ceiling: the five Locust entry
APIs together stay near 600 req/s on this cluster even when more than 650
users are configured. One both-off hold, no config changes beyond the pin and
the mix below. Success is a single candidate over its line and the others
under theirs. Zero or several candidates over their lines is an inconclusive
snapshot; the isolation holds in §7 are the next step and are not run here.

The number 600 is measured, not a constant in the generator.
`constant_throughput(1)` caps each user at one request per second, and at
less than that when the response takes longer than a second. Holds whose
configured sum is only ~560 (the run 89 mix, 275/90/100/90/5) cannot show a
ceiling at 600, because the generator itself stops at the user count. This
snapshot therefore uses a mix whose configured sum is 800.

## 2. What is already ruled out

These are not candidates. The snapshot does not re-test them.

- Load VM CPU. `topfull-load` was ~90% idle, no Locust process near one core
  ([2026-09-18 investigation](2026-09-18-s2-load-scaling-investigation-summary.md),
  [run 60 snapshot](../../../Guides%20and%20Info/2026-09-29-s2-round0-ceiling-snapshot.md)).
- Frontend app-container CPU. 20–30% of quota on the holds that hit the
  ceiling; doubling the quota and adding replicas did not raise arrival rate.
- TopFull admission. The ceiling holds had Layer A at the 10000 passthrough.
  This hold is both-off as well, and the reading checks that it stayed there.
- The sidecar CPU *request*. `proxyCPU=100m` with `proxyCPULimit` absent is a
  scheduling weight, not a cap. The proxy already runs at ~500m. A 90–100m
  *limit* did collapse latency (runs 14–25); this hold does not set one.

## 3. The hold

One 600 s both-off S2 hold on the disk-copy VMs. Slot **run154**
(`experiments/configs/scenario_2_baseline_no_topfull.yaml`, currently unused).
Counts are getproduct / postcheckout / getcart / postcart / emptycart =
**100 / 200 / 100 / 200 / 200** (sum 800). This is the run 51 mix, the hold
where `emptycart` at a 53 ms P95 still reached only 0.72 of its users
([calibration spec, Runs 30–56](2026-09-25-s2-overload-user-count-calibration.md)).
`spawn_rate` 50. `paper_cpu_reconcile: false`. TopFull RL off, RetryGuard off.
The proxy still starts: Locust routes through `:8090` even when RL is off.

Paper-C1 pin, per pod, request equal to limit: frontend 1150 m × 4 (HPA min 4
/ max 4), checkoutservice 800 m × 1, recommendationservice 1150 m × 1,
productcatalogservice 800 m, cartservice 800 m, currencyservice 770 m,
shippingservice 770 m, adservice 1150 m, paymentservice 155 m, emailservice
120 m, redis-cart 540 m. Every other Deployment has 1 replica. Catalog HPA
min 1 / max 1. Sidecar annotation `sidecar.istio.io/proxyCPU=100m` on every
Deployment, `proxyCPULimit` absent. If the fourth frontend pod stays Pending,
set the sidecar request to 90 m, record that, and continue. Do not combine
that with any other schedulability change. Before the post-hold restore
check, set the sidecar request back to 100 m.

Before the hold, `experiments/latch_restore_check.sh` must pass, or
`experiments/latch_restore_fix.sh` is applied and the check is run again.
After the hold, the same check must pass. Do not stop the VMs in this spec.

## 4. Readings

Take every reading in one ~60 s window starting about 120 s after Locust
starts (the ramp at `count/50` is over by then). Read-only SSH. Do not restart
collectors.

**Ceiling, per tag.** On `topfull-load`, read each tag's stats port from
`ports_v2/` (do not hardcode port numbers). Record configured users, current
RPS, and P95. Ratio = current RPS / configured users.

**Candidate 1 — proxy and collectors on `topfull-master`.** Master is 8 vCPU.
Over the 60 s window, sample `/proc/stat` once a second and record mean busy
cores. Record the mean CPU of the `go run proxy_online_boutique.go` process
and of `metric_collector.py`, `envoy_retry_collector.py`,
`resource_usage_collector.py`, and `topfull_throttle_collector.py`.

**Candidate 2 — worker node.** Worker is 16 vCPU. Same `/proc/stat` sample.
Record mean busy cores and mean steal percent.

**Candidate 3 — Envoy threads.** `kubectl top pod --containers -n default`
during the window. Record `istio-proxy` millicores for every pod. On one
frontend pod and on the hottest non-frontend proxy, read the `envoy` or
`pilot-agent` command line for `--concurrency` (`kubectl exec` into
`istio-proxy`). Absent means default; record the word `default` and the envoy
thread count from `ps -eLf`.

**Candidate 4 — shared-path latency.** From the same stats-port reading:
`emptycart` P95, `getproduct` P95, `getcart` P95.

**Also record, from the pulled folder after the hold.** Mean RPS of each tag
over the whole hold (Locust history CSV, drop the first 60 s and the last
5 s). Sum of those five means. Frontend admitted λ from `service_inbound.csv`.
Layer A: fraction of `topfull_throttle.csv` rows whose threshold is below
10000. `emptycart` mean P95 from its Locust CSV over the same window.

## 5. Verdicts

A candidate is over its line when any of its conditions holds. Lines:

| Candidate | Over the line when |
|---|---|
| 1. Master | Mean busy ≥ 7.2 of 8 cores, or the proxy process mean CPU ≥ 80% of one core |
| 2. Worker | Mean busy ≥ 14.4 of 16 cores, or mean steal > 5% |
| 3. Envoy threads | A proxy's CPU stays within 10% of `concurrency × 1000` m for the window. `concurrency` absent → this candidate is **inconclusive**, not cleared |
| 4. Shared path | `emptycart` P95 > 200 ms in the live reading |

Cleared, so it is not named:

- Candidate 4 is cleared when `emptycart` P95 < 100 ms while `getproduct` or
  `getcart` P95 > 1000 ms.
- Candidate 1 is cleared when master mean busy < 6 of 8 and the proxy
  process is < 50% of one core.
- Candidate 2 is cleared when worker mean busy < 13 of 16 and steal ≤ 2%.

**The hold shows the ceiling** when the five-tag mean-RPS sum is from 450
through 680 (680 is 0.85 × 800). Above 680, the ceiling did not appear;
report the four readings anyway and do not name a limiter. Below 450, the
hold collapsed (a checkout latch is the usual reason: checkout streak ≥ 30
and postcheckout achieved < half its users). Do not name a limiter. Do not
repeat the mix. The next step is the emptycart-only isolation hold (§7),
which does not depend on checkout.

**Naming.** Exactly one candidate over its line, the others cleared or (for
candidate 3 only) inconclusive, and the ceiling present: that candidate is
the likely limiter. The isolation hold that tests it is the next spec.
More than one over, or none over: inconclusive. All three isolation holds
are the next spec.

## 6. Gates and bookkeeping

The hold counts only when all of these pass. Same gates as the latch-probe
series:

- Locust `total.csv` rows ≥ 540
- `service_inbound.csv` span 480–900 s
- mesh `gap2_pct` ≤ 10
- frontend `replica_count` 4 on the modal `resource_usage.csv` sample, every
  other service 1
- Layer A threshold below 10000 on ≤ 1% of rows (the proxy was open)

On failure, do not relaunch into the same folder. The next free slot is
run155. After a counted hold, bump `scenario_2_baseline_no_topfull.yaml` to
run155. Write the readings and the verdict into
`Guides and Info/2026-10-05-600-rps-ceiling-snapshot.md`. Update `AGENTS.md`
§4 with the slot and the verdict. Restore Paper-C1 (§3) before the session
ends. Do not stop the VMs unless asked.

## 7. Isolation holds — next step, not this spec

Run these only after the snapshot is scored. Each hold changes one thing
from the snapshot hold. New slots, starting at whatever
`scenario_2_baseline_no_topfull.yaml` says after §6. Same Paper-C1 pin, same
gates, same 120 s reading. Proxy-bypass and collectors-off "rise" when their
five-tag mean-RPS sum is at least 15% above the snapshot hold's sum. The
emptycart series uses its own bar, below.

Which holds to run:

- Snapshot named candidate 1 → proxy-bypass hold, then the collectors-off
  hold only if bypass did not rise.
- Snapshot named candidate 2 or 3 → emptycart-only series. Those two
  candidates are not separable by a config change in this section; a rise
  on one tag alone means the cap is per swarm, and a rise only in the
  combined mix means the cap is the shared node.
- Snapshot named candidate 4, or the snapshot collapsed below 450 →
  emptycart-only series.
- Inconclusive → all three, in the order below.

**Emptycart only.** Three 180 s holds, both controllers off, 120 s cool-off.
`emptycart` users 200, then 400, then 600. Other tags at 0. Reaching about
1 req/s per user at 600 with P95 under 100 ms means one swarm is not capped
at 600. A sum well below the user count at a P95 under 100 ms pins the cap
on that Locust process or on the path in front of a fast tag.

**Proxy bypass.** One 600 s hold at the snapshot mix. Locust's `proxies`
entry for `:8090` is removed so traffic goes to the frontend NodePort
(`HOST`, `http://10.128.0.3:30440`) directly. The Go proxy is not started.
Collectors stay on. A rise names the proxy. No rise clears it.

**Collectors off.** One 600 s hold at the snapshot mix. The proxy stays up
(RL still off). `envoy_retry_collector.py`, `resource_usage_collector.py`,
and `topfull_throttle_collector.py` are not started. Locust CSVs are the
only RPS source, so the mesh span gate does not apply; `total.csv` rows
≥ 540 still does. A rise names collector load on master. No rise clears it.

Do not change `wait_time`, do not resize VMs, and do not raise sidecar
requests or set a sidecar limit in these holds. Those are remedies, and
they wait until a candidate is confirmed.

## 8. Out of scope

Changing Locust's wait model, adding loadgen VMs, raising frontend replicas
or frontend CPU, setting `proxyCPULimit`, and any remedy for a named
candidate. Remedies are a later spec, after the isolation hold that matches
the snapshot's verdict.
