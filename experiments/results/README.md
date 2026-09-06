# Local experiment results

Two datasets, kept separate. **Master** still writes to `/home/idozacharia/experiments/results/<log_folder>/` — this split is **local only**.

| Directory | What | Count | Collectors |
|---|---|---|---|
| [`campaign_48/`](campaign_48/) | Paper-grade Phase 7 campaign (2026-09-05 → 2026-09-06). **Primary analysis dataset.** | 48 | Locust + Envoy retries + `resource_usage.csv` |
| [`august_38/`](august_38/) | Historical Phase 5/6 matrix (2026-08-11 → 2026-08-15). Goodput / P95 / rejection only. | 38 | No Envoy / resource CSVs. S5 never re-enabled. |

Do not mix them in analysis. Do not delete `august_38`. After a new `scp` from master, put campaign-style folders under `campaign_48/`.

Campaign slots: S6 `forced_recovery` run1–3; S5 `interval_*` run3–5; S1–S4A/S4B run4–6.

August slots: S1–S4A/S4B run1–3; S5 `interval_*` run1–2 (flat hold). No Scenario 6.
