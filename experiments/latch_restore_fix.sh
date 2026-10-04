#!/bin/bash
# Re-apply only the Paper-C1 pin pieces that drift: the two HPAs and the sidecar request.
# Does not touch CPU limits (latch_hold_pre.ps1 -Treatment control restores checkout and recommendations).
# Run on topfull-master:  ssh topfull-master bash -s < experiments/latch_restore_fix.sh
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":4,"maxReplicas":4}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":1}}'
for dep in $(kubectl get deploy -n default -o jsonpath='{.items[*].metadata.name}'); do
  kubectl patch deployment "$dep" -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"100m"}}}}}'
  kubectl patch deployment "$dep" -n default --type json -p '[{"op":"remove","path":"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit"}]' 2>/dev/null || true
done
echo "restore fix applied"
