# Fit Ron's footprint on the 16-vCPU worker: frontend HPA max 4, uniform CPU trim

A GCP quota increase is not available (32 vCPU already used). Ron's September-scale numbers do not fit `topfull-worker-1`. We keep his HPA *mechanism* but cap frontend at **4** replicas (`maxReplicas: 4`, not 20) and trim every service's CPU-per-replica by ~77% from the January YAML so full scale-out stays inside the node's app-container budget. Productcatalog HPA stays off until S4A is redesigned. Stock Boutique images stay; `ronnezer/*` (probes stripped) do not.

**Status:** proposed (arithmetic is **provisional numbers** until Ron replies).

**Considered options:** grow VMs; keep 8 frontend replicas and haircut CPU harder; keep his CPU-per-replica and drop replica count only; adopt the 2600m namespace ResourceQuota as the cap.

**Consequences:** this is not a bit-for-bit replay of Ron's replica/CPU footprint. If he names different live millicores, redo the trim against the same budget method; do not grow the cluster without a quota change.

Detail: [2026-09-20-ron-nezer-base-migration-design.md](../superpowers/specs/2026-09-20-ron-nezer-base-migration-design.md) §3–§4.
