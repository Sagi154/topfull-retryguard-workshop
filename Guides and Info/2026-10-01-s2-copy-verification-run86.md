# S2 copy-verification hold, run86

Both controllers off, 600 s, on the disk copy in project `project-76deda76-55f1-42d2-abb`. This replays the Hybrid pair run68 / run70. Mix is getproduct / postcheckout / getcart / postcart / emptycart = **270 / 200 / 280 / 10 / 10**, `spawn_rate` 50. Istio `attempts: 3`, `perTryTimeout` 500 ms. `paper_cpu_reconcile` was false, so the runner left the Hybrid CPU table in place. Frontend HPA was pinned min = max = 4 before Locust. Checkout was scaled to 2. Catalog HPA max was 1. Sidecar request was 100 m, with no CPU limit. The three VMs are **TERMINATED** after the pull.

Folder: `experiments/results/copy verification/baseline_no_topfull_sustained_overload_run86`.

(a)/(b)/(c) below are from `experiments/s2_both_off_abc.py`.

## Hold index

| Slot | Where | Mix | Controllers | Locust rows | Mesh span | gap2 | Layer A admitting rows |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| run68 | `networks-workshop` | 270/200/280/10/10 | both off | 571 | 692 s | 0% | 0 |
| run70 | `networks-workshop` | 270/200/280/10/10 | both off | 569 | 691 s | 0% | 0 |
| run86 | copied project | 270/200/280/10/10 | both off | 543 | 695 s | 65% | 0 |

Layer A `threshold` is only 0 or 10000 on run86 (3175 samples at 10000, 20 at 0). The last sample of every API is 10000. That is the passthrough sentinel: TopFull admission stayed off, same as run68 and run70.

`service_capacity.json` on run86 is the Hybrid table: frontend 1150 m × 4, checkout 800 m × 2, recommendations 1150 m × 1, catalog / cart / ad 600 m, currency 650 m, shipping 400 m, payment / email 200 m, redis-cart 300 m. Resource samples: frontend `replica_count` 4 on 134/134, checkout 2 on 134/134.

## Verdict

The copy ran this Hybrid setup and produced the same recommendations retry storm as the pair.

Recommendations arrival is 710 req/s on run86 versus 707 and 702. Sojourn is 473 ms versus 480 and 478. Detector overloaded share is 83.4% versus 90.3% and 89.3%. Frontend → recommendations retries are 270,387 versus 248,174 and 239,565. Frontend CPU mean is 1049 m versus 1050 and 1074, with the pin held at 4 for the whole window. Only frontend retried.

It is not a tight numerical replay of the pair:

- Recommendations rejection stayed above 0.20 for a streak of 212 (304 high samples, failure fraction 0.319). The pair flickered: 453 and 426 high samples, but the longest streak was 17 and 16, and the failure fraction was 0.222 and 0.219.
- Checkout's detector share rose to 272/639 (42.6%) from 5/638 and 6/637. Inbound failure stays small (0.020 versus 0.005 and 0.004) and sojourn stays about 79 ms, under the 500 ms `perTryTimeout`. Streak is 8 versus 1.
- Email overloaded ticks are 106/639 (16.6%) versus 9/638 and 6/637.
- Storefront total goodput is 122 req/s versus 156 and 171. Browse and checkout P95 stay near 2.1 s on all three.
- Mesh polls ran slow: 4,642 inbound rows and 422 checkout polls, gap2 65%, versus about 7,600 rows, about 690 polls, and gap2 0% on the pair. The span is still about 695 s. The slower poll does not explain the streak of 212 on its own; the failure fraction is higher as well.

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart are outside that set.

| Service | run68 | run70 | run86 |
| --- | ---: | ---: | ---: |
| frontend (not controlled) | 578 / 578 | 576 / 576 | 212 / 305 |
| checkoutservice | 1 / 1 | 1 / 1 | 8 / 8 |
| recommendationservice | 17 / 453 | 16 / 426 | **212 / 304** |
| paymentservice | 0 / 0 | 0 / 0 | 8 / 8 |
| emailservice | 1 / 2 | 1 / 2 | 1 / 1 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 1 / 1 | 0 / 0 | 0 / 0 |
| shippingservice | 1 / 1 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 |

## (b) Detector overloaded ticks

`overloaded=1` over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

