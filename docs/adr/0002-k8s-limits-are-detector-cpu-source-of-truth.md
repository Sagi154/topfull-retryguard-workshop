# Live Kubernetes CPU limits are the Detector's source of truth

Ron's Detector CPU table and his Boutique YAML disagree on four services (checkout 4500m vs 800m is the worst). KAIST's own comment says the Detector field should match the YAML. We will not reproduce that split: the **CPU source of truth** is the live Deployment limit, and **quota-sync** runs on every experiment so the Detector cannot drift.

**Status:** accepted.

**Considered options:** freeze Ron's Detector table as written (mismatch included); correct the Detector table once to match the YAML, as a one-time static rewrite with no ongoing sync; sync only during S3/S4 constraints (today's overlay).

**Consequences:** scenario "squeeze one backend" knobs must change the live limit and let sync follow; they must not write a Detector-only number. Numeric millicores remain **provisional numbers** until Ron confirms the YAML.

Detail: [2026-09-20-ron-nezer-base-migration-design.md](../superpowers/specs/2026-09-20-ron-nezer-base-migration-design.md) §2d, §5.
