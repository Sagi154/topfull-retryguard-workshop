# Workshop experiments

Language for how this lab runs TopFull, RetryGuard, and Online Boutique. Implementation details live in the migration spec and the guides, not here.

## Language

### Trees and recipes

**Ron's setup**:
The experiment recipe Ron Nezer actually used: cluster manifests, Detector CPU beliefs, Boutique Deployment resources, replica/HPA shape, and loadgen mix. The inherited VMs are not this; they are only the machines.
_Avoid_: copied environment, his cluster, working TopFull environment (when those mean the VMs)

**Workshop tree**:
The TopFull checkout the runner drives (`idozacharia`'s clone). Canonical after the migration: Ron's *values* are ported here; the runner does not point at Ron's home directory.
_Avoid_: his tree, `/home/user/TopFull`, swapping trees

**KAIST upstream**:
The paper scripts at git commit `0c7af21`, before either Ron's or the workshop's local patches.
_Avoid_: stock TopFull (ambiguous between paper quotas and paper images)

**Experiment base**:
The configuration later scenarios are deviations from. After the migration, that base is Ron's setup, not the paper CPU table or 1-replica Boutique.
_Avoid_: default, current cluster, live path (those mix infra leftover with recipe)

### Capacity beliefs

**CPU source of truth**:
The millicores a service is actually allowed to use on the cluster (the live Deployment limit). The Detector's per-service CPU field is a copy of this, not an independent table.
_Avoid_: Detector table, paper CPU table, ResourceQuota (as if any of those were the real limit)

**Detector CPU table**:
The Detector's hardcoded per-service millicores. It is supposed to match the CPU source of truth. On Ron's disk it does not; that mismatch is drift, not a second convention.
_Avoid_: quota overlay, paper quotas (when you mean this field)

**Quota-sync**:
Keeping the Detector CPU table equal to the live Kubernetes limits on every run, not only when a scenario deliberately squeezes one service.
_Avoid_: S3/S4 overlay, `cpu_limit_fraction` (those are scenario knobs, not the sync itself)

### Regimes

**Paper-config regime**:
The 1-replica, paper-quota setup used for `campaign_48/` and the frozen-capacity calibration. Historical once the migration lands.
_Avoid_: baseline, current results (ambiguous with a future Ron-base campaign)

**Ron-config regime**:
The post-migration setup: Ron's setup as experiment base, workshop instrumentation on top, numbers fitted to this project's worker. The next campaign lives here.
_Avoid_: his exact cluster (we cannot grow to his replica/CPU footprint)

**Provisional numbers**:
The millicores and frontend replica ceiling in the migration spec, taken from Ron's January Boutique YAML and trimmed to fit this node, until Ron confirms what was live when TopFull engaged.
_Avoid_: final CPU table, calibrated limits