| Service | run68 | run70 | run86 |
| --- | ---: | ---: | ---: |
| frontend | 0/638 (0.0%) | 0/637 (0.0%) | 0/639 (0.0%) |
| checkoutservice | 5/638 (0.8%) | 6/637 (0.9%) | 272/639 (42.6%) |
| recommendationservice | **576/638 (90.3%)** | **569/637 (89.3%)** | **533/639 (83.4%)** |
| paymentservice | 0/638 (0.0%) | 0/637 (0.0%) | 14/639 (2.2%) |
| emailservice | 9/638 (1.4%) | 6/637 (0.9%) | 106/639 (16.6%) |
| productcatalogservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/639 (0.0%) |
| cartservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/639 (0.0%) |
| currencyservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/639 (0.0%) |
| shippingservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/639 (0.0%) |
| adservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/639 (0.0%) |
| redis-cart | 0/638 (0.0%) | 0/637 (0.0%) | 0/639 (0.0%) |

## (c) Outbound retry delta

- **run68.** frontend → recommendationservice 248,174, frontend → checkoutservice 227.
- **run70.** frontend → recommendationservice 239,565, frontend → checkoutservice 214.
- **run86.** frontend → recommendationservice 270,387, frontend → checkoutservice 846, frontend → cartservice 6.

No caller other than frontend retried on any of the three holds.

| Service | run68 | run70 | run86 |
| --- | ---: | ---: | ---: |
| recommendationservice | 248,174 | 239,565 | 270,387 |
| checkoutservice | 227 | 214 | 846 |
| cartservice | 0 | 0 | 6 |
| paymentservice | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 |

## Inbound failure fraction

Δ(5xx+resets) / Δtotal over the mesh span.

| Service | run68 | run70 | run86 |
| --- | ---: | ---: | ---: |
| frontend | 0.457 | 0.423 | 0.507 |
| checkoutservice | 0.005 | 0.004 | 0.020 |
| recommendationservice | 0.222 | 0.219 | 0.319 |
| paymentservice | 0.000 | 0.000 | 0.036 |
| emailservice | 0.006 | 0.006 | 0.001 |

## CPU mean / max

App-container millicores from `resource_usage.csv`, mean / max. Frontend and checkout replica counts are from that file. Master is the node total on the 8-vCPU control plane.

| Service | run68 | run70 | run86 |
| --- | ---: | ---: | ---: |
| frontend (×4) | 1050 / 1408 | 1074 / 1383 | 1049 / 1317 |
| checkoutservice (×2) | 736 / 1261 | 785 / 1124 | 756 / 1240 |
| recommendationservice | 893 / 1049 | 886 / 1040 | 874 / 1142 |
| emailservice | 87 / 164 | 93 / 149 | 83 / 131 |
| paymentservice | 47 / 91 | 50 / 79 | 53 / 173 |
| master node | 3939 / 6310 | 4108 / 5967 | 4274 / 6030 |

## Locust

Mean while `RPS` > 0. `Fail / RPS` counts SLO misses, not only HTTP 5xx.

| API | run68 goodput | run70 goodput | run86 goodput | run68 fail | run70 fail | run86 fail | run68 P95 | run70 P95 | run86 P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 48.1 | 53.7 | 32.7 | 0.670 | 0.635 | 0.741 | 2084 | 2082 | 2103 |
| postcheckout | 38.1 | 41.8 | 30.5 | 0.650 | 0.619 | 0.689 | 2056 | 2057 | 2076 |
| getcart | 55.8 | 61.8 | 45.0 | 0.641 | 0.606 | 0.686 | 2007 | 2008 | 2063 |
| postcart | 7.0 | 7.1 | 6.4 | 0.103 | 0.091 | 0.062 | 61 | 67 | 69 |
| emptycart | 6.9 | 7.0 | 7.5 | 0.108 | 0.101 | 0.037 | 16 | 18 | 25 |
| total | 155.7 | 171.2 | 121.9 | 0.634 | 0.601 | 0.680 | 1243 | 1245 | 1266 |

postcart and emptycart stay on the fast path. Browse and checkout goodput are lower on run86, with P95 still around 2.1 s.

## Inbound arrival and sojourn

Mean inbound requests/s (Δtotal / mesh span) and mean sojourn (Δ`rq_time_sum_ms` / Δ`rq_time_count`).

| Service | run68 req/s | run70 req/s | run86 req/s | run68 W ms | run70 W ms | run86 W ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 360.9 | 367.8 | 334.1 | 1026 | 1001 | 1126 |
| checkoutservice | 50.2 | 54.2 | 43.9 | 76 | 77 | 79 |
| recommendationservice | 707.1 | 702.0 | 709.8 | 480 | 478 | 473 |
| paymentservice | 50.2 | 54.2 | 43.9 | 2 | 2 | 7 |
| emailservice | 50.2 | 54.2 | 42.1 | 8 | 8 | 6 |

Recommendations arrival and sojourn line up across the three holds. The extra heat on run86 is the failure fraction and the long streak, not a different arrival rate. Checkout sojourn stays near 80 ms on all three while its detector share does not.
