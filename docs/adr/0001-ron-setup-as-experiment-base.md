# Ron's setup is the experiment base; port values into the workshop tree

We inherited Ron Nezer's VMs, not his experiment recipe, and ran a paper-quota 1-replica setup instead. The team decided the **experiment base** is **Ron's setup** (all four layers: cluster manifests, Detector/replica shape, Boutique resources, loadgen mix), implemented by porting his values into the **workshop tree** rather than pointing the runner at `/home/user/TopFull`.

**Status:** accepted (mechanism); loadgen-layer details still deferred.

**Considered options:** keep the paper-config regime; swap the runner onto Ron's clone; port selected knobs only (CPU + replicas, skip HPA and loadgen).

**Consequences:** `campaign_48/` and the frozen-capacity calibration become the **paper-config regime** (historical). A later campaign must be run under the **Ron-config regime**. Do not treat "we copied his VMs" as "we ran his setup."

Detail: [2026-09-20-ron-nezer-base-migration-design.md](../superpowers/specs/2026-09-20-ron-nezer-base-migration-design.md).
