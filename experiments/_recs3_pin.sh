#!/bin/bash
set -eu
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":4,"maxReplicas":4}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":1}}'
kubectl scale deployment/checkoutservice -n default --replicas=4
kubectl scale deployment/recommendationservice -n default --replicas=3
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18; do
  echo "TRY $i"
  kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,DESIRED:.spec.replicas
  pending=$(kubectl get pods -n default --field-selector=status.phase=Pending --no-headers | wc -l)
  echo "pending=$pending"
  fe=$(kubectl get deploy frontend -n default -o jsonpath='{.status.readyReplicas}')
  co=$(kubectl get deploy checkoutservice -n default -o jsonpath='{.status.readyReplicas}')
  rec=$(kubectl get deploy recommendationservice -n default -o jsonpath='{.status.readyReplicas}')
  cat=$(kubectl get deploy productcatalogservice -n default -o jsonpath='{.status.readyReplicas}')
  if [ "$fe" = "4" ] && [ "$co" = "4" ] && [ "$rec" = "3" ] && [ "$cat" = "1" ] && [ "$pending" = "0" ]; then
    echo PIN_READY
    exit 0
  fi
  sleep 10
done
echo PIN_NOT_READY
kubectl get pods -n default --field-selector=status.phase=Pending -o wide
exit 1
