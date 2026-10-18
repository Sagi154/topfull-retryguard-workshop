# Round 0 ceiling snapshot (during run60)

Taken about two minutes into both-off S2 run60 (Checkout-3, A2 mix 150/250/150/20/20), while the 600 s hold was already running. No extra hold. The custom stats port is the text line `api=current_rps=current_fail=latency95=latency99` from `locust_online_boutique.py`. It does not report `user_count`. Masters (8888, 8891) stay at zero, as that file documents. Workers and the three standalone processes carry the traffic.

## Users and achieved rate

Configured count is the Locust `-u` on the process. Achieved rate is the sum of `current_rps` across that tag's worker ports. Ratio is achieved rps / configured users. Spawn rate is `count / 50`, so the ramp is 50 s and was over by this reading.

| Tag | Configured users | Ports | Achieved rps | rps / users | P95 (ms) |
|---|---:|---|---:|---:|---|
| postcheckout | 250 | 8889 + 8890 | 67.5 + 64.0 = 131.5 | 0.53 | 2400 / 2500 |
| getproduct | 150 | 8892–8895 | 33.5 + 33.5 + 33.0 + 34.0 = 134.0 | 0.89 | 640 / 610 / 650 / 640 |
| getcart | 150 | 8896 | 147.0 | 0.98 | 550 |
| postcart | 20 | 8897 | 19.0 | 0.95 | 120 |
| emptycart | 20 | 8898 | 19.0 | 0.95 | 23 |

Sum of those current rates is about 450 req/s. The fast tags (emptycart P95 23 ms, postcart 120 ms, getcart 550 ms) sit at 0.95–0.98 of their configured users. A swarm that had not finished ramping would miss that on the fast tags too. The shortfall is on postcheckout, whose P95 is 2.4–2.5 s. `constant_throughput(1)` cannot send one request per second per user while that request is still in flight.

## Load generator

`topfull-load` has 8 cores. Over a 1 s `/proc/stat` sample the idle fraction was **0.898**. No Locust process was near a full core. The busiest were the two postcheckout workers at 16.8% and 16.5% of one core, getcart at 16.5%, and the four getproduct workers at about 9% each. The generator is not the limit.

## Frontend sidecar

`kubectl top pod --containers -l app=frontend` at the same moment:

| Pod | istio-proxy | server |
|---|---:|---:|
| frontend-85ff4b5b6d-gtxsx | 545 m | 286 m |
| frontend-85ff4b5b6d-jh6wf | 463 m | 238 m |
| frontend-85ff4b5b6d-m7dv4 | 463 m | 249 m |
| frontend-85ff4b5b6d-pqs7m | 494 m | 258 m |

The app container is about a quarter of its 1150 m limit. Each proxy is near half a core, with no CPU limit set. emptycart stays at 19 req/s and a 23 ms P95 while those proxies are that busy, so the proxy time is on the slow tags. A sidecar queue in front of every tag would have lifted emptycart's P95 with it.

## What the limiter is

The cap on this hold is the closed loop. Fast tags already run at about one request per second per configured user. postcheckout does not, because each attempt takes about 2.5 s, so those users are busy inside the request and never send the rest. The load VM is idle, and the frontend app container is not at its limit. E1 and E2 are not needed: the snapshot already separates the load generator and the sidecar from the closed-loop wait.
