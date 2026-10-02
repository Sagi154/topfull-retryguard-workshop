# Handoff: S2 Paper-C1, the run 89 mix

Continue the both-off S2 series on the Paper-C1 table in [2026-09-30-s2-lens-blend-handoff.md](2026-09-30-s2-lens-blend-handoff.md). Four holds of one mix are done: **275 / 90 / 100 / 90 / 5** (getproduct / postcheckout / getcart / postcart / emptycart). The blend cleared once. The three replays did not clear it again. The next unused slot is **run96**, already filled with this mix and this pin.

## Where things stand

Branch `s2-paper-c1-run89-replay`. The three VMs were left **RUNNING** on project `project-76deda76-55f1-42d2-abb`. The cluster was left on the Paper-C1 pin: frontend HPA min 4 / max 4, every other service at 1 replica, sidecar request 100 m, no `proxyCPULimit`.

`experiments/configs/scenario_2_baseline_no_topfull.yaml` is unused **run96**. `paper_cpu_reconcile: false`. `scale_constraints` is the Paper-C1 table below. The locust counts are 275 / 90 / 100 / 90 / 5. `experiments/test_topfull_cpu_quotas.py` `TestBothOffYamlRestored` still expects unused run87 with empty `scale_constraints` and paper reconcile on. Leave that test until the series stops and the YAML is restored. After the series, point it at the new unused slot.

Full tables for the four holds: [2026-10-02-s2-paper-c1-run89-replay.md](2026-10-02-s2-paper-c1-run89-replay.md).

Do not overwrite run89, run92, run94, or run95.

## What runs 89, 92, 94, and 95 were

600 s, both controllers off, `spawn_rate` 50, Istio `attempts: 3`, `per_try_timeout_ms: 500`. Paper-C1, frontend pinned at 4, every other service at 1, sidecar request 100 m with no CPU limit. run89 and run92 ran 2026-10-01. run94 and run95 ran 2026-10-02 on the disk copy. Folders: run89 and run92 stay in `experiments/results/campaign_48/S2_sustained_overload/`. run94, run95, and run96 are in `experiments/results/new vms/`.

Per-pod millicores, request equals limit. Frontend is × 4. Deployment total is 11,655 m.

| Service | Quota | Replicas |
|---|---:|---:|
| frontend | 1150 | 4 |
| checkoutservice | 800 | 1 |
| recommendationservice | 1150 | 1 |
| productcatalogservice | 800 | 1 |
| cartservice | 800 | 1 |
| currencyservice | 770 | 1 |
| shippingservice | 770 | 1 |
| adservice | 1150 | 1 |
| paymentservice | 155 | 1 |
| emailservice | 120 | 1 |
| redis-cart | 540 | 1 |

| Slot | Mix | Counts (getproduct / postcheckout / getcart / postcart / emptycart) | Locust rows | Frontend replicas |
|---|---|---|---:|---|
| run89 | run89 | 275 / 90 / 100 / 90 / 5 | 567 | 4 on 134/134 |
| run92 | replay | 275 / 90 / 100 / 90 / 5 | 565 | 4 on 134/134 |
| run94 | third | 275 / 90 / 100 / 90 / 5 | 558 | 4 on 133/133 |
| run95 | fourth | 275 / 90 / 100 / 90 / 5 | 563 | 4 on 133/133 |

Every other service stayed at 1 replica on every resource sample. Mesh gaps of 1.5 s or more were 0% on all four. Layer A admitting rows are 0 on all four. Sampling is 1 s. All four holds are scorable.

Pass bar, from the lens-blend handoff. Streak = `(Δ5xx + Δresets) / Δtotal > 0.20` on consecutive 1 s inbound polls. Overloaded tick = `topfull_detect.csv` `overloaded=1`. A blend needs recommendations (streak ≥ 10 and ≥ 10 overloaded ticks), checkout (the same), and a chain leaf (email or payment with ≥ 10 overloaded ticks). Retry volume, goodput, and max utilization are recorded and do not pass or fail a hold. A blend counts after a replay also clears it. **Bold** in the (a) table of the results guide is the separate RetryGuard length, streak ≥ 30 on a controlled service.

| Slot | Rec streak | Rec ov | Checkout streak | Checkout ov | Email ov | Payment ov | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| run89 | 238 | 485 | 58 | 164 | 23 | 0 | blend |
| run92 | 454 | 480 | 59 | 128 | 6 | 5 | independent pair; leaf missed |
| run94 | 0 | 0 | 564 | 590 | 16 | 10 | checkout latch; recommendations cold |
| run95 | 0 | 0 | 568 | 591 | 11 | 0 | checkout latch; recommendations cold |

run89 clears all three rows. The leaf is thin: email is 23 of 638 detector ticks (3.6%), streak 5. run92 keeps checkout and recommendations and drops the leaf under 10 ticks. run94 and run95 latch checkout for the whole scored series (streak 564 / 568, overloaded 92.8% / 93.1%, frontend → checkout retries 61,002 / 61,643) and leave recommendations at streak 0, overloaded 0, retries 0. Browse goodput on those two holds is getproduct about 264 req/s, fail 0, P95 about 300 ms. postcheckout goodput is about 3 req/s with fail about 0.93.

