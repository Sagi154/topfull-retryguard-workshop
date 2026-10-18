# S2 run 89 mix, four arms, second pair

600 s holds, mix getproduct 275 / postcheckout 90 / getcart 100 / postcart 90 / emptycart 5, `spawn_rate` 50, Paper-C1, 360 s cool-off between holds. Two holds per arm. Folders are under `experiments/results/campaign_48/S2_sustained_overload/`. The earlier pair of this mix is [2026-10-07-s2-run89-four-arms.md](2026-10-07-s2-run89-four-arms.md).

Goodput, failure fraction (`Fail / RPS`), and P95 are means over the Locust `total.csv` rows. Locust lines include the header. Frontend is the count of `resource_usage.csv` samples at 4 replicas. The rejection streak drops the last 5 inbound polls and counts consecutive ticks with `(Δ5xx + Δresets) / Δtotal > 0.20` on a controlled service. The retry column is the largest first-to-last `retry` delta on `service_edges.csv`.

Every hold passed the gate: `total.csv` at least 500 lines, frontend at 4 on every resource sample, every other service at 1, no zero replica count, and `service_capacity.json` on the Paper-C1 millicores. Run 160's mesh file spans 999 s with one 142 s gap before Locust, during collector startup. Run 25 spans 1052 s with one 175 s gap in the same startup window. The other six spans are 697–728 s with a max gap of 2–3 s.

| Slot | Arm | Locust lines | Goodput | Fail | P95 ms | Frontend | Streak | Largest retry edge |
|---|---|---:|---:|---:|---:|---|---|---|
| 160 | RG off, TF off | 740 | 200.2 | 0.473 | 1264 | 167/167 | checkout 8 | frontend → recommendations 459,907 |
| 161 | RG off, TF off | 565 | 217.8 | 0.435 | 1225 | 134/134 | checkout 11 | frontend → recommendations 257,454 |
| 20 | RG on, TF off | 564 | 380.8 | 0.245 | 566 | 140/140 | checkout 45 | frontend → recommendations 72,892 |
| 21 | RG on, TF off | 563 | 368.2 | 0.281 | 510 | 140/140 | checkout 16 | frontend → recommendations 31,496 |
| 39 | RG off, TF on | 557 | 116.7 | 0.636 | 1224 | 135/135 | checkout 4 | frontend → recommendations 347,746 |
| 40 | RG off, TF on | 554 | 399.2 | 0.229 | 312 | 135/135 | checkout 5 | frontend → checkout 17,877 |
| 24 | RG on, TF on | 554 | 319.4 | 0.361 | 566 | 140/140 | checkout 5 | frontend → recommendations 66,302 |
| 25 | RG on, TF on | 754 | 211.2 | 0.563 | 418 | 171/171 | recommendations 2 | frontend → recommendations 201,165 |

RetryGuard toggles:

- Run 20: `frontend→checkoutservice` 3× ON→OFF and 3× OFF→ON; `frontend→recommendationservice` 3× ON→OFF and 2× OFF→ON. The last recommendations disable stayed at 0 attempts.
- Run 21: 1× ON→OFF on `frontend→recommendationservice`, no OFF→ON.
- Run 24: 1× ON→OFF on `frontend→recommendationservice`, no OFF→ON.
- Run 25: no toggles.

YAML next-free: both-off **162**, RetryGuard-only **22**, TopFull-only **41**, both-on **26**. The cluster was left on the Paper-C1 pin.
