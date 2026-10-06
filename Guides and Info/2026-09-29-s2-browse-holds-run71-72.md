# S2 browse holds, runs 71–73

600 s both-off holds (`topfull_rl` off, RetryGuard off, `spawn_rate` 50, Istio attempts 3, `perTryTimeout` 500 ms). How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). CPU tables: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md). Every (a)/(b)/(c) number below is from `experiments/s2_both_off_abc.py` on that run folder. Locust row counts and replica dips are from `total.csv` and `resource_usage.csv`.

Counts are getproduct / postcheckout / getcart / postcart / emptycart. Frontend stays the paper 1150 m. Catalog HPA was `min=max=1` on all three holds. Layer A admitting rows are 0 on all three.

## CPU tables

Millicores per pod. Request equals limit. Sidecar CPU is not in the deployment total.

**run71** — mix 250 / 250 / 250 / 50 / 50. Sidecar request **100 m**, no CPU limit. Deployment total **12,850 m**. Replica gate passed.

| Service | Millicores | Replicas | Total |
|---|---:|---:|---:|
| frontend | 1150 | 4 | 4600 |
| checkoutservice | 900 | 3 | 2700 |
| recommendationservice | 900 | 2 | 1800 |
| productcatalogservice | 600 | 1 | 600 |
| cartservice | 600 | 1 | 600 |
| currencyservice | 650 | 1 | 650 |
| shippingservice | 400 | 1 | 400 |
| adservice | 600 | 1 | 600 |
| paymentservice | 300 | 1 | 300 |
| emailservice | 300 | 1 | 300 |
| redis-cart | 300 | 1 | 300 |

**run72** — mix 300 / 200 / 300 / 50 / 50. Same per-pod limits. Frontend HPA 5 left the fifth pod Pending (`Insufficient cpu`) at sidecar request 100 m, so sidecar request dropped to **90 m** with no CPU limit before the hold. Deployment total **13,100 m**. Replica gate passed.

| Service | Millicores | Replicas | Total |
|---|---:|---:|---:|
| frontend | 1150 | 5 | 5750 |
| checkoutservice | 900 | 2 | 1800 |
| recommendationservice | 900 | 2 | 1800 |
| productcatalogservice | 600 | 1 | 600 |
| cartservice | 600 | 1 | 600 |
| currencyservice | 650 | 1 | 650 |
| shippingservice | 400 | 1 | 400 |
| adservice | 600 | 1 | 600 |
| paymentservice | 300 | 1 | 300 |
| emailservice | 300 | 1 | 300 |
| redis-cart | 300 | 1 | 300 |

**run73** — mix 350 / 275 / 350 / 50 / 50. Same table and sidecar as run72. Replica gate passed.

## Hold index

| Slot | Mix | Sidecar | Locust rows | Mesh span | Gate |
| --- | ---: | --- | ---: | ---: | --- |
| run71 | 250/250/250/50/50 | 100 m | 571 | 691 s | pass |
| run72 | 300/200/300/50/50 | 90 m | 571 | 692 s | pass |
| run73 | 350/275/350/50/50 | 90 m | 540 | 692 s | pass |

## (a) / (b) / (c)

| Hold | (a) controlled ≥ 30 | (b) ≥ 0.5 | (c) top edges |
| --- | --- | --- | --- |
| run71 | none (checkout streak 1, email 0) | none (email 48.0%) | frontend → checkout 98, frontend → recommendations 16 |
| run72 | none (recommendations streak 10, checkout 2) | none (checkout 41.9%) | frontend → recommendations 83,360, frontend → checkout 252 |
| run73 | none (recommendations streak 2, checkout 0) | checkout 91.2% | frontend → recommendations 35,015, frontend → checkout 2 |

run71 cooled the run61 chain: checkout CPU mean 1,766 m across three 900 m pods, payment mean 117 m of 300 m, email mean 214 m of 300 m (overloaded share 48.0%, just under 0.5). Recommendations max 916 m of 1,800 m.

run72 moved retry mass onto recommendations (83,360) with inbound failure 0.138 and streak 10. Checkout overloaded share 41.9% at two 900 m pods. Email and payment stayed cold.

run73 is the same pin as run72 with more configured users. Checkout went detector-hot (91.2%) without an inbound streak (failure 0). Recommendations retries fell from 83,360 to 35,015 and streak from 10 to 2. Frontend app CPU stayed similar (mean 1,236 m / max 1,425 m of 5,750 m). Extra configured users did not produce a second (a) bar.

Paper CPU and HPAs restored after the holds (frontend 1–4, catalog max 2, sidecar `proxyCPU` 100 m, limit unset). Next free both-off slot **run74**.
