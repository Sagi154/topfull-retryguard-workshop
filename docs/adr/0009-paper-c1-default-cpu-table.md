# Paper-C1 is the default CPU table, and this file is its only source

Every hold uses one CPU table, called Paper-C1. It is locked from both-off run 89 (see [2026-10-02-s2-paper-c1-run89-handoff.md](../../Guides%20and%20Info/2026-10-02-s2-paper-c1-run89-handoff.md)). The table below is the single source of truth. No other doc restates the values; they link here.

| Service | Container | CPU limit (millicores) | Replicas |
|---|---|---|---|
| `frontend` | app | 1150 | 4 (HPA pin) |
| `checkoutservice` | server | 800 | 1 |
| `recommendationservice` | server | 1150 | 1 |
| `productcatalogservice` | server | 800 | HPA max 1 |
| `cartservice` | server | 800 | 1 |
| `currencyservice` | server | 770 | 1 |
| `shippingservice` | server | 770 | 1 |
| `adservice` | server | 1150 | 1 |
| `paymentservice` | server | 155 | 1 |
| `emailservice` | server | 120 | 1 |
| `redis-cart` | redis | 540 | 1 |

The frontend sidecar request is 100m and `proxyCPULimit` stays unset (see AGENTS.md §7). The frontend 1150m is the HPA pin, not a `scale_constraints` entry.

**Rule for scenario configs.** Every scenario YAML carries the full table in `scale_constraints` (frontend excluded). A scenario that constrains a service (S3 checkout, S4A productcatalog, S4B email) writes its constrained value in that service's row and leaves the other ten rows at the table value. The config is then the complete CPU state of the hold. There is no separate "constraint" block and no fraction-based limit, which matches [ADR 0006](0006-absolute-bottleneck-cap-not-fraction.md). S1, S2, S5, and S6 carry the table unchanged.

**Rule for the code.** `PAPER_CPU_LIMIT_MILLICORES` in `experiments/topfull_cpu_quotas.py` mirrors this table. `test_topfull_cpu_quotas.py` parses the table above and fails if the two differ, so edit the ADR first and then the code.

**Rule for the VMs.** Every hold resets the VMs; there is no opt-out. The old `paper_cpu_reconcile` key is removed from the runner and from the live configs; it is ignored where it remains in historical `study_*` YAMLs. Before and after each hold the runner resets all eleven Deployments to this table, which heals leftovers such as a checkout 50m from S3. After the constraints are applied, `verify_live_cpu_limits` in `run_scenario.py` reads the live Deployments and aborts before Locust starts if any limit or request differs from this table plus the config's constrained values.

**Status:** accepted.

**Considered options:** keep the table only in `scenario_2_*.yaml` and let other YAMLs inherit through the runner's reconcile step; store the table in a shared file that YAMLs reference; repeat the full table in each YAML with constrained rows overridden.

**Consequences:**
- A change to the table means editing this ADR first, then every YAML. A YAML whose unconstrained rows differ from this table is wrong, and the YAML is what gets fixed.
- Each config can be read alone to know a hold's exact CPU state, and a diff between two configs shows only the constrained service.
- Holds that used a different table are not comparable: `campaign_48/`, `august_38/`, and any hold before 2026-10-08.
- Re-running an old `study_*` YAML now resets CPU to Paper-C1 too, because the flag no longer exists. Those holds' records are unchanged.
- S1, S3, S4A, S4B, and S6 YAMLs that do not yet carry the full table must be updated to match before their next hold.
- Related: [ADR 0002](0002-k8s-limits-are-detector-cpu-source-of-truth.md) (K8s limits are the detector's CPU source), [ADR 0005](0005-productcatalog-hpa-max-replicas-2.md) (catalog replicas).