## How to run the next hold

run96 is already the fifth hold of this mix. The pin and the YAML constraints are already in place.

1. Confirm the three VMs are `RUNNING` with `gcloud compute instances list --project=project-76deda76-55f1-42d2-abb`. Refresh `HostName` in `~/.ssh/config` if any address changed. SSH aliases only. Confirm `kubectl get nodes` on `topfull-master`.
2. Confirm the pin before launch: frontend ready 4/4, every other Boutique deployment ready 1/1, pending 0. Sidecar annotation `sidecar.istio.io/proxyCPU=100m` on all 11 Deployments, `proxyCPULimit` absent. `service_capacity.json` from the next pull must match the table above.
3. Cool off 300 s from the end of run95 if that window has not already elapsed. Then launch. Clear `/tmp/rg_*.sh` and `/tmp/envoy_retry_params.json` on master before the launch.

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

4. Gate on the same checks as the four holds: `service_capacity.json` millicores match Paper-C1, `resource_usage.csv` replica counts equal the pin on every sample (frontend 4, everything else 1), collector files present, `total.csv` rows ≥ 500, mesh span about 600 s, at least 90% of `service_inbound.csv` gaps under 1.5 s. A failed gate means the hold is not scored. Keep the folder. Bump to the next free slot for a relaunch.
5. Score with `python experiments/s2_both_off_abc.py` on the new folder and on run89, run92, run94, and run95. Write the post-run guide as in [Post-run analysis](#post-run-analysis).
6. To keep going on this pin, bump only `run_number`, `log_folder`, `description`, and `locust.user_counts`. Leave `paper_cpu_reconcile: false` and the Paper-C1 `scale_constraints` in place. Cool off 300 s between holds.
7. Restore before stopping: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, then `reconcile_paper_cpu_limits`, then sidecar request 100 m with no limit. Point the YAML at the next free slot with `scale_constraints: []` and no `paper_cpu_reconcile` key. Update `TestBothOffYamlRestored` to that slot.

PowerShell here-strings piped to `ssh ... bash -s` leave a trailing CR on the last line. If a command fails with `\r`, reissue that command. Write scripts with LF when the pipe keeps failing.

## Post-run analysis

After the hold, add it to a dated guide in `Guides and Info/`, or extend [2026-10-02-s2-paper-c1-run89-replay.md](2026-10-02-s2-paper-c1-run89-replay.md) if the mix is unchanged. That file is the standard for this series. Read (a), (b), and (c) from [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). Leave that reading file unchanged.

The results guide has these sections, in this order:

1. Setup paragraph, then the pass-bar table (recommendations, checkout, chain leaf, verdict).
2. Gates: Locust rows, mesh span, sampling gaps, replica pin, Layer A admitting rows.
3. CPU table.
4. **(a)** inbound rejection streak, **(b)** detector overloaded fraction, **(c)** outbound retry edges plus a retry-by-target table, for all 11 services. **Bold** in (a) is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain there. **Bold** in (b) is an overloaded share of at least 0.5.
5. CPU mean / max. The quota column is the per-pod limit. The mean / max cells are `cpu_millicores` summed across replicas.
6. Locust goodput, Locust fail rate (`Fail / RPS`), and Locust P95 (`Latency95`), each its own table, per API.
7. Inbound arrival rate, per service.
8. Inbound 5xx fraction and inbound reset fraction, as two tables.
9. Inbound sojourn, and the share of inbound requests above 500 ms.
10. CPU use as a fraction of per-pod quota × replicas (mean / max).
11. Detector max utilization.
12. Per-hold prose, then where the mix stands.

(a)/(b)/(c) come from `experiments/s2_both_off_abc.py`. The other tables come from the Locust CSVs, `service_inbound.csv`, `resource_usage.csv`, and `topfull_detect.csv`.

The guide is done when every section above is present and the (a)/(b) bold rules match the runs 35–38 guide.

## Read next

- Full tables for these four holds: [2026-10-02-s2-paper-c1-run89-replay.md](2026-10-02-s2-paper-c1-run89-replay.md).
- Pass bar and the C1 table: [2026-09-30-s2-lens-blend-handoff.md](2026-09-30-s2-lens-blend-handoff.md).
- Earlier Paper-C1 holds on this table: [2026-10-01-s2-paper-c1-runs-80-84-88.md](2026-10-01-s2-paper-c1-runs-80-84-88.md).
- Definitions of (a)/(b)/(c): [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- The procedure this handoff follows: [2026-09-27-s2-cpu-variant-handoff.md](2026-09-27-s2-cpu-variant-handoff.md).
- Checkout retry-latching: [2026-09-25-s2-overload-user-count-calibration.md](../docs/superpowers/specs/2026-09-25-s2-overload-user-count-calibration.md).
