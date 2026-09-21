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

### Loadgen

**Loadgen shape**:
How Locust tags are grouped into swarms: one independent single-tag swarm per tag (no `@task` weight ever arbitrates between tags) versus a merged swarm where several tags share one pool and weights split it. Ron's `frontend.sh` uses the independent shape; his `online_boutique_create.sh` merges the cart family into one weighted swarm. We adopt the independent shape.
_Avoid_: launcher script, split-cart (both conflate the shape decision with one specific file or one specific tag family)

**Loadgen numbers**:
The actual per-tag user counts and spawn rate. Decided separately from shape. Not copied from either of Ron's scripts — deferred to a fresh calibration pass run under the Ron-config regime, together with the S1–S6 scenario methodology rework.
_Avoid_: sizing, load level (too vague to mean this specifically)

**Task-weight remix**:
Ron's edited `@task()` values in `locust_online_boutique.py` (postcheckout 500, getcart 100, postcart 1, emptycart 1, getproduct 100, vs. the paper's 50/30/15/15/150). Adopted for fidelity with his tree, but inert under our loadgen shape: no scenario ever merges tags into one swarm where a weight would matter.
_Avoid_: "the mix" (ambiguous with loadgen numbers)
