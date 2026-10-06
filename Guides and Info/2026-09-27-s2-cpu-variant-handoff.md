# Handoff: next S2 both-off CPU / replica / user-count variant

Continue the both-off S2 series on the Checkout-4 CPU table in [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md). A variant is three knobs: per-pod CPU limits, replica counts, and Locust user counts. Limits and replica counts are chosen. User counts for the holds are still open.

## Where things stand

Branch `cpu-table-calibration` is pushed (`3eea5a0`, `6ea1597`, `9e5cda2`). The three VMs are **TERMINATED**. The cluster was restored before the stop: backends at 1 replica, frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, paper CPU, sidecar request 100 m, no `proxyCPULimit`.

`experiments/configs/scenario_2_baseline_no_topfull.yaml` is unused **run43**. `scale_constraints` is empty. `paper_cpu_reconcile` is omitted, so the runner restores paper CPU. The locust counts in that file are leftovers from run42 (150/250/150/20/20) and were not launched on run43. `experiments/test_topfull_cpu_quotas.py` `TestBothOffYamlRestored` expects run43. After the next series, point that test at the new unused slot.

`Guides and Info/2026-09-27-s2-checkout3-cpu-runs-39-42.md` is the post-run analysis standard (below). The runs 35–38 guide is the layout it copied.

Do not overwrite run35–run42, or the comparison folders run7, run12, run26, run31, run33, run34.

## What runs 35–38 were

600 s, both controllers off, `spawn_rate` 50, Istio `attempts: 3`, `per_try_timeout_ms: 500`. 360 s cool-off before run35 and between holds. No cool-off after run38.

Per-pod millicores, request equals limit. Replicas pinned for the whole series:

| Service | Quota | Replicas |
|---|---:|---:|
| frontend | 1150 | 4 |
| checkoutservice | 800 | 2 |
| recommendationservice | 800 | 3 |
| productcatalogservice | 600 | 1 |
| cartservice | 600 | 2 |
| currencyservice | 650 | 1 |
| shippingservice | 400 | 1 |
| adservice | 600 | 1 |
| paymentservice | 150 | 2 |
| emailservice | 150 | 2 |
| redis-cart | 500 | 1 |

Deployment total (limit × replicas) is 13,150 m, under the paper four-frontend ceiling of 13,360 m. Quota in the results table is the per-pod limit. `cpu_millicores` in `resource_usage.csv` is the sum across replicas, so a mean can sit above the per-pod quota.

| Slot | Mix | Counts (getproduct / postcheckout / getcart / postcart / emptycart) | Locust rows |
|---|---|---|---:|
| run35 | 7 | 380 / 100 / 270 / 20 / 20 | 565 |
| run36 | 12 | 100 / 150 / 100 / 100 / 5 | 564 |
| run37 | 26 | 325 / 100 / 100 / 100 / 5 | 564 |
| run38 | new | 250 / 150 / 250 / 50 / 50 | 565 |

Sidecar request was **70 m** with no CPU limit. 100 m left a frontend pod Pending (`Insufficient cpu`). 20 pods × 100 m sidecars plus this app table did not fit; 70 m did.

run36's first launch died before Locust (`duplicate session: envoyretry` from an overlapping runner). The same slot was relaunched. The pulled folder is that second hold.

Signals, from [2026-09-27-s2-replica-cpu-runs-35-38.md](2026-09-27-s2-replica-cpu-runs-35-38.md): streak ≥ 30 on a controlled service only on run36 checkoutservice. Overloaded share ≥ 0.5 on checkoutservice for run36 and run38. Layer A admitting rows are 0 on all four.

## How to run the next variant

