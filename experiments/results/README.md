# Local experiment results

Two datasets, kept separate. **Master** still writes to `/home/idozacharia/experiments/results/<log_folder>/` — this split is **local only**.

| Directory | What | Count | Collectors |
|---|---|---|---|
| [`campaign_48/`](campaign_48/) | Paper-grade Phase 7 campaign (2026-09-05 → 2026-09-06). **Primary analysis dataset.** | 48 | Locust + Envoy retries + `resource_usage.csv` |
| [`august_38/`](august_38/) | Historical Phase 5/6 matrix (2026-08-11 → 2026-08-15). Goodput / P95 / rejection only. | 38 | No Envoy / resource CSVs. S5 never re-enabled. |

Do not mix them in analysis. Do not delete `august_38`. After a new `scp` from master, put campaign-style folders under the matching scenario subfolder of `campaign_48/` (e.g. `campaign_48/S2_sustained_overload/`) — see [campaign_48/README.md](campaign_48/README.md) for the full map and per-scenario destinations.

The 2026-10-01 copy-verification holds sit in [`copy verification/`](copy%20verification/), not inside `campaign_48/`: run85 and run86.

Paper-C1 holds launched on the disk copy sit in [`new vms/`](new%20vms/): run94, run95, run96, run97, run98, run99–run107, latch-probe run108–run126, and the `ck_rep2_pc120` replay runs 128–131. Run116 is in that tree and failed the sampling gate. Run127 was not run. Run132 was stopped before Locust and has no folder. A truncated first launch of run123 is under [`new vms/_discarded/`](new%20vms/_discarded/) and is not a score.

`campaign_48/` is organized into 7 scenario subfolders (`S1_normal_op/`, `S2_sustained_overload/`, `S3_targeted_bottleneck/`, `S4A_topology_position_A/`, `S4B_topology_position_B/`, `S5_interval_tuning/`, `S6_forced_recovery/`), each containing that scenario's baseline + RetryGuard run folders.

Campaign slots: S6 `forced_recovery` run1–3; S5 `interval_*` run3–5; S1–S4A/S4B run4–6.

August slots: S1–S4A/S4B run1–3; S5 `interval_*` run1–2 (flat hold). No Scenario 6.
