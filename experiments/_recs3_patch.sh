#!/bin/bash
set -eu
patch() {
  dep="$1"; container="$2"; milli="$3"
  echo "PATCH $dep $milli"
  kubectl set resources "deployment/$dep" -n default -c "$container" --limits=cpu=${milli}m --requests=cpu=${milli}m
  kubectl rollout status "deployment/$dep" -n default --timeout=180s
}
patch frontend server 1050
patch checkoutservice server 800
patch recommendationservice server 700
patch productcatalogservice server 600
patch cartservice server 600
patch currencyservice server 600
patch shippingservice server 400
patch adservice server 500
patch paymentservice server 250
patch emailservice server 250
patch redis-cart redis 250
echo PATCH_DONE