1. Start the three VMs. Refresh `HostName` in `~/.ssh/config` from `gcloud compute instances list --project=networks-workshop`. SSH aliases only. Confirm `kubectl get nodes` on `topfull-master`.
2. Write the new per-pod limits and replica counts into [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md) before the first hold. Sum limit × replicas and keep that deployment total ≤ 13,360 m.
3. Put only `method: cpu_limit` / `cpu_limit_millicores` in the both-off YAML, with `paper_cpu_reconcile: false`. Leave replica counts out of `scale_constraints`. `restore_constraints` scales a replicas entry back to 1 at the end of every hold. Frontend stays off the list when its limit is still the paper 1150 m. `redis-cart` container name is `redis`; every other container is `server`.
4. Patch CPU while every backend is still 1 replica. Then pin. Frontend and catalog are the only HPAs: set `minReplicas = maxReplicas` to the table count. Scale the other deployments with `kubectl scale`. Paper CPU at the extra replica counts does not fit the worker.
5. Leave `proxyCPULimit` absent. A sidecar CPU limit collapsed storefront latency on earlier holds. Start from the restored request of 100 m. If a pod is Pending with `Insufficient cpu`, lower `sidecar.istio.io/proxyCPU` on all 11 Deployments only until that table schedules. 70 m is the request that fit the Replica table (20 pods, 13,150 m app). It is not the request for the next table. A smaller table may still schedule at 100 m. Record the request that scheduled.
6. Wait until ready counts match the table and pending is 0. Cool off 360 s. Then the holds: 600 s, `spawn_rate` 50, both controllers off. Clear `/tmp/rg_*.sh` and `/tmp/envoy_retry_params.json` on master before each launch. Cool off 360 s between holds.
7. Bump only `run_number`, `log_folder`, `description`, and `locust.user_counts` between holds. Start at run43. Pull with `experiments/pull_results.py`. Gate on Replica-style checks: `service_capacity.json` millicores, `resource_usage.csv` replica counts equal to the pin for every sample, the collector files present, `total.csv` rows ≥ 500.
8. Write the post-run guide as in [Post-run analysis](#post-run-analysis). Score (a)/(b)/(c) with `python experiments/s2_both_off_abc.py` on the new folders and on the earlier runs of the same mixes.
9. Restore before stopping: scale extra replicas back to 1, set frontend HPA to min 1 / max 4 and catalog HPA to min 1 / max 2, then `reconcile_paper_cpu_limits`, then sidecar request 100 m with no limit. Point the YAML at the next free slot with `scale_constraints: []` and no `paper_cpu_reconcile` key. Update `TestBothOffYamlRestored` to that slot.

PowerShell here-strings piped to `ssh ... bash -s` leave a trailing CR on the last line. If a command fails with `\r`, reissue that command. Write scripts with LF when the pipe keeps failing.

## Post-run analysis

After the holds, write a new dated guide in `Guides and Info/`. Copy the layout of [2026-09-27-s2-replica-cpu-runs-35-38.md](2026-09-27-s2-replica-cpu-runs-35-38.md). That file is the standard for how a both-off series is written up. Read (a), (b), and (c) from [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). Leave that reading file unchanged. The results guide applies those three signals; it does not restate them.

The results guide has these sections, in this order:

1. Setup paragraph, then a mix index: this series, the earlier replay of that mix, the earlier both-off hold.
2. **(a)** inbound rejection streak, **(b)** detector overloaded fraction, **(c)** outbound retry edges plus a retry-by-target table, for all 11 services. **Bold** in (a) is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain there. **Bold** in (b) is an overloaded share of at least 0.5.
3. CPU mean / max. The quota column is the per-pod limit, with a replicas column. The mean / max cells are `cpu_millicores` summed across replicas.
4. Locust goodput, Locust fail rate (`Fail / RPS`), and Locust P95 (`Latency95`), each its own table, per API.
5. Inbound arrival rate, per service.
6. Inbound 5xx fraction and inbound reset fraction, as two tables.
7. Inbound sojourn, and the share of inbound requests above 500 ms.
8. CPU use as a fraction of per-pod quota × replicas (mean / max).
9. Detector max utilization.
10. Per-mix prose, then related links.

Comparison columns follow the mix index, left to right within each mix, then the next mix. A bold bar (`**┃**`) separates mix groups, so one mix's runs stay in one section. Each comparison run uses that run's own quota and replica count.

(a)/(b)/(c) come from `experiments/s2_both_off_abc.py`. The other tables come from the Locust CSVs, `service_inbound.csv`, `resource_usage.csv`, and `topfull_detect.csv`.

The guide is done when every section above is present, the mix bars are in the comparison tables, and the (a)/(b) bold rules match the runs 35–38 guide.

## Read next

- Analysis standard (copy this layout): [2026-09-27-s2-checkout3-cpu-runs-39-42.md](2026-09-27-s2-checkout3-cpu-runs-39-42.md). The runs 35–38 guide is the layout that file copied: [2026-09-27-s2-replica-cpu-runs-35-38.md](2026-09-27-s2-replica-cpu-runs-35-38.md).
- Definitions of (a)/(b)/(c): [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- The six CPU tables (Paper, Dispense, Agreed, Replica, Checkout-3, Checkout-4): [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).
- The procedure this series followed: [2026-09-27-s2-replica-cpu-holds.md](../docs/superpowers/plans/2026-09-27-s2-replica-cpu-holds.md).
- Agreed-table comparison holds: [2026-09-26-s2-cpu-spread-runs-30-34.md](2026-09-26-s2-cpu-spread-runs-30-34.md).
