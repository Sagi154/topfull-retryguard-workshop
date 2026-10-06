#!/bin/bash
# Paper-C1 restore gate. Run on topfull-master:  ssh topfull-master bash -s < experiments/latch_restore_check.sh
# Exit 0 only if checkout 800 m x1, recommendations 1150 m x1, every other Paper-C1 limit unchanged,
# frontend HPA 4/4 with 4 ready, catalog HPA 1/1, sidecar request 100 m everywhere with no
# proxyCPULimit, and no Pending pods.
fail=0
check() {
  if [ "$2" != "$3" ]; then echo "FAIL $1: got '$2' want '$3'"; fail=1; else echo "ok   $1 = $2"; fi
}
cpu() {
  kubectl get deploy "$1" -n default -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}'
}
reps() { kubectl get deploy "$1" -n default -o jsonpath='{.spec.replicas}'; }

check checkoutservice_cpu "$(cpu checkoutservice)" 800m
check recommendationservice_cpu "$(cpu recommendationservice)" 1150m
check checkoutservice_replicas "$(reps checkoutservice)" 1
check recommendationservice_replicas "$(reps recommendationservice)" 1
check frontend_cpu "$(cpu frontend)" 1150m
check productcatalogservice_cpu "$(cpu productcatalogservice)" 800m
check cartservice_cpu "$(cpu cartservice)" 800m
check currencyservice_cpu "$(cpu currencyservice)" 770m
check shippingservice_cpu "$(cpu shippingservice)" 770m
check adservice_cpu "$(cpu adservice)" 1150m
check paymentservice_cpu "$(cpu paymentservice)" 155m
check emailservice_cpu "$(cpu emailservice)" 120m
check redis-cart_cpu "$(cpu redis-cart)" 540m

check frontend_hpa_min "$(kubectl get hpa frontend-hpa -n default -o jsonpath='{.spec.minReplicas}')" 4
check frontend_hpa_max "$(kubectl get hpa frontend-hpa -n default -o jsonpath='{.spec.maxReplicas}')" 4
check frontend_ready "$(kubectl get deploy frontend -n default -o jsonpath='{.status.readyReplicas}')" 4
check catalog_hpa_min "$(kubectl get hpa productcatalogservice-hpa -n default -o jsonpath='{.spec.minReplicas}')" 1
check catalog_hpa_max "$(kubectl get hpa productcatalogservice-hpa -n default -o jsonpath='{.spec.maxReplicas}')" 1

for d in $(kubectl get deploy -n default -o jsonpath='{.items[*].metadata.name}'); do
  check "${d}_proxyCPU" "$(kubectl get deploy "$d" -n default -o jsonpath='{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPU}')" 100m
  check "${d}_proxyCPULimit" "$(kubectl get deploy "$d" -n default -o jsonpath='{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPULimit}')" ""
done

check pending_pods "$(kubectl get pods -n default --field-selector=status.phase=Pending --no-headers 2>/dev/null | wc -l)" 0
if [ "$fail" -eq 0 ]; then echo "RESTORE GATE PASS"; else echo "RESTORE GATE FAIL"; fi
exit $fail
