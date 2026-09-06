# Task 15 Report

**Status:** Complete.

**Commit:** `57733b5` — "docs: point AGENTS.md at mentor update doc; fix S5 gallery path" (AGENTS.md + MENTOR-UPDATE.md, single commit).

**Verification checklist:**
- Read MENTOR-UPDATE.md top to bottom: OK, sections 1–4 coherent, S5 numbers in toggle table consistent with interval-sweep chart discussion.
- Mermaid fence present (infra diagram, section 1): OK.
- No `august_38`, no conclusions/recommendations section, no `[Fill in]` leftovers: confirmed via grep — none found.
- Spot-checked 5 image paths (Online-Boutique-architecture.png, S1 total_goodput, S2 resource_memory, S4A getproduct_goodput, S6 s5_s6_rejection_rate_by_interval): all exist.
- Fixed dead `charts_gallery/S5_interval_tuning/` pointer → now reads "`charts_gallery/S6_forced_recovery/` (includes S5 interval-sensitivity overlays)"; confirmed only `S6_forced_recovery/` exists under `charts_gallery/`.
- AGENTS.md pointer added under the "Not done yet" block per brief Step 2.

**Concerns:** None.

**Report path:** `.superpowers/sdd/task-15-report.md`

---

## Final-review fix (2026-09-06): preserve elapsed-seconds index

**Bug:** `average_dataframes` called `reset_index(drop=True)`, so Envoy retries and CPU/memory charts plotted row number (0..N) labeled "Elapsed seconds". ~5s polls made real time ~5× larger. MENTOR-UPDATE.md S2/S3 bullets that cited CPU/retries timings against Locust toggle seconds were therefore wrong.

**Fix:** Returned DataFrame index is now the pointwise mean of the truncated input indexes. Common-columns + shortest-length averaging for values is unchanged.

**Commits:**
- `92cb8e2` — `fix: preserve elapsed-seconds index in average_dataframes`
- (this follow-up) — `fix: regenerate mentor charts and correct timing observations`

**Tests:**
```
python experiments/test_mentor_charts_data.py
............
Ran 12 tests in 0.045s
OK

python experiments/test_mentor_charts.py
....
Ran 4 tests in 4.126s
OK
```

**Chart regen:** `python experiments/mentor_charts.py` completed successfully. Envoy/CPU/memory x-axes now span ~650–680s (S2/S3) instead of ~125 row counts.

**Doc:** Rewrote S2 and S3 CPU/retries observation bullets from the regenerated PNGs plus averaged peak times. Dropped the S3 claim that frontend retries went to 0 after the first `ON→OFF` at ~60s (last spike is ~353s). S6 CPU is shown but its bullets do not correlate collector seconds with Locust toggle times; left unchanged.

**Concerns:** Envoy/CPU elapsed seconds are relative to each collector file's earliest timestamp, not RetryGuard/Locust t0, and `plot_multi_line` does not overlay toggle markers. Treat CPU/retries vs toggle-second comparisons as approximate.
