# Adopt Ron's loadgen shape, not either of his launcher scripts' literal numbers

Ron's disk has two different loadgen launcher families — a merged-`$CART` script (`online_boutique_create.sh`) and a split-swarm script (`frontend.sh`) — and `.bash_history` shows him actively tuning both, interleaved with raw ad-hoc capacity probes, right up to the end of the visible history. Neither is a settled "final" recipe the way, e.g., a single Detector CPU table would be. We adopt the **shape** both scripts partially agree on (frontend.sh fully, create.sh for 4 of 5 tags) — one independent Locust swarm per tag, so `@task()` weights never arbitrate between tags — rather than freezing either script's numbers as ground truth.

**Status:** accepted.

**Considered options:** freeze `frontend.sh`'s literal numbers (most-exercised script) as the recipe; freeze `create.sh`'s literal numbers instead; block on asking Ron which was final before deciding anything.

**Consequences:** loadgen *numbers* (user counts, the `RATE` value) are not ported from Ron — they still need a fresh calibration pass under the Ron-config regime, bundled with the S1–S6 scenario methodology rework. `experiments/loadgen/online_boutique_create_v2.sh` is the implementation vehicle for the independent-swarm shape. Its spawn math matches Ron's (2026-09-22): Locust `-r` = `count / RATE`, awk float, not `RATE` as users/sec. The `@task()` weight remix is ported for fidelity but is inert under this shape — no scenario merges tags into one swarm.
Detail: [2026-09-21-loadgen-shape-ron-migration-design.md](../superpowers/specs/2026-09-21-loadgen-shape-ron-migration-design.md).
