# Run comparison

Steady window: drop first 60 s and last 10 s.

## Headline

| Run | Services overloaded at once | Hot services (util p95 >= 0.85) |
|---|---|---|
| ref | max 2, mean 1.018 | checkoutservice |
| A | max 1, mean 0.123 | (none >= 0.85) |
| B | max 1, mean 0.696 | recommendationservice |

## 1. Load sent

| Run | getproduct RPS / goodput / P95 | getcart RPS / goodput / P95 | postcart RPS / goodput / P95 | emptycart RPS / goodput / P95 | postcheckout RPS / goodput / P95 |
|---|---|---|---|---|---|
| ref | 274.0 / 243.0 / 725.4 | 196.0 / 176.9 / 461.1 | 47.0 / 47.0 / 96.6 | 46.0 / 45.8 / 56.5 | 41.2 / 20.4 / 1789.1 |
| A | 225.6 / 129.7 / 2114.2 | 164.3 / 103.9 / 1981.2 | 44.0 / 43.9 / 73.8 | 44.0 / 43.9 / 28.2 | 45.5 / 28.3 / 2019.4 |
| B | 219.0 / 91.2 / 2174.1 | 163.7 / 80.7 / 2098.6 | 33.0 / 27.3 / 66.9 | 33.0 / 31.3 / 18.9 | 46.4 / 22.9 / 2105.6 |

## 2. TopFull cap

| Run | emptycart share-capped / thresh / admitted | getcart share-capped / thresh / admitted | getproduct share-capped / thresh / admitted | postcart share-capped / thresh / admitted | postcheckout share-capped / thresh / admitted |
|---|---|---|---|---|---|
| ref | 0.989 / 105.6 / 40.0 | 0.989 / 279.8 / 171.8 | 0.989 / 105.6 / 236.7 | 0.989 / 105.6 / 40.0 | 0.993 / 70.8 / 47.9 |
| A | 0.000 / 10000.0 / 39.9 | 0.000 / 10000.0 / 169.8 | 0.000 / 10000.0 / 236.6 | 0.000 / 10000.0 / 39.9 | 0.000 / 10000.0 / 47.9 |
| B | 0.000 / 10000.0 / 30.0 | 0.000 / 10000.0 / 177.0 | 0.000 / 10000.0 / 244.0 | 0.000 / 10000.0 / 30.0 | 0.000 / 10000.0 / 48.0 |

## 3. Backend arrivals

| Run | adservice λ / fail / Wms | cartservice λ / fail / Wms | checkoutservice λ / fail / Wms | currencyservice λ / fail / Wms | emailservice λ / fail / Wms | frontend λ / fail / Wms | paymentservice λ / fail / Wms | productcatalogservice λ / fail / Wms | recommendationservice λ / fail / Wms | redis-cart λ / fail / Wms | shippingservice λ / fail / Wms | Δretry |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ref | 227.29 / 0.000 / 1.9 | 592.10 / 0.004 / 7.1 | 69.18 / 0.299 / 399.2 | 877.68 / 0.000 / 26.9 | 26.91 / 0.048 / 7.0 | 516.63 / 0.029 / 357.6 | 68.17 / 0.006 / 4.2 | 2849.22 / 0.000 / 3.7 | 430.06 / 0.000 / 145.9 | 0.00 / 0.000 / n/a | 295.11 / 0.004 / 1.2 | 20254 |
| A | 160.81 / 0.000 / 1.2 | 508.75 / 0.000 / 2.7 | 32.69 / 0.000 / 47.5 | 756.40 / 0.000 / 4.2 | 32.70 / 0.000 / 4.6 | 486.02 / 0.188 / 659.1 | 32.69 / 0.000 / 2.5 | 2269.81 / 0.000 / 3.5 | 607.73 / 0.161 / 456.6 | 0.00 / 0.000 / n/a | 184.51 / 0.000 / 0.5 | 128314 |
| B | 132.61 / 0.000 / 1.1 | 472.85 / 0.000 / 2.3 | 29.00 / 0.000 / 48.4 | 725.92 / 0.000 / 3.2 | 29.00 / 0.000 / 4.6 | 458.42 / 0.299 / 808.7 | 28.99 / 0.000 / 2.3 | 2012.95 / 0.000 / 2.9 | 706.03 / 0.218 / 469.0 | 0.00 / 0.000 / n/a | 161.06 / 0.000 / 0.6 | 188770 |

## 4. Utilization

| Run | adservice p95 / ovl-share | cartservice p95 / ovl-share | checkoutservice p95 / ovl-share | currencyservice p95 / ovl-share | emailservice p95 / ovl-share | frontend p95 / ovl-share | paymentservice p95 / ovl-share | productcatalogservice p95 / ovl-share | recommendationservice p95 / ovl-share | redis-cart p95 / ovl-share | shippingservice p95 / ovl-share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ref | 0.110 / 0.000 | 0.178 / 0.000 | 0.993 / 0.991 | 0.483 / 0.000 | 0.516 / 0.000 | 0.305 / 0.000 | 0.413 / 0.000 | 0.356 / 0.000 | 0.740 / 0.026 | 0.048 / 0.000 | 0.173 / 0.000 |
| A | 0.248 / 0.004 | 0.339 / 0.000 | 0.513 / 0.000 | 0.584 / 0.000 | 0.465 / 0.000 | 0.238 / 0.000 | 0.342 / 0.000 | 0.311 / 0.000 | 0.790 / 0.119 | 0.067 / 0.000 | 0.148 / 0.000 |
| B | 0.109 / 0.000 | 0.359 / 0.000 | 0.501 / 0.000 | 0.592 / 0.000 | 0.458 / 0.000 | 0.233 / 0.000 | 0.258 / 0.000 | 0.307 / 0.000 | 0.889 / 0.696 | 0.070 / 0.000 | 0.145 / 0.000 |

## 5. Machines

| Run | Master cores p95 / max | Worker cores p95 / max | Load cores p95 / max | Locust %CPU max |
|---|---|---|---|---|
| ref | 6.30 / 6.75 | n/a (no worker_cpu.txt) | n/a (no load_cpu.txt) | n/a |
| A | 6.05 / 6.33 | 11.79 / 12.21 | 0.95 / 2.00 | 26.7 |
| B | 6.28 / 6.70 | 11.78 / 12.22 | 1.00 / 1.85 | 27.8 |
