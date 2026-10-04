echo "### pods"
kubectl get pods -n default -o wide
echo "### nodes"
kubectl get nodes -o wide
echo "### hpa"
kubectl get hpa -n default
echo "### sidecar annotations"
kubectl get deploy -n default -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.metadata.annotations}{"\n"}{end}'
echo "### worker allocated resources"
kubectl describe node topfull-worker1 | grep -A8 'Allocated resources'
