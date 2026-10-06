#!/bin/bash
set -eu
for dep in frontend cartservice checkoutservice productcatalogservice paymentservice recommendationservice shippingservice currencyservice emailservice adservice redis-cart; do
  echo "SIDECAR $dep"
  kubectl patch deployment "$dep" -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"90m"}}}}}'
  kubectl annotate deployment "$dep" -n default sidecar.istio.io/proxyCPULimit- || true
  kubectl rollout status "deployment/$dep" -n default --timeout=240s
done
echo SIDECAR_DONE
