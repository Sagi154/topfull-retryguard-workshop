# S2 Checkout-Latch Probe v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run twenty both-off S2 holds (runs 128–147) on the disk-copy VMs from the run 89 mix on Paper-C1: seven new lever combinations twice each (checkout 2 replicas + postcheckout 120, with and without a 10 s ramp; checkout 1000 m + postcheckout 120, with and without a 10 s ramp; ramp alone; recommendations 1000 m, with and without a 10 s ramp) plus six untouched controls, with CPU steal captured on all three VMs during every hold. Then score every hold, write the results guide and the all-services ABC guide, update `AGENTS.md`, commit and push everything, and stop the three VMs after restoring the cluster to Paper-C1.

**Architecture:** The earlier probe's helper `experiments/s2_latch_probe.py` and scripts `experiments/latch_hold_pre.ps1` / `experiments/latch_hold_run.ps1` are extended, not replaced: four new treatments, a seeded `hold_order()`, a worker-CPU-request fit check and a safer `prep` (scale checkout down, patch, roll both Deployments so every hold starts with equally young pods, scale up), pod-age and steal gates. A new module `experiments/steal_stat.py` parses `/proc/stat` samples into a steal percentage; a new script `experiments/node_steal.sh` takes a 10 s snapshot and runs a 5 s background sampler on each VM. A new `experiments/s2_probe_tables.py` builds the all-services tables for the ABC guide. Holds run in two shuffled blocks of ten (randomized block design) with a control at the very first and very last slot so drift over the day is visible.

**Tech Stack:** Python 3 + `unittest`, PowerShell, bash over `ssh` (aliases only), `kubectl` on `topfull-master`, `gcloud compute` on project `project-76deda76-55f1-42d2-abb`, `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/s2_both_off_canon.py`, `experiments/s2_both_off_abc.py`.

## Global Constraints

- Project is `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. Never start or stop anything in `networks-workshop`; pass `--project` to every `gcloud` call. SSH aliases only: `topfull-master`, `topfull-worker-1`, `topfull-load`; never an IP. SSH user is `idozacharia`. (`kubectl` names the worker node `topfull-worker1`, no second hyphen; that is the node name, not the SSH alias.)
- **Base (every hold unless its arm says otherwise):** counts getproduct / postcheckout / getcart / postcart / emptycart = **275 / 90 / 100 / 90 / 5** (run 89 mix). Paper-C1, per-pod millicores with request equal to limit: frontend 1150 x 4 (HPA pinned min 4 / max 4), checkoutservice 800 x 1, recommendationservice 1150 x 1, productcatalogservice 800, cartservice 800, currencyservice 770, shippingservice 770, adservice 1150, paymentservice 155, emailservice 120, redis-cart 540 (container `redis`). Every other Deployment has 1 replica. Catalog HPA min 1 / max 1. Sidecar annotation `sidecar.istio.io/proxyCPU=100m`, `proxyCPULimit` absent.
- Every hold is 600 s, `spawn_rate` 50 (10 for the `*_spawn10` arms), `topfull_rl.enabled: false`, `retryguard.enabled: false`, Istio `attempts: 3`, `per_try_timeout_ms: 500`, script `online_boutique_create_v2.sh`, `paper_cpu_reconcile: false`.
- **One arm per hold; no hold combines arms.** Seven arms, two holds each, six controls, fixed in the order table below. Do not reorder or drop a hold except under the failure rules.
- **Slots are run128 to run147.** Run1–run127 are taken or reserved: run116 failed its gate and run127 was never run, and both numbers stay unused so the earlier guides stay true. Do not overwrite any folder under `campaign_48/`, `experiments/results/new vms/`, or `experiments/results/copy verification/`. Appended relaunch slots (failure rules) are run148, run149, and so on.
- Local destination: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run<N>/`. `pull_results.py` first writes under `campaign_48/S2_sustained_overload/`; the run script moves the folder. Nothing from this series stays under `campaign_48/`.
- The helper writes each hold's generated config to `experiments/configs/scenario_2_latch_probe.yaml`. Do not edit `scenario_2_baseline_no_topfull.yaml` until the bookkeeping task.
- **Fresh-pod rule (new in v2).** `prep` rolls checkoutservice and recommendationservice before every hold, so every hold, controls included, starts with checkout and recommendations pods about 6–10 minutes old at t=0 (the gate fails any hold with such a pod older than 1200 s). The first probe left controls on pods from 6 minutes to 5 hours old, a confound. This also means v2 holds are not directly comparable to runs 94–107, which ran on old pods.
- **Cluster state is set by `prep`, never by the runner.** `prep` sets checkout CPU, recommendations CPU, and checkout replicas before the cool-off, so the runner's CPU patch is `already at …; skipping patch`. If a runner log shows an applied patch, note it in the results guide.
- **Schedulability.** The worker has 16 vCPU (16000 m allocatable). Base CPU requests, sidecars included, are 14305 m; the ceiling is 15600 m. `latch_hold_pre.ps1` runs `s2_latch_probe.py fit <treatment>` before touching the cluster and the `prep` script exits 3 if the worker's live requests pass the ceiling. Never combine checkout 1000 m with 2 replicas (2 x 1100 m puts requests at 15405 m plus the rollout surge; this combination went Pending on 2026-10-03). A Pending pod after `prep`: stop and report `kubectl describe pod`. Do not lower the sidecar request and do not unpin frontend.
- Cool-off is 360 s after `prep` finishes and before launch, for every hold. Do not call `Start-Sleep`. Call AwaitShell with no `shell_id` and `block_until_ms: 360000`.
- **PowerShell pipes add CRLF to remote bash scripts.** Every remote script goes through `cmd /c "… | ssh … bash -s"` or `cmd /c "ssh … bash -s < file"` (done inside the `.ps1` scripts). Never pipe a script to ssh directly from PowerShell. `experiments/node_steal.sh` and `experiments/latch_restore_check.sh` must be LF; the Write tool saves CRLF on Windows, so each creation step normalizes the file and a unit test checks it.
- `duplicate session: envoyretry` in a hold's output: `ssh -o BatchMode=yes topfull-master "tmux kill-session -t envoyretry"`, then rerun that hold's run script once. Any other death before Locust: keep whatever folder exists, do not relaunch the slot, go to the failure rules.
- **Per-hold gates (all must pass; `latch_hold_run.ps1` prints PASS/FAIL):** Locust `total.csv` rows >= 540; mesh span (`service_inbound.csv` first to last timestamp) 480–900 s, normally about 690 s; `gap2_pct` <= 10; all collector files present; replica pin counts equal to the arm's (frontend 4, checkout 1 or 2, every other service 1) on the modal `resource_usage.csv` sample; checkout and recommendations pods younger than 1200 s in `state/t0.txt`; nine steal files present in `state/` (`steal_t0_*`, `steal_end_*`, `steal_series_*` for master, worker, load) and at least 100 series samples inside the hold window on each node.
- **Failure rules.** A *sampling-type* failure (rows, span, gap2, missing collector file, STATE pod-age, STEAL files) keeps the folder, is never relaunched in the same slot, is committed with the message `data: S2 latch probe v2 runN FAILED gate`, gets a blank row in the guide, and the same treatment is appended at the end as the next unused slot (run148, then run149; at most two appended holds, then stop and report). Two STEAL failures in a row mean the capture is broken: stop the series, fix it, and report. A *replica-mode* failure (the message contains `replica mode`: the arm did not apply) stops the series; go to Task 28. A Pending pod stops the series. Never commit a failed hold as if it passed.
- **YAML run_number rule.** The generated `scenario_2_latch_probe.yaml` carries each hold's slot as `run_number` and `log_folder`. `scenario_2_baseline_no_topfull.yaml` stays at run128 (unused) until Task 30, which bumps it to one past the highest slot used (148, or higher if relaunch slots were used). A run number is never reused, including for a failed hold.
- Do not call `reconcile_paper_cpu_limits`, do not restore the frontend HPA, do not restore paper CPU during the series. Task 28 returns checkout and recommendations to the Paper-C1 base and leaves frontend HPA 4/4 and catalog HPA 1/1 as the earlier sessions left them.
- Do not commit `.superpowers/`, private keys, `known_hosts`, or `~/.ssh/config`. Commit each hold before the next cool-off. Push once, in Task 31. Do not stop the VMs before Task 32.
- **Reading the results (honesty rule, unchanged).** A hold is *sticky* when `s2_latch_probe.py` scores it sticky (checkout streak >= 400, recommendations streak 0); *released* when frontend->recommendations retries >= 70000 (not sticky); *other* otherwise. A *blend* is recommendations and checkout both at streak >= 10 and overloaded >= 10 ticks, plus email or payment overloaded >= 10 ticks. Verdict per arm: **moved** (no hold sticky), **no effect seen** (every hold sticky), **mixed** (anything else); add **latch avoided** to moved when checkout never held a streak of 30 in either hold. Two holds per arm is a screen, not a proof: if an arm did nothing, two non-sticky holds in a row still happen about a quarter to a third of the time at the observed background rate. Only a moved arm earns a 3-replay follow-up. The six controls are reported as their own rate beside the earlier holds of this mix on the copy (runs 94–97 and 99–101: 3 blends, 4 sticky) and the two scored first-probe controls (runs 111 and 121: both released blends).

## Hold order (seed 20261004)

Produced by `python experiments/s2_latch_probe.py order 20261004 128` (Task 3 Step 6 prints it and compares). `hold_order()` builds block A as a control first plus the seven arms and two controls shuffled, block B as the seven arms and two controls shuffled plus a control last, and reshuffles until no two adjacent holds (across the A/B boundary too) share a lever family (control, checkout-2-replicas, checkout-1000 m, recommendations-1000 m, plain ramp). Every arm therefore appears once in each block, so its second hold is always in the second half.

| Slot | Block | Treatment | What changes from base | Projected worker CPU requests |
|---|---|---|---|---|
| 128 | A | `control` | nothing (plain base, `spawn_rate` 50) | 14305 m |
| 129 | A | `spawn10` | `spawn_rate` 50 -> 10 | 14305 m |
| 130 | A | `control` | nothing (plain base, `spawn_rate` 50) | 14305 m |
| 131 | A | `ck_cpu1000_pc120` | checkoutservice 1000 m x 1, postcheckout 120 | 14505 m |
| 132 | A | `recs_cpu1000_spawn10` | recommendationservice 1000 m, `spawn_rate` 10 | 14155 m |
| 133 | A | `ck_rep2_pc120` | checkoutservice 800 m x 2 replicas, postcheckout 90 -> 120 | 15205 m |
| 134 | A | `recs_cpu1000` | recommendationservice 1150 -> 1000 m | 14155 m |
| 135 | A | `control` | nothing (plain base, `spawn_rate` 50) | 14305 m |
| 136 | A | `ck_rep2_pc120_spawn10` | checkoutservice 800 m x 2 replicas, postcheckout 120, `spawn_rate` 10 | 15205 m |
| 137 | A | `ck_cpu1000_pc120_spawn10` | checkoutservice 1000 m x 1, postcheckout 120, `spawn_rate` 10 | 14505 m |
| 138 | B | `spawn10` | `spawn_rate` 50 -> 10 | 14305 m |
| 139 | B | `control` | nothing (plain base, `spawn_rate` 50) | 14305 m |
| 140 | B | `recs_cpu1000_spawn10` | recommendationservice 1000 m, `spawn_rate` 10 | 14155 m |
| 141 | B | `ck_rep2_pc120_spawn10` | checkoutservice 800 m x 2 replicas, postcheckout 120, `spawn_rate` 10 | 15205 m |
| 142 | B | `ck_cpu1000_pc120` | checkoutservice 1000 m x 1, postcheckout 120 | 14505 m |
| 143 | B | `control` | nothing (plain base, `spawn_rate` 50) | 14305 m |
| 144 | B | `recs_cpu1000` | recommendationservice 1150 -> 1000 m | 14155 m |
| 145 | B | `ck_cpu1000_pc120_spawn10` | checkoutservice 1000 m x 1, postcheckout 120, `spawn_rate` 10 | 14505 m |
| 146 | B | `ck_rep2_pc120` | checkoutservice 800 m x 2 replicas, postcheckout 90 -> 120 | 15205 m |
| 147 | B | `control` | nothing (plain base, `spawn_rate` 50) | 14305 m |

**Why six controls.** Twenty holds split into two blocks of ten leave three controls per block, which keeps every arm to one hold per block. Controls sit at slot 128 (very first), 130, 135, 139, 143, and 147 (very last). The first probe's last three holds (runs 124–126) were all sticky and two of them were also second holds of their arm, so a drift late in the day and a real arm effect could not be told apart; with a control at both ends, a first control that blends and a last control that latches is visible as drift. Six controls also give the background latch rate its own estimate (a 50% rate gives a wide interval at n = 6, which is why the earlier 7 holds and the two scored first-probe controls are reported beside it, not pooled). Fewer than four controls would leave the two bookends and one middle point, too little to see a trend; more than six costs a whole extra 30-minute hold per control without changing the arm count.

**Why the prep rolls every hold.** In the first probe an arm that changed a CPU limit or replica count got fresh checkout/recommendations pods while the controls and unchanged-limit arms kept pods hours old (run 121: 3h43m and 5h8m; run 123: 12 hours). Pod age is a candidate cause of the mode, so v2 removes it as a difference between arms: every hold rolls both Deployments in `prep` and then waits the same 360 s. The `restart` arm of the first probe (mixed) is therefore dropped as a separate arm.

**Wall clock.** Per hold: `prep` about 4 min (scale down, patch, roll, scale up, 20 s settle), cool-off 6 min, t=0 snapshots about 1.3 min (cluster snapshot plus three 10 s steal snapshots), runner about 17 min (600 s hold plus ramp, collector start/stop and teardown), pull about 1 min, end snapshots about 1.3 min, commit under 1 min: about **31 minutes**. Twenty holds is about **10.3 hours**; Task 6 (start and preflight) about 25 minutes; Task 28 onward (restore, tables, two guides, push, stop) about 1.5 hours. Plan for **about 12 hours** end to end, and relaunch slots add 31 minutes each.

## File map

| File | Role |
|---|---|
| `experiments/steal_stat.py` | New. Parses `/proc/stat` samples into steal %, reads snapshots and sampler series, scores a run folder; CLI prints one line or a markdown row per run. |
| `experiments/test_steal_stat.py` | New. Unit tests, including that `node_steal.sh` has no CR. |
| `experiments/node_steal.sh` | New. LF-only bash for one VM: `snap` (10 s steal reading), `start <file>` / `stop <file>` (5 s sampler). |
| `experiments/s2_latch_probe.py` | Modify (full replacement). Adds four treatments, `projected_requests_mc`, safer `prep`, `hold_order`, `family`, `pod_ages`, steal and pod-age gates, rows >= 540, CLI `fit`, `order`, `steal`. Classifier already uses 70000. |
| `experiments/test_s2_latch_probe.py` | Modify. Appends boundary tests (Task 1) and v2 tests (Task 3). |
| `experiments/latch_hold_pre.ps1` | Modify (full replacement). Adds the `fit` gate before the cluster is touched. |
| `experiments/latch_hold_run.ps1` | Modify (full replacement). Adds steal snapshots at t=0 and end, starts and stops the 5 s samplers, fetches the series. |
| `experiments/latch_restore_check.sh` | New. LF bash gate that Paper-C1 is restored. |
| `experiments/latch_restore_fix.sh` | New. LF bash that re-pins both HPAs and the sidecar request. |
| `experiments/s2_probe_tables.py`, `experiments/test_s2_probe_tables.py` | New. All-services tables for the ABC guide, plus a steal table. |
| `.superpowers/latch/scorecard_v2.py` | New, not committed. Per-hold, per-arm, control-drift, blend-count, and steal-by-mode readout. |
| `docs/superpowers/plans/2026-10-03-s2-latch-probe-holds.md` | Modify (docs only, applied when this plan was written): classifier threshold 100000 -> 70000 and the run101 test. Committed in Task 1. |
| `experiments/configs/scenario_2_latch_probe.yaml` | Generated per hold; committed with that hold. |
| `experiments/results/new vms/baseline_no_topfull_sustained_overload_run128` … `run147` (plus any relaunch slots) | Created by pull plus move. One data commit each, with a `state/` subfolder (`t0.txt`, `end.txt`, nine steal files). |
| `Guides and Info/2026-10-04-s2-latch-probe-v2-results.md` | New. Per-hold scorecard, per-arm verdicts, control drift, steal vs mode, blend counts, replays, handoff. |
| `Guides and Info/2026-10-04-s2-latch-probe-v2-abc.md` | New. All-services (a)/(b)/(c) and the other tables, mirroring `2026-09-27-s2-cpu-variant-handoff.md` / `2026-10-04-s2-latch-probe-abc.md`. |
| `AGENTS.md`, `experiments/results/README.md`, `experiments/configs/scenario_2_baseline_no_topfull.yaml` | Task 30 bookkeeping (next free both-off slot). |

---

### Task 1: Classifier retry threshold 70000 (docs edit already applied; lock it with tests)

**Files:**
- Modify (already edited when this plan was written): `docs/superpowers/plans/2026-10-03-s2-latch-probe-holds.md` (its `classify` code now reads `ret >= 70000` and its tests include the run101-like case)
- Verify: `experiments/s2_latch_probe.py` (`classify`)
- Modify: `experiments/test_s2_latch_probe.py` (append a test class before the `if __name__` block)

**Interfaces:**
- Consumes: `s2_latch_probe.classify(o: dict) -> str` where `o = {"svc": {...}, "edges": {("frontend", "recommendationservice"): retries}}`.
- Produces: tests that fix the bar at 70000: 76,303 (run101) is `released`, 69,999 is `other`, 70,000 is `released`. Task 3 replaces `s2_latch_probe.py` in full and keeps `classify` identical.

- [ ] **Step 1: Record the starting commit**

```powershell
New-Item -ItemType Directory -Force ".superpowers/latch" | Out-Null
git rev-parse HEAD | Out-File -Encoding ascii ".superpowers/latch/base_sha.txt"
git status --short
```

Expected: `git status --short` lists the plan files and the guides from the earlier session (some staged). Read it once; Task 31 decides what to commit.

- [ ] **Step 2: Confirm the old plan and the live code both say 70000**

```powershell
rg -n "ret >= " docs/superpowers/plans/2026-10-03-s2-latch-probe-holds.md experiments/s2_latch_probe.py
rg -n "100000" docs/superpowers/plans/2026-10-03-s2-latch-probe-holds.md
```

Expected: the first command prints exactly two lines, both `if ret >= 70000:`. The second prints nothing. If either file still has `ret >= 100000`, change it to `ret >= 70000` and add the comment `# 70_000 sits under run 101's 76,303 frontend>recommendations retries and` / `# above the 50,000 count that stays "other".` above it.

- [ ] **Step 3: Write the boundary tests**

Append to `experiments/test_s2_latch_probe.py`, above the `if __name__ == "__main__":` line:

```python
class TestClassifyBoundary(unittest.TestCase):
    def o(self, ck, rc, ret):
        return {"svc": {"checkoutservice": {"streak": ck, "ov": 0},
                        "recommendationservice": {"streak": rc, "ov": 0}},
                "edges": {("frontend", "recommendationservice"): ret}}

    def test_run101_like_76303_is_released(self):
        self.assertEqual(p.classify(self.o(375, 77, 76303)), "released")

    def test_bar_is_70000(self):
        self.assertEqual(p.classify(self.o(10, 10, 69999)), "other")
        self.assertEqual(p.classify(self.o(10, 10, 70000)), "released")

    def test_100000_is_no_longer_the_bar(self):
        self.assertEqual(p.classify(self.o(10, 10, 85000)), "released")
```

- [ ] **Step 4: Run the tests**

Run: `python experiments/test_s2_latch_probe.py -v`
Expected: all pass (the live code already uses 70000, so these tests lock it instead of failing first). To prove they bite, temporarily change `70000` to `100000` in `classify`, rerun, see `test_run101_like_76303_is_released` and `test_bar_is_70000` fail, then change it back and rerun to green.

- [ ] **Step 5: Commit**

```powershell
git add docs/superpowers/plans/2026-10-03-s2-latch-probe-holds.md experiments/test_s2_latch_probe.py
git commit -m "test: lock the latch classifier retry bar at 70000 (run101 is released)"
```

---

### Task 2: CPU steal parser and node capture script (TDD)

**Files:**
- Create: `experiments/steal_stat.py`
- Create: `experiments/test_steal_stat.py`
- Create: `experiments/node_steal.sh` (LF only)

**Interfaces:**
- Consumes: Linux `/proc/stat` first line (`cpu user nice system idle iowait irq softirq steal guest guest_nice`), optionally prefixed by an epoch.
- Produces (used by Tasks 3, 4, 5, 29): `parse_cpu_line(line) -> dict`, `steal_pct(a, b) -> float`, `parse_snapshot(text) -> (dict, dict)`, `read_series(path) -> list`, `window_stats(series, lo, hi) -> dict | None`, `hold_window(run_dir) -> (lo, hi)`, `score_run(run_dir) -> {"master"|"worker"|"load": {"hold_pct","max_interval_pct","samples","t0_pct","end_pct"}}`, `format_line(label, scored)`, `md_row(label, scored)`, `NODES`. Files the run script writes into each run folder's `state/`: `steal_t0_<node>.txt`, `steal_end_<node>.txt` (output of `node_steal.sh snap`), `steal_series_<node>.txt` (sampler lines `<epoch> cpu …`).

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_steal_stat.py`:

```python
"""Unit tests for steal_stat. No network, no result folders."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import steal_stat as s

A = "cpu  1000 0 500 8000 100 0 50 100 0 0"
B = "cpu  1400 0 700 8600 100 0 50 250 0 0"


class TestParse(unittest.TestCase):
    def test_parse_with_leading_epoch(self):
        d = s.parse_cpu_line("1759570000 " + A)
        self.assertEqual(d["epoch"], 1759570000.0)
        self.assertEqual((d["user"], d["idle"], d["steal"]), (1000, 8000, 100))

    def test_parse_without_epoch(self):
        self.assertIsNone(s.parse_cpu_line(A)["epoch"])

    def test_short_line_defaults_missing_fields_to_zero(self):
        d = s.parse_cpu_line("cpu  10 0 5 80 1 0 0")  # 7 fields: pre-2.6.11 kernels have no steal
        self.assertEqual(d["steal"], 0)

    def test_not_a_cpu_line_raises(self):
        with self.assertRaises(ValueError):
            s.parse_cpu_line("cpu0 1 2 3")
        with self.assertRaises(ValueError):
            s.parse_cpu_line("intr 12345")


class TestStealPct(unittest.TestCase):
    def test_known_value(self):
        # total went 9750 -> 11100 (+1350); steal went 100 -> 250 (+150): 11.111%
        self.assertAlmostEqual(s.steal_pct(s.parse_cpu_line(A), s.parse_cpu_line(B)), 11.1111, places=3)

    def test_zero_steal(self):
        a = s.parse_cpu_line("cpu  10 0 10 100 0 0 0 7")
        b = s.parse_cpu_line("cpu  20 0 20 200 0 0 0 7")
        self.assertEqual(s.steal_pct(a, b), 0.0)

    def test_guest_is_not_double_counted(self):
        a = s.parse_cpu_line("cpu  100 0 0 100 0 0 0 0 50 0")
        b = s.parse_cpu_line("cpu  200 0 0 200 0 0 0 10 100 0")
        # total delta = 100 + 100 + 10 = 210 (guest ignored); steal delta 10
        self.assertAlmostEqual(s.steal_pct(a, b), 100 * 10 / 210, places=4)

    def test_counter_reset_raises(self):
        with self.assertRaises(ValueError):
            s.steal_pct(s.parse_cpu_line(B), s.parse_cpu_line(A))


class TestSnapshot(unittest.TestCase):
    TEXT = ("### proc_stat_a\n1759570000 " + A + "\n### vmstat_10s\nprocs ---memory---\n"
            " 1  0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\n### mpstat\nmpstat unavailable\n"
            "### proc_stat_b\n1759570010 " + B + "\n")

    def test_parse_snapshot_returns_a_then_b(self):
        a, b = s.parse_snapshot(self.TEXT)
        self.assertEqual((a["epoch"], b["epoch"]), (1759570000.0, 1759570010.0))
        self.assertAlmostEqual(s.steal_pct(a, b), 11.1111, places=3)

    def test_missing_section_raises(self):
        with self.assertRaises(ValueError):
            s.parse_snapshot("### proc_stat_a\n1759570000 " + A + "\n")


def _series_lines(start_epoch, n, step, steal_per_step, busy_per_step):
    lines, user, steal, idle = [], 0, 0, 0
    for i in range(n):
        lines.append(f"{start_epoch + i * step} cpu  {user} 0 0 {idle} 0 0 0 {steal} 0 0")
        user += busy_per_step
        steal += steal_per_step
        idle += 100 - busy_per_step - steal_per_step
    return lines


class TestWindowAndScore(unittest.TestCase):
    def test_window_stats_uses_only_samples_inside_window(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "series.txt"
            # 11 samples, 5 s apart, 5% steal each step (100 jiffies per step)
            p.write_text("\n".join(_series_lines(1000, 11, 5, 5, 45)) + "\ngarbage line\n")
            ser = s.read_series(p)
            self.assertEqual(len(ser), 11)
            w = s.window_stats(ser, 1010, 1040)
            self.assertEqual(w["samples"], 7)
            self.assertAlmostEqual(w["pct"], 5.0, places=6)
            self.assertAlmostEqual(w["max_interval_pct"], 5.0, places=6)
            self.assertIsNone(s.window_stats(ser, 5000, 6000))

    def test_score_run_reads_all_three_nodes(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            lo = s._utc("2026-10-04T10:00:00Z")
            (run / "service_inbound.csv").write_text(
                "timestamp,service,total\n2026-10-04T10:00:00Z,frontend,1\n"
                "2026-10-04T10:01:00Z,frontend,2\n", encoding="utf-8")
            st = run / "state"
            st.mkdir()
            for node, steal_step in (("master", 0), ("worker", 10), ("load", 1)):
                (st / f"steal_series_{node}.txt").write_text(
                    "\n".join(_series_lines(int(lo) - 20, 15, 5, steal_step, 50 - steal_step)),
                    encoding="utf-8")
                (st / f"steal_t0_{node}.txt").write_text(
                    "### proc_stat_a\n1759570000 " + A + "\n### proc_stat_b\n1759570010 " + B + "\n",
                    encoding="utf-8-sig")
            r = s.score_run(run)
            self.assertAlmostEqual(r["master"]["hold_pct"], 0.0)
            self.assertAlmostEqual(r["worker"]["hold_pct"], 10.0, places=6)
            self.assertAlmostEqual(r["load"]["hold_pct"], 1.0, places=6)
            self.assertAlmostEqual(r["worker"]["t0_pct"], 11.1111, places=3)
            self.assertIsNone(r["worker"]["end_pct"])
            self.assertIn("worker 10.00%", s.format_line("run128", r))
            self.assertTrue(s.md_row("run128", r).startswith("| run128 |"))


class TestNodeStealScript(unittest.TestCase):
    def test_script_has_no_carriage_returns(self):
        # A CR in a script piped to "ssh bash -s" breaks it (see Global Constraints).
        data = (Path(__file__).resolve().parent / "node_steal.sh").read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertIn(b"### proc_stat_a", data)
        self.assertIn(b"### proc_stat_b", data)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python experiments/test_steal_stat.py -v`
Expected: `ModuleNotFoundError: No module named 'steal_stat'`.

- [ ] **Step 3: Implement the parser**

Create `experiments/steal_stat.py`:

```python
"""CPU steal from /proc/stat samples (snapshots and background sampler series).

CLI:
  python experiments/steal_stat.py <run_dir> [<run_dir> ...]        # one line per run
  python experiments/steal_stat.py --md <run_dir> [<run_dir> ...]   # markdown table rows
Files read from <run_dir>/state/: steal_t0_<node>.txt, steal_end_<node>.txt,
steal_series_<node>.txt for node in master, worker, load. The hold window is the first
and last timestamp of <run_dir>/service_inbound.csv (UTC).
"""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal",
          "guest", "guest_nice"]
NODES = ("master", "worker", "load")


def parse_cpu_line(line: str) -> dict:
    """Parse '[epoch] cpu  user nice ...' from /proc/stat. Missing trailing fields are 0."""
    parts = line.split()
    if "cpu" not in parts[:2]:
        raise ValueError(f"not an aggregate cpu line: {line!r}")
    i = parts.index("cpu")
    epoch = float(parts[0]) if i == 1 else None
    vals = [int(x) for x in parts[i + 1:]]
    vals += [0] * (len(FIELDS) - len(vals))
    out = dict(zip(FIELDS, vals[:len(FIELDS)]))
    out["epoch"] = epoch
    return out


def total_jiffies(s: dict) -> int:
    """user..steal. guest and guest_nice are already counted inside user and nice."""
    return sum(s[k] for k in FIELDS[:8])


def steal_pct(a: dict, b: dict) -> float:
    """Percent of CPU time stolen between two samples (a earlier than b)."""
    dt = total_jiffies(b) - total_jiffies(a)
    ds = b["steal"] - a["steal"]
    if dt <= 0 or ds < 0:
        raise ValueError("counters did not advance (reboot or reordered samples)")
    return 100.0 * ds / dt


def parse_snapshot(text: str):
    """node_steal.sh snap output -> (sample_a, sample_b) from the proc_stat_a / proc_stat_b sections."""
    out, key = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("### "):
            key = line[4:]
            continue
        if key in ("proc_stat_a", "proc_stat_b") and line and key not in out:
            out[key] = parse_cpu_line(line)
    if "proc_stat_a" not in out or "proc_stat_b" not in out:
        raise ValueError("snapshot lacks proc_stat_a / proc_stat_b")
    return out["proc_stat_a"], out["proc_stat_b"]


def read_series(path) -> list:
    """Sampler file: one '<epoch> cpu ...' line per sample. Bad lines are skipped."""
    out = []
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    for line in text.splitlines():
        try:
            s = parse_cpu_line(line)
        except ValueError:
            continue
        if s["epoch"] is not None:
            out.append(s)
    return out


def window_stats(series: list, lo: float, hi: float):
    """Steal % over [lo, hi] (first to last sample inside it), plus the worst consecutive-sample %."""
    w = [s for s in series if lo <= s["epoch"] <= hi]
    if len(w) < 2:
        return None
    worst = 0.0
    for a, b in zip(w, w[1:]):
        try:
            worst = max(worst, steal_pct(a, b))
        except ValueError:
            pass
    return {"pct": steal_pct(w[0], w[-1]), "max_interval_pct": worst, "samples": len(w)}


def _utc(ts: str) -> float:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def hold_window(run_dir) -> tuple:
    with open(Path(run_dir) / "service_inbound.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return _utc(rows[0]["timestamp"]), _utc(rows[-1]["timestamp"])


def score_run(run_dir) -> dict:
    run_dir = Path(run_dir)
    state = run_dir / "state"
    lo, hi = hold_window(run_dir)
    out = {}
    for node in NODES:
        r = {"hold_pct": None, "max_interval_pct": None, "samples": 0,
             "t0_pct": None, "end_pct": None}
        series = state / f"steal_series_{node}.txt"
        if series.exists():
            try:
                w = window_stats(read_series(series), lo, hi)
            except ValueError:
                w = None
            if w:
                r.update(hold_pct=w["pct"], max_interval_pct=w["max_interval_pct"],
                         samples=w["samples"])
        for tag in ("t0", "end"):
            snap = state / f"steal_{tag}_{node}.txt"
            if snap.exists():
                try:
                    a, b = parse_snapshot(snap.read_text(encoding="utf-8-sig", errors="replace"))
                    r[f"{tag}_pct"] = steal_pct(a, b)
                except ValueError:
                    pass
        out[node] = r
    return out


def _f(x):
    return "n/a" if x is None else f"{x:.2f}"


def format_line(label: str, scored: dict) -> str:
    parts = [f"{n} {_f(scored[n]['hold_pct'])}% (max {_f(scored[n]['max_interval_pct'])}, "
             f"n={scored[n]['samples']})" for n in NODES]
    return f"{label} steal " + " | ".join(parts)


def md_row(label: str, scored: dict) -> str:
    cells = [f"{_f(scored[n]['hold_pct'])} / {_f(scored[n]['max_interval_pct'])}" for n in NODES]
    return f"| {label} | " + " | ".join(cells) + " |"


def main(argv):
    md = "--md" in argv
    dirs = [a for a in argv[1:] if a != "--md"]
    if not dirs:
        print(__doc__)
        return 2
    if md:
        print("| Run | master hold % / max | worker hold % / max | load hold % / max |")
        print("|---|---|---|---|")
    for d in dirs:
        label = Path(d).name.replace("baseline_no_topfull_sustained_overload_", "")
        scored = score_run(d)
        print(md_row(label, scored) if md else format_line(label, scored))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Create the node script and make it LF**

Create `experiments/node_steal.sh`:

```bash
#!/bin/bash
# CPU steal capture for one node. Sent over ssh as a script on stdin; the mode follows "--":
#   ssh <alias> bash -s -- snap                 < experiments/node_steal.sh
#   ssh <alias> bash -s -- start /tmp/file.txt  < experiments/node_steal.sh
#   ssh <alias> bash -s -- stop  /tmp/file.txt  < experiments/node_steal.sh
# snap  : /proc/stat cpu line, a 10 s vmstat (its "st" column is steal), a 1 s mpstat if
#         installed, then the /proc/stat cpu line again (so one snapshot is a 10 s steal reading).
# start : appends "<epoch> <cpu line>" every 5 s to the file until stopped.
# stop  : stops that sampler.
mode="$1"
cpu_line() { echo "$(date +%s) $(head -n 1 /proc/stat)"; }
case "$mode" in
  snap)
    echo "### proc_stat_a"
    cpu_line
    echo "### vmstat_10s"
    if command -v vmstat >/dev/null 2>&1; then vmstat 10 2; else echo "vmstat unavailable"; sleep 10; fi
    echo "### mpstat"
    if command -v mpstat >/dev/null 2>&1; then mpstat 1 1; else echo "mpstat unavailable"; fi
    echo "### proc_stat_b"
    cpu_line
    ;;
  start)
    out="$2"
    if [ -f "$out.pid" ]; then kill "$(cat "$out.pid")" 2>/dev/null || true; fi
    : > "$out"
    nohup bash -c 'while true; do echo "$(date +%s) $(head -n 1 /proc/stat)"; sleep 5; done' >> "$out" 2>/dev/null < /dev/null &
    echo $! > "$out.pid"
    echo "sampler started pid $(cat "$out.pid") -> $out"
    ;;
  stop)
    out="$2"
    if [ -f "$out.pid" ]; then kill "$(cat "$out.pid")" 2>/dev/null || true; rm -f "$out.pid"; fi
    echo "sampler stopped; $(wc -l < "$out") lines in $out"
    ;;
  *)
    echo "usage: snap | start <file> | stop <file>" >&2
    exit 2
    ;;
esac
```

The Write tool saves CRLF on Windows and a CR breaks `bash -s`. Normalize and check:

```powershell
python -c "p='experiments/node_steal.sh'; d=open(p,'rb').read().replace(b'\r\n',b'\n'); open(p,'wb').write(d)"
python -c "print(b'\r' in open('experiments/node_steal.sh','rb').read())"
```

Expected: `False`. Syntax check: `bash -n experiments/node_steal.sh` prints nothing and exits 0 (Git Bash or WSL; skip only if no bash exists locally, the Task 6 smoke test covers it on the VMs).

- [ ] **Step 5: Run to verify pass**

Run: `python experiments/test_steal_stat.py -v`
Expected: 13 tests, OK.

- [ ] **Step 6: Commit**

```powershell
git add experiments/steal_stat.py experiments/test_steal_stat.py experiments/node_steal.sh
git commit -m "feat: CPU steal parser and per-node capture script"
```

---

### Task 3: `s2_latch_probe.py` v2 (TDD): treatments, order, fit, safer prep, gates

**Files:**
- Modify (full replacement): `experiments/s2_latch_probe.py`
- Modify: `experiments/test_s2_latch_probe.py` (append classes before the `if __name__` block)

**Interfaces:**
- Consumes: Task 2's `steal_stat` (`score_run`, `NODES`, `format_line`); `s2_both_off_canon.score(n)`; the first probe's helpers (all kept with the same names and signatures: `build_config`, `expected_replicas`, `prep_script`, `classify`, `is_blend`, `sojourn_window`, `gate`, `score_line`).
- Produces: new `TREATMENTS` keys `ck_rep2_pc120_spawn10`, `ck_cpu1000_pc120`, `ck_cpu1000_pc120_spawn10`, `recs_cpu1000_spawn10`; `ARMS_V2`; `projected_requests_mc(treatment) -> int`; `REQUEST_CEILING_MC = 15600`; `family(treatment) -> str`; `hold_order(seed=20261004, first_slot=128) -> list[(slot, "A"|"B", treatment)]`; `parse_age_seconds(age) -> int`; `pod_ages(t0_text) -> dict`; CLI commands `fit <treatment>` (exit 3 over the ceiling), `order [seed] [first_slot]`, `steal <slot>`; `gate` now also enforces rows >= 540, pod age <= 1200 s at t=0, and steal files and samples.

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_s2_latch_probe.py`, above the `if __name__ == "__main__":` line (the `base_cfg()` and `cpu()` helpers already exist at the top of that file):

```python
class TestV2Treatments(unittest.TestCase):
    def test_four_new_treatments(self):
        c = p.build_config(base_cfg(), "ck_rep2_pc120_spawn10", 130)
        self.assertEqual(c["locust"]["spawn_rate"], 10)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        self.assertEqual([x["replicas"] for x in c["scale_constraints"] if x["method"] == "replicas"], [2])
        self.assertEqual(cpu(c, "checkoutservice"), 800)
        c = p.build_config(base_cfg(), "ck_cpu1000_pc120", 131)
        self.assertEqual(cpu(c, "checkoutservice"), 1000)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        self.assertEqual(c["locust"]["spawn_rate"], 50)
        self.assertFalse([x for x in c["scale_constraints"] if x["method"] == "replicas"])
        c = p.build_config(base_cfg(), "ck_cpu1000_pc120_spawn10", 137)
        self.assertEqual((cpu(c, "checkoutservice"), c["locust"]["spawn_rate"]), (1000, 10))
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        c = p.build_config(base_cfg(), "recs_cpu1000_spawn10", 132)
        self.assertEqual((cpu(c, "recommendationservice"), c["locust"]["spawn_rate"]), (1000, 10))
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 90)
        self.assertEqual(cpu(c, "checkoutservice"), 800)

    def test_expected_replicas_for_new_arms(self):
        self.assertEqual(p.expected_replicas("ck_rep2_pc120_spawn10")["checkoutservice"], 2)
        self.assertEqual(p.expected_replicas("ck_cpu1000_pc120_spawn10")["checkoutservice"], 1)


class TestFitAndPrepV2(unittest.TestCase):
    def test_projected_requests(self):
        self.assertEqual(p.projected_requests_mc("control"), 14305)
        self.assertEqual(p.projected_requests_mc("spawn10"), 14305)
        self.assertEqual(p.projected_requests_mc("ck_rep2_pc120"), 15205)   # run123 t0 showed 15205
        self.assertEqual(p.projected_requests_mc("ck_cpu1000_pc120"), 14505)
        self.assertEqual(p.projected_requests_mc("recs_cpu1000"), 14155)

    def test_every_v2_arm_fits_under_the_ceiling(self):
        for t in p.ARMS_V2 + ["control"]:
            self.assertLessEqual(p.projected_requests_mc(t), p.REQUEST_CEILING_MC, t)

    def test_the_pending_combination_would_not_fit(self):
        p.TREATMENTS["_bad"] = {"checkout_cpu": 1000, "checkout_replicas": 2}
        try:
            self.assertGreater(p.projected_requests_mc("_bad"), p.REQUEST_CEILING_MC)
        finally:
            del p.TREATMENTS["_bad"]

    def test_prep_scales_down_before_patching_then_rolls_then_scales_up(self):
        s = p.prep_script("ck_rep2_pc120")
        self.assertNotIn("\r", s)
        down = s.index("--replicas=1")
        patch = s.index("patch_cpu checkoutservice 800m")
        roll = s.index("rollout restart deployment/checkoutservice")
        up = s.index("--replicas=2")
        self.assertTrue(down < patch < roll < up)
        self.assertIn("rollout restart deployment/recommendationservice", s)

    def test_prep_node_line_precedes_pending_and_ceiling_exits_3(self):
        s = p.prep_script("control")
        self.assertLess(s.index("--- node_cpu_requests_m"), s.index("--- pending"))
        self.assertLess(s.index("--- pending"), s.index("--- end"))
        self.assertIn('-gt 15600', s)
        self.assertIn("exit 3", s)
        self.assertIn("topfull-worker1", s)


class TestHoldOrder(unittest.TestCase):
    def setUp(self):
        self.order = p.hold_order(20261004, 128)

    def test_twenty_holds_slots_128_to_147(self):
        self.assertEqual([x[0] for x in self.order], list(range(128, 148)))

    def test_each_arm_once_per_block_and_three_controls_per_block(self):
        for blk in "AB":
            ts = [t for _, b, t in self.order if b == blk]
            self.assertEqual(len(ts), 10)
            self.assertEqual(sorted(t for t in ts if t != "control"), sorted(p.ARMS_V2))
            self.assertEqual(ts.count("control"), 3)

    def test_first_and_last_holds_are_controls(self):
        self.assertEqual(self.order[0][2], "control")
        self.assertEqual(self.order[-1][2], "control")

    def test_no_same_family_back_to_back_including_block_boundary(self):
        ts = [t for _, _, t in self.order]
        for a, b in zip(ts, ts[1:]):
            self.assertNotEqual(p.family(a), p.family(b), (a, b))

    def test_deterministic_for_a_seed_and_different_for_another(self):
        self.assertEqual(self.order, p.hold_order(20261004, 128))
        self.assertNotEqual([t for _, _, t in self.order],
                            [t for _, _, t in p.hold_order(1, 128)])

    def test_pinned_order_for_seed_20261004(self):
        self.assertEqual([t for _, _, t in self.order], [
            "control", "spawn10", "control", "ck_cpu1000_pc120", "recs_cpu1000_spawn10",
            "ck_rep2_pc120", "recs_cpu1000", "control", "ck_rep2_pc120_spawn10",
            "ck_cpu1000_pc120_spawn10",
            "spawn10", "control", "recs_cpu1000_spawn10", "ck_rep2_pc120_spawn10",
            "ck_cpu1000_pc120", "control", "recs_cpu1000", "ck_cpu1000_pc120_spawn10",
            "ck_rep2_pc120", "control"])


class TestPodAges(unittest.TestCase):
    T0 = (
        "### pods\n"
        "NAME  READY STATUS RESTARTS AGE IP NODE\n"
        "checkoutservice-85fb96fbf-76zdj          2/2     Running   2 (6h6m ago)   6h15m   192.168.148.111   topfull-worker1   <none>   <none>\n"
        "checkoutservice-85fb96fbf-p27c4          2/2     Running   0              40m     192.168.148.110   topfull-worker1   <none>   <none>\n"
        "recommendationservice-566f644686-jwsxh   2/2     Running   0              6m22s   192.168.148.92    topfull-worker1   <none>   <none>\n"
        "frontend-85ff4b5b6d-8zjvs                2/2     Running   22 (6h6m ago)  4d15h   192.168.148.118   topfull-worker1   <none>   <none>\n")

    def test_parse_age_seconds(self):
        self.assertEqual(p.parse_age_seconds("6m22s"), 382)
        self.assertEqual(p.parse_age_seconds("6h15m"), 22500)
        self.assertEqual(p.parse_age_seconds("2d14h"), 2 * 86400 + 14 * 3600)
        self.assertEqual(p.parse_age_seconds("45s"), 45)
        with self.assertRaises(ValueError):
            p.parse_age_seconds("old")

    def test_pod_ages_picks_only_checkout_and_recs_and_skips_restart_age(self):
        a = p.pod_ages(self.T0)
        self.assertEqual(sorted(a["checkoutservice"]), [2400, 22500])
        self.assertEqual(a["recommendationservice"], [382])
```

- [ ] **Step 2: Run to verify failure**

Run: `python experiments/test_s2_latch_probe.py -v`
Expected: the new classes error with `KeyError: 'ck_rep2_pc120_spawn10'` / `AttributeError: module 's2_latch_probe' has no attribute 'projected_requests_mc'` (and `hold_order`, `pod_ages`, `parse_age_seconds`). The first-probe tests still pass.

- [ ] **Step 3: Replace the module**

Replace the whole of `experiments/s2_latch_probe.py` with the following. It keeps every first-probe function (same names and signatures) and fixes the garbled arrow character in the `classify` comment.

```python
"""Helpers for the S2 checkout-latch probe series (runs 108-127, v2 holds from run128).

CLI:
  python experiments/s2_latch_probe.py config <treatment> <slot>   # writes configs/scenario_2_latch_probe.yaml
  python experiments/s2_latch_probe.py prep <treatment>            # prints bash for: ssh topfull-master bash -s
  python experiments/s2_latch_probe.py fit <treatment>             # exit 3 if worker CPU requests would pass the ceiling
  python experiments/s2_latch_probe.py gate <treatment> <slot>     # exit 0 = pass
  python experiments/s2_latch_probe.py score <slot> [--root newvms|campaign]
  python experiments/s2_latch_probe.py steal <slot>                # CPU steal % per node for one pulled folder
  python experiments/s2_latch_probe.py order [seed] [first_slot]   # prints the v2 hold order table
"""
import copy
import csv
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s2_both_off_canon as canon  # noqa: E402
import steal_stat  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BASE_CONFIG = HERE / "configs" / "scenario_2_baseline_no_topfull.yaml"
OUT_CONFIG = HERE / "configs" / "scenario_2_latch_probe.yaml"
NEW_VMS = str(REPO / "experiments" / "results" / "new vms" /
              "baseline_no_topfull_sustained_overload_run%d")
CAMPAIGN = canon.ROOT

BASE_COUNTS = {"getproduct": 275, "postcheckout": 90, "getcart": 100,
               "postcart": 90, "emptycart": 5}
CHECKOUT_MC, RECS_MC = 800, 1150

# Worker (topfull-worker1, 16 vCPU, allocatable 16000 m) CPU *requests* at the Paper-C1 base,
# sidecars included: 14305 m = the 15205 m seen in run123's t0 snapshot (two checkout pods)
# minus one 800 m + 100 m checkout pod. Ceiling leaves 400 m of headroom.
BASE_REQUESTS_MC = 14305
SIDECAR_REQUEST_MC = 100
REQUEST_CEILING_MC = 15600

# Pods older than this at t=0 mean prep did not roll them (v2 rule: every hold starts fresh).
MAX_POD_AGE_S = 1200
MIN_STEAL_SAMPLES = 100
STEAL_NODES = steal_stat.NODES

# treatment -> overrides. Keys: spawn_rate, counts, checkout_cpu, recs_cpu,
# checkout_replicas, restart.
TREATMENTS = {
    "control": {},
    "spawn10": {"spawn_rate": 10},
    "restart": {"restart": True},
    "recs_users310": {"counts": {"getproduct": 310}},
    "recs_cpu1000": {"recs_cpu": 1000},
    "ck_cpu1000": {"checkout_cpu": 1000},
    "ck_rep2": {"checkout_replicas": 2},
    "pc120": {"counts": {"postcheckout": 120}},
    "ck_rep2_pc120": {"checkout_replicas": 2, "counts": {"postcheckout": 120}},
    # v2 (run128 onward)
    "ck_rep2_pc120_spawn10": {"checkout_replicas": 2, "counts": {"postcheckout": 120},
                              "spawn_rate": 10},
    "ck_cpu1000_pc120": {"checkout_cpu": 1000, "counts": {"postcheckout": 120}},
    "ck_cpu1000_pc120_spawn10": {"checkout_cpu": 1000, "counts": {"postcheckout": 120},
                                 "spawn_rate": 10},
    "recs_cpu1000_spawn10": {"recs_cpu": 1000, "spawn_rate": 10},
}

# The seven v2 arms (two holds each) and the control.
ARMS_V2 = ["ck_rep2_pc120", "ck_rep2_pc120_spawn10", "ck_cpu1000_pc120",
           "ck_cpu1000_pc120_spawn10", "spawn10", "recs_cpu1000", "recs_cpu1000_spawn10"]


def _set_cpu(cfg, dep, mc):
    for c in cfg["scale_constraints"]:
        if c["deployment"] == dep and c["method"] == "cpu_limit":
            c["cpu_limit_millicores"] = mc
            return
    raise KeyError(f"no cpu_limit constraint for {dep}")


def build_config(base: dict, treatment: str, slot: int) -> dict:
    t = TREATMENTS[treatment]
    cfg = copy.deepcopy(base)
    cfg["run_number"] = slot
    cfg["log_folder"] = f"baseline_no_topfull_sustained_overload_run{slot}"
    cfg["description"] = (f"Both controllers off. Paper-C1. Latch probe, treatment "
                          f"{treatment}, run89 mix base.")
    cfg["locust"]["user_counts"] = {**BASE_COUNTS, **t.get("counts", {})}
    cfg["locust"]["spawn_rate"] = t.get("spawn_rate", 50)
    if "checkout_cpu" in t:
        _set_cpu(cfg, "checkoutservice", t["checkout_cpu"])
    if "recs_cpu" in t:
        _set_cpu(cfg, "recommendationservice", t["recs_cpu"])
    if "checkout_replicas" in t:
        cfg["scale_constraints"].append({
            "deployment": "checkoutservice", "namespace": "default",
            "method": "replicas", "replicas": t["checkout_replicas"]})
    if t.get("restart"):
        cfg["restart_before_hold"] = {
            "deployments": ["checkoutservice", "recommendationservice"],
            "settle_seconds": 60}
    return cfg


def expected_replicas(treatment: str) -> dict:
    out = {"frontend": 4}
    out["checkoutservice"] = TREATMENTS[treatment].get("checkout_replicas", 1)
    return out


def projected_requests_mc(treatment: str) -> int:
    """Worker CPU requests (m) once prep has finished, sidecars included."""
    t = TREATMENTS[treatment]
    ck = (t.get("checkout_cpu", CHECKOUT_MC) + SIDECAR_REQUEST_MC) * t.get("checkout_replicas", 1)
    base_ck = CHECKOUT_MC + SIDECAR_REQUEST_MC
    return BASE_REQUESTS_MC - base_ck + ck + (t.get("recs_cpu", RECS_MC) - RECS_MC)


# Prep order matters for schedulability: scale checkout to 1 first (so a CPU patch never rolls
# two big pods), patch both Deployments, roll both so every hold starts with pods of the same
# age, then scale checkout to the hold's replica count. The final check exits 3 if the worker's
# CPU requests are over the ceiling. "--- node_cpu_requests_m" must stay before "--- pending":
# latch_hold_pre.ps1 reads the text between "--- pending" and "--- end" as the Pending list.
_PREP = """set -e
patch_cpu() {
  kubectl patch deployment "$1" -n default -p \\
    "{\\"spec\\":{\\"template\\":{\\"spec\\":{\\"containers\\":[{\\"name\\":\\"server\\",\\"resources\\":{\\"limits\\":{\\"cpu\\":\\"$2\\"},\\"requests\\":{\\"cpu\\":\\"$2\\"}}}]}}}}"
}
kubectl scale deployment/checkoutservice -n default --replicas=1
kubectl rollout status deployment/checkoutservice -n default --timeout=240s
patch_cpu checkoutservice @CK@m
patch_cpu recommendationservice @RC@m
kubectl rollout restart deployment/checkoutservice -n default
kubectl rollout restart deployment/recommendationservice -n default
kubectl rollout status deployment/checkoutservice -n default --timeout=240s
kubectl rollout status deployment/recommendationservice -n default --timeout=240s
kubectl scale deployment/checkoutservice -n default --replicas=@REP@
kubectl rollout status deployment/checkoutservice -n default --timeout=240s
sleep 20
echo "--- pods"
kubectl get pods -n default -o wide
echo "--- node_cpu_requests_m"
req=$(kubectl describe node topfull-worker1 | awk '/^  cpu /{gsub("m","",$2); print $2}')
echo "$req"
echo "--- pending"
kubectl get pods -n default --field-selector=status.phase=Pending --no-headers
echo "--- end"
if [ "$req" -gt @CEIL@ ]; then echo "OVER CEILING: $req m > @CEIL@ m"; exit 3; fi
"""


def prep_script(treatment: str) -> str:
    t = TREATMENTS[treatment]
    s = (_PREP.replace("@CK@", str(t.get("checkout_cpu", CHECKOUT_MC)))
              .replace("@RC@", str(t.get("recs_cpu", RECS_MC)))
              .replace("@REP@", str(t.get("checkout_replicas", 1)))
              .replace("@CEIL@", str(REQUEST_CEILING_MC)))
    return s.replace("\r", "")


def is_blend(o: dict) -> bool:
    s = o["svc"]
    g = lambda svc, k: s.get(svc, {}).get(k, 0) or 0  # noqa: E731
    return (g("recommendationservice", "streak") >= 10 and g("recommendationservice", "ov") >= 10
            and g("checkoutservice", "streak") >= 10 and g("checkoutservice", "ov") >= 10
            and (g("emailservice", "ov") >= 10 or g("paymentservice", "ov") >= 10))


def classify(o: dict) -> str:
    s = o["svc"]
    ck = s.get("checkoutservice", {}).get("streak", 0) or 0
    rc = s.get("recommendationservice", {}).get("streak", 0) or 0
    ret = o["edges"].get(("frontend", "recommendationservice"), 0)
    if ck >= 400 and rc == 0:
        return "sticky"
    # 70_000 sits under run 101's 76,303 frontend>recommendations retries and
    # above the 50,000 count that stays "other".
    if ret >= 70000:
        return "released"
    return "other"


def _ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").timestamp()


def sojourn_window(root: str, n: int, lo: int = 90, hi: int = 150) -> dict:
    """Checkout inbound mean sojourn (ms) and share of ticks above 500 ms, lo..hi s
    after the first checkout row. Clock is the collector's, not Locust's."""
    path = os.path.join(root % n, "service_inbound.csv")
    rows = [r for r in csv.DictReader(open(path)) if r["service"] == "checkoutservice"]
    if len(rows) < 2:
        return {"mean_ms": None, "share_over_500": None, "ticks": 0}
    t0 = _ts(rows[0]["timestamp"])
    vals = []
    for a, b in zip(rows, rows[1:]):
        t = _ts(b["timestamp"]) - t0
        if not (lo <= t <= hi):
            continue
        dc = float(b["rq_time_count"]) - float(a["rq_time_count"])
        ds = float(b["rq_time_sum_ms"]) - float(a["rq_time_sum_ms"])
        if dc > 0:
            vals.append(ds / dc)
    if not vals:
        return {"mean_ms": None, "share_over_500": None, "ticks": 0}
    return {"mean_ms": round(sum(vals) / len(vals), 1),
            "share_over_500": round(sum(v > 500 for v in vals) / len(vals), 2),
            "ticks": len(vals)}


_AGE_PART = re.compile(r"(\d+)([dhms])")
_AGE_UNIT_S = {"d": 86400, "h": 3600, "m": 60, "s": 1}
_POD_AGE_RE = re.compile(r"(\S+)\s+\d{1,3}(?:\.\d{1,3}){3}\s")


def parse_age_seconds(age: str) -> int:
    """kubectl AGE such as '6m22s', '6h15m', '2d14h', '45s'."""
    parts = _AGE_PART.findall(age)
    if not parts:
        raise ValueError(f"unparseable age {age!r}")
    return sum(int(n) * _AGE_UNIT_S[u] for n, u in parts)


def pod_ages(t0_text: str, services=("checkoutservice", "recommendationservice")) -> dict:
    """Age in seconds of every pod of `services` in the '### pods' table of a t0.txt snapshot."""
    out = {svc: [] for svc in services}
    for line in t0_text.splitlines():
        words = line.split()
        if not words:
            continue
        for svc in services:
            if words[0].startswith(svc + "-"):
                m = _POD_AGE_RE.search(line)
                if m:
                    out[svc].append(parse_age_seconds(m.group(1)))
    return out


def family(treatment: str) -> str:
    """Arms that share a lever are never run back to back."""
    if treatment == "control":
        return "control"
    if treatment.startswith("ck_rep2"):
        return "rep2"
    if treatment.startswith("ck_cpu1000"):
        return "ck_cpu"
    if treatment.startswith("recs_cpu1000"):
        return "recs_cpu"
    return treatment


def hold_order(seed: int = 20261004, first_slot: int = 128) -> list:
    """Two blocks of ten: block A = control first + (7 arms + 2 controls) shuffled;
    block B = (7 arms + 2 controls) shuffled + control last. Reshuffled until no two
    adjacent holds (across the A/B boundary too) share a family. Returns
    [(slot, 'A'|'B', treatment), ...]."""
    rng = random.Random(seed)
    while True:
        a = ARMS_V2 + ["control", "control"]
        rng.shuffle(a)
        block_a = ["control"] + a
        b = ARMS_V2 + ["control", "control"]
        rng.shuffle(b)
        block_b = b + ["control"]
        seq = block_a + block_b
        if all(family(x) != family(y) for x, y in zip(seq, seq[1:])):
            break
    return [(first_slot + i, "A" if i < 10 else "B", t) for i, t in enumerate(seq)]


def gate(n: int, treatment: str, root: str = NEW_VMS):
    canon.ROOT = root
    d = root % n
    problems, notes = [], []
    need = ["service_inbound.csv", "service_edges.csv", "topfull_detect.csv",
            "resource_usage.csv", "total.csv", "service_capacity.json"]
    missing = [f for f in need if not os.path.exists(os.path.join(d, f))]
    if missing:
        return False, [f"missing {missing}"]
    rows = sum(1 for _ in open(os.path.join(d, "total.csv"))) - 1
    o = canon.score(n)
    q, s = o["q"], o["svc"]
    notes.append(f"rows {rows} span {round(q.get('span', 0))} gap2 {q.get('gap2_pct')}")
    if rows < 540:
        problems.append(f"total.csv rows {rows} < 540")
    if not (480 <= q.get("span", 0) <= 900):
        problems.append(f"mesh span {q.get('span')} outside 480-900")
    if q.get("gap2_pct", 100) > 10:
        problems.append(f"gap2_pct {q.get('gap2_pct')} > 10")
    exp = expected_replicas(treatment)
    for svc, v in s.items():
        if svc == "__master_node__" or "rmode" not in v:
            continue
        want = exp.get(svc, 1)
        if v["rmode"] != want:
            problems.append(f"{svc} replica mode {v['rmode']} != {want}")
        if v.get("rzero", 0) > 0 and svc in ("checkoutservice", "recommendationservice"):
            notes.append(f"WARN {svc} rzero {v['rzero']}")
    # v2: pods must be fresh at t=0 (prep rolls them) and steal capture must be complete.
    t0 = os.path.join(d, "state", "t0.txt")
    if not os.path.exists(t0):
        problems.append("STATE: state/t0.txt missing")
    else:
        ages = pod_ages(open(t0, encoding="utf-8-sig", errors="replace").read())
        for svc, vals in ages.items():
            if not vals:
                problems.append(f"STATE: no {svc} pod in t0.txt")
            elif max(vals) > MAX_POD_AGE_S:
                problems.append(f"STATE: {svc} pod age {max(vals)} s > {MAX_POD_AGE_S} s at t=0")
        notes.append("t0 pod ages s " + str({k: v for k, v in ages.items()}))
    files = [f"steal_{tag}_{node}.txt" for tag in ("t0", "end") for node in STEAL_NODES]
    files += [f"steal_series_{node}.txt" for node in STEAL_NODES]
    miss = [f for f in files if not os.path.exists(os.path.join(d, "state", f))]
    if miss:
        problems.append(f"STEAL: missing state files {miss}")
    else:
        sc = steal_stat.score_run(d)
        for node in STEAL_NODES:
            r = sc[node]
            if r["samples"] < MIN_STEAL_SAMPLES:
                problems.append(f"STEAL: {node} series has {r['samples']} samples < {MIN_STEAL_SAMPLES}")
            if (r["hold_pct"] or 0) > 2.0:
                notes.append(f"WARN {node} steal {r['hold_pct']:.2f}% over the hold")
    return not problems, problems + notes


def score_line(n: int, root: str) -> str:
    canon.ROOT = root
    o = canon.score(n)
    s = o["svc"]
    f = lambda svc, k: s.get(svc, {}).get(k)  # noqa: E731
    soj = sojourn_window(root, n)
    ret_r = o["edges"].get(("frontend", "recommendationservice"), 0)
    ret_c = o["edges"].get(("frontend", "checkoutservice"), 0)
    return (f"run{n} {classify(o)} blend={is_blend(o)} "
            f"ck streak/ov {f('checkoutservice','streak')}/{f('checkoutservice','ov')} "
            f"recs streak/ov {f('recommendationservice','streak')}/{f('recommendationservice','ov')} "
            f"email_ov {f('emailservice','ov')} pay_ov {f('paymentservice','ov')} "
            f"retries f>recs {int(ret_r)} f>ck {int(ret_c)} "
            f"ck_sojourn_90_150 {soj['mean_ms']}ms over500 {soj['share_over_500']}")


def main(argv):
    cmd = argv[1]
    if cmd == "config":
        base = yaml.safe_load(open(BASE_CONFIG, encoding="utf-8"))
        cfg = build_config(base, argv[2], int(argv[3]))
        OUT_CONFIG.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        print(f"wrote {OUT_CONFIG} for {argv[2]} run{argv[3]}")
        return 0
    if cmd == "prep":
        sys.stdout.buffer.write(prep_script(argv[2]).encode())
        return 0
    if cmd == "fit":
        need = projected_requests_mc(argv[2])
        ok = need <= REQUEST_CEILING_MC
        print(f"{argv[2]}: projected worker CPU requests {need} m, ceiling {REQUEST_CEILING_MC} m "
              f"-> {'FITS' if ok else 'DOES NOT FIT'}")
        return 0 if ok else 3
    if cmd == "gate":
        ok, lines = gate(int(argv[3]), argv[2])
        print("\n".join(lines))
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    if cmd == "score":
        root = CAMPAIGN if "--root" in argv and argv[argv.index("--root") + 1] == "campaign" else NEW_VMS
        print(score_line(int(argv[2]), root))
        return 0
    if cmd == "steal":
        d = NEW_VMS % int(argv[2])
        print(steal_stat.format_line(f"run{argv[2]}", steal_stat.score_run(d)))
        return 0
    if cmd == "order":
        seed = int(argv[2]) if len(argv) > 2 else 20261004
        first = int(argv[3]) if len(argv) > 3 else 128
        print("| Slot | Block | Treatment |")
        print("|---|---|---|")
        for slot, block, t in hold_order(seed, first):
            print(f"| {slot} | {block} | {t} |")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run to verify pass**

Run: `python experiments/test_s2_latch_probe.py -v`
Expected: 31 tests, OK. Then run the other modules this plan touches:

```powershell
python experiments/test_steal_stat.py
python experiments/test_run_scenario.py
python experiments/test_s2_both_off_abc.py
```

Expected: all OK. (`experiments/test_topfull_cpu_quotas.py` has a known failure in `TestBothOffYamlRestored`; it expects run87. Do not fix it here.)

- [ ] **Step 5: Check every arm fits the worker**

```powershell
foreach ($t in "control","spawn10","ck_rep2_pc120","ck_rep2_pc120_spawn10","ck_cpu1000_pc120","ck_cpu1000_pc120_spawn10","recs_cpu1000","recs_cpu1000_spawn10") { python experiments/s2_latch_probe.py fit $t }
```

Expected, each line ending `FITS` with these numbers: control 14305 m, spawn10 14305 m, ck_rep2_pc120 15205 m, ck_rep2_pc120_spawn10 15205 m, ck_cpu1000_pc120 14505 m, ck_cpu1000_pc120_spawn10 14505 m, recs_cpu1000 14155 m, recs_cpu1000_spawn10 14155 m (ceiling 15600 m).

- [ ] **Step 6: Print the hold order and compare it with the table above**

```powershell
python experiments/s2_latch_probe.py order 20261004 128
```

Expected: exactly the 20 rows of the "Hold order" table in this plan (slot, block, treatment). If a row differs, stop: the hold order in this plan and the code have diverged.

- [ ] **Step 7: Commit**

```powershell
git add experiments/s2_latch_probe.py experiments/test_s2_latch_probe.py
git commit -m "feat: latch probe v2 treatments, hold order, fit check, pod-age and steal gates"
```

---

### Task 4: Per-hold scripts and the restore gate

**Files:**
- Modify (full replacement): `experiments/latch_hold_pre.ps1`
- Modify (full replacement): `experiments/latch_hold_run.ps1`
- Create: `experiments/latch_restore_check.sh` (LF only)
- Create: `experiments/latch_restore_fix.sh` (LF only)

**Interfaces:**
- Consumes: `s2_latch_probe.py` CLI (`fit`, `prep`, `config`, `gate`, `score`, `steal`); `experiments/node_steal.sh`; `experiments/latch_snapshot.sh` (unchanged).
- Produces: `latch_hold_pre.ps1 -Treatment T [-DryRun]` and `latch_hold_run.ps1 -Treatment T -Slot N [-DryRun]` (exit 0 only when the gate passes); `latch_restore_check.sh` (exit 0 when Paper-C1 is restored). Per run, the run script saves `state/t0.txt`, `state/end.txt`, `state/steal_{t0,end}_{master,worker,load}.txt` and `state/steal_series_{master,worker,load}.txt` (sampler file pulled with `scp`).

- [ ] **Step 1: Replace the prep wrapper**

Replace `experiments/latch_hold_pre.ps1` with:

```powershell
param(
    [Parameter(Mandatory)][string]$Treatment,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# Schedulability gate: refuse before touching the cluster if the worker's CPU requests would
# pass the ceiling for this treatment (a checkout pod went Pending on 2026-10-03 when 1000 m
# and two replicas were combined).
python experiments/s2_latch_probe.py fit $Treatment
if ($LASTEXITCODE -ne 0) { Write-Error "fit check failed for $Treatment"; exit 1 }

if ($DryRun) {
    python experiments/s2_latch_probe.py prep $Treatment
    exit 0
}

# cmd /c keeps the pipe byte-exact (PowerShell would add CRLF to the bash script).
# Continue: with Stop, Windows PowerShell turns merged native stderr into a
# terminating error. kubectl rollout status writes progress to stderr on success.
$eap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $out = @(cmd /c "python experiments\s2_latch_probe.py prep $Treatment | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s" 2>&1 | ForEach-Object { "$_" })
    $rc = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $eap
}
$out | ForEach-Object { Write-Host $_ }
if ($rc -ne 0) { Write-Error "prep failed rc=$rc (rc=3 means the worker CPU request ceiling was passed)"; exit 1 }

$text = ($out | ForEach-Object { "$_" }) -join "`n"
if ($text -notmatch "--- end") { Write-Error "prep did not reach '--- end'"; exit 1 }
$m = [regex]::Match($text, '(?s)--- pending\r?\n(.*?)--- end')
$pendingBody = ""
if ($m.Success) { $pendingBody = $m.Groups[1].Value }
# kubectl prints "No resources found..." on an empty Pending list; that is not a pod.
$pendingLines = @($pendingBody -split "`r?`n" | Where-Object {
    $line = $_.Trim()
    $line.Length -gt 0 -and $line -notmatch '^No resources found'
})
if ($pendingLines.Count -gt 0) {
    Write-Error "Pending pods after prep: $($pendingLines -join ', ')"
    exit 1
}
Write-Host "PREP OK for $Treatment"
exit 0
```

- [ ] **Step 2: Replace the run wrapper**

Replace `experiments/latch_hold_run.ps1` with:

```powershell
param(
    [Parameter(Mandatory)][string]$Treatment,
    [Parameter(Mandatory)][int]$Slot,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$name = "baseline_no_topfull_sustained_overload_run$Slot"
$src  = "experiments\results\campaign_48\S2_sustained_overload\$name"
$dest = "experiments\results\new vms\$name"
$S    = ".superpowers\latch\state\run$Slot"
$cfg  = "experiments/configs/scenario_2_latch_probe.yaml"
$StealRemote = "/tmp/latch_steal_run$Slot.txt"
$Nodes = @(
    @{ Key = "master"; Hostname = "topfull-master" },
    @{ Key = "worker"; Hostname = "topfull-worker-1" },
    @{ Key = "load";   Hostname = "topfull-load" }
)

function Step([string]$Label, [scriptblock]$Block) {
    Write-Host "==> $Label"
    if ($DryRun) { Write-Host "    (dry run) $Block"; return }
    $global:LASTEXITCODE = 0
    & $Block
    if ($LASTEXITCODE -ne 0) { throw "$Label failed rc=$LASTEXITCODE" }
}

function Save-Snapshot([string]$File) {
    # Continue: with Stop, Windows PowerShell turns merged native stderr into a
    # terminating error before LASTEXITCODE is stored.
    $eap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $m = @(cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s < experiments\latch_snapshot.sh" 2>&1 | ForEach-Object { "$_" })
        $masterRc = $LASTEXITCODE
        $w = @(ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "uname -r; uptime -s; nproc" 2>&1 | ForEach-Object { "$_" })
        $workerRc = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $eap
    }
    if ($masterRc -ne 0 -or $workerRc -ne 0) {
        $m + $w | ForEach-Object { Write-Host $_ }
        throw "snapshot failed master=$masterRc worker=$workerRc"
    }
    $lines = @("# captured " + (Get-Date -Format o)) + $m + @("### worker kernel / boot / nproc") + $w
    $lines | ForEach-Object { "$_" } | Out-File -Encoding utf8 $File
}

# Runs experiments/node_steal.sh on one node (script on stdin, mode after "--").
function Invoke-Node([string]$Hostname, [string]$NodeArgs) {
    $eap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $o = @(cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 $Hostname bash -s -- $NodeArgs < experiments\node_steal.sh" 2>&1 | ForEach-Object { "$_" })
        $rc = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $eap
    }
    if ($rc -ne 0) {
        $o | ForEach-Object { Write-Host $_ }
        throw "node_steal.sh $NodeArgs failed on $Hostname rc=$rc"
    }
    return $o
}

function Save-Steal([string]$Tag) {
    foreach ($n in $Nodes) {
        $o = Invoke-Node $n.Hostname "snap"
        $o | Out-File -Encoding utf8 "$S\steal_${Tag}_$($n.Key).txt"
    }
}

function Start-Samplers {
    foreach ($n in $Nodes) { Invoke-Node $n.Hostname "start $StealRemote" | Out-Null }
}

function Stop-Samplers {
    foreach ($n in $Nodes) {
        Invoke-Node $n.Hostname "stop $StealRemote" | Out-Null
        $global:LASTEXITCODE = 0
        scp -o BatchMode=yes -o ConnectTimeout=8 "$($n.Hostname):$StealRemote" "$S\steal_series_$($n.Key).txt"
        if ($LASTEXITCODE -ne 0) { throw "scp of the steal series failed from $($n.Hostname)" }
    }
}

if ((Test-Path $dest) -or (Test-Path $src)) { throw "$name already exists locally; refusing to overwrite" }

Step "t=0 snapshot" { New-Item -ItemType Directory -Force $S | Out-Null; Save-Snapshot "$S\t0.txt" }
Step "t=0 steal snapshot, 3 nodes (about 35 s)" { Save-Steal "t0" }
Step "start steal samplers (every 5 s)" { Start-Samplers }
try {
    Step "generate config" { python experiments/s2_latch_probe.py config $Treatment $Slot }
    Step "clear stale remote scripts" {
        ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
    }
    Step "run hold (about 17 min)" { python experiments/run_scenario.py $cfg }
} finally {
    try { Step "stop steal samplers and fetch the series" { Stop-Samplers } }
    catch { Write-Host "WARN: sampler stop/fetch failed: $_ (the gate will report missing steal files)" }
}
Step "pull" { python experiments/pull_results.py $cfg }
Step "move into new vms" { Move-Item $src "experiments\results\new vms\" }
Step "end snapshot" { Save-Snapshot "$S\end.txt" }
Step "end steal snapshot, 3 nodes (about 35 s)" { Save-Steal "end" }
Step "copy snapshots into run folder" { Copy-Item $S "$dest\state" -Recurse }

if ($DryRun) { exit 0 }

python experiments/s2_latch_probe.py gate $Treatment $Slot
$gateRc = $LASTEXITCODE
python experiments/s2_latch_probe.py score $Slot
python experiments/s2_latch_probe.py steal $Slot
exit $gateRc
```

- [ ] **Step 3: Create the restore gate and make it LF**

Create `experiments/latch_restore_check.sh`:

```bash
#!/bin/bash
# Paper-C1 restore gate. Run on topfull-master:  ssh topfull-master bash -s < experiments/latch_restore_check.sh
# Exit 0 only if checkout 800 m x1, recommendations 1150 m x1, every other Paper-C1 limit unchanged,
# frontend HPA 4/4 with 4 ready, catalog HPA 1/1, sidecar request 100 m everywhere with no
# proxyCPULimit, and no Pending pods.
fail=0
check() {
  if [ "$2" != "$3" ]; then echo "FAIL $1: got '$2' want '$3'"; fail=1; else echo "ok   $1 = $2"; fi
}
cpu() {
  kubectl get deploy "$1" -n default -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}'
}
reps() { kubectl get deploy "$1" -n default -o jsonpath='{.spec.replicas}'; }

check checkoutservice_cpu "$(cpu checkoutservice)" 800m
check recommendationservice_cpu "$(cpu recommendationservice)" 1150m
check checkoutservice_replicas "$(reps checkoutservice)" 1
check recommendationservice_replicas "$(reps recommendationservice)" 1
check frontend_cpu "$(cpu frontend)" 1150m
check productcatalogservice_cpu "$(cpu productcatalogservice)" 800m
check cartservice_cpu "$(cpu cartservice)" 800m
check currencyservice_cpu "$(cpu currencyservice)" 770m
check shippingservice_cpu "$(cpu shippingservice)" 770m
check adservice_cpu "$(cpu adservice)" 1150m
check paymentservice_cpu "$(cpu paymentservice)" 155m
check emailservice_cpu "$(cpu emailservice)" 120m
check redis-cart_cpu "$(cpu redis-cart)" 540m

check frontend_hpa_min "$(kubectl get hpa frontend-hpa -n default -o jsonpath='{.spec.minReplicas}')" 4
check frontend_hpa_max "$(kubectl get hpa frontend-hpa -n default -o jsonpath='{.spec.maxReplicas}')" 4
check frontend_ready "$(kubectl get deploy frontend -n default -o jsonpath='{.status.readyReplicas}')" 4
check catalog_hpa_min "$(kubectl get hpa productcatalogservice-hpa -n default -o jsonpath='{.spec.minReplicas}')" 1
check catalog_hpa_max "$(kubectl get hpa productcatalogservice-hpa -n default -o jsonpath='{.spec.maxReplicas}')" 1

for d in $(kubectl get deploy -n default -o jsonpath='{.items[*].metadata.name}'); do
  check "${d}_proxyCPU" "$(kubectl get deploy "$d" -n default -o jsonpath='{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPU}')" 100m
  check "${d}_proxyCPULimit" "$(kubectl get deploy "$d" -n default -o jsonpath='{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPULimit}')" ""
done

check pending_pods "$(kubectl get pods -n default --field-selector=status.phase=Pending --no-headers 2>/dev/null | wc -l)" 0
if [ "$fail" -eq 0 ]; then echo "RESTORE GATE PASS"; else echo "RESTORE GATE FAIL"; fi
exit $fail
```

Create `experiments/latch_restore_fix.sh`:

```bash
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
```

```powershell
foreach ($f in 'latch_restore_check.sh','latch_restore_fix.sh') {
  python -c "import sys; p='experiments/'+sys.argv[1]; d=open(p,'rb').read().replace(b'\r\n',b'\n'); open(p,'wb').write(d)" $f
  python -c "import sys; print(b'\r' in open('experiments/'+sys.argv[1],'rb').read())" $f
  bash -n ("experiments/" + $f)
}
```

Expected: `False` twice, and `bash -n` prints nothing for both.

- [ ] **Step 4: Dry-run both wrappers**

```powershell
powershell -NoProfile -File experiments\latch_hold_pre.ps1 -Treatment ck_rep2_pc120_spawn10 -DryRun
powershell -NoProfile -File experiments\latch_hold_run.ps1 -Treatment ck_rep2_pc120_spawn10 -Slot 999 -DryRun
git status --short
```

Expected: the first prints `ck_rep2_pc120_spawn10: projected worker CPU requests 15205 m, ceiling 15600 m -> FITS`, then the bash with `--replicas=1` before `patch_cpu checkoutservice 800m` and `--replicas=2` after the rollouts, with no `\r`. The second prints twelve `==>` steps (t=0 snapshot, t=0 steal snapshot, start samplers, generate config, clear stale remote scripts, run hold, stop samplers and fetch, pull, move, end snapshot, end steal snapshot, copy snapshots) each with `(dry run)`. `git status --short` shows no new run folder and no `scenario_2_latch_probe.yaml`. If it throws "already exists", slot 999 collided; use another unused number.

- [ ] **Step 5: Commit**

```powershell
git add experiments/latch_hold_pre.ps1 experiments/latch_hold_run.ps1 experiments/latch_restore_check.sh experiments/latch_restore_fix.sh
git commit -m "feat: latch hold scripts capture CPU steal; fit gate; restore gate"
```

---

### Task 5: Table generator and scorecard (TDD, no VMs)

**Files:**
- Create: `experiments/s2_probe_tables.py`
- Create: `experiments/test_s2_probe_tables.py`
- Create (not committed): `.superpowers/latch/scorecard_v2.py`

**Interfaces:**
- Consumes: `s2_both_off_abc.score_run(run_dir)` returning `{"inbound": {svc: {"streak","high_samples","samples","failure_fraction"}}, "overloaded": {svc: {"ticks","overloaded_ticks","share"}}, "retry_by_edge", "retry_by_target", "layer_a_admitting_rows", "cpu_mean_max"}`; `steal_stat.score_run`, `md_row`.
- Produces: `s2_probe_tables.py --out <file> --block "A=128,129,…" --block "B=…"` (markdown: (a), (b), (c), CPU, arrival, 5xx, resets, sojourn, share above 500 ms, CPU fraction, detector utilization, Locust goodput / fail / P95, steal); `scorecard_v2.py` (per-hold rows, per-arm verdicts, controls, blend counts, steal by mode).

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_s2_probe_tables.py`:

```python
"""Unit tests for s2_probe_tables. Synthetic rows only."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s2_probe_tables as t


def inbound_rows(n=12):
    rows = []
    for i in range(n):
        total = 100 * i
        rows.append({
            "timestamp": f"2026-10-04T10:00:{i:02d}Z", "service": "checkoutservice",
            "total": str(total), "5xx": str(10 * i), "resets": str(5 * i),
            "rq_time_sum_ms": str(20000 * i), "rq_time_count": str(100 * i),
            "rq_time_buckets": json.dumps({"500": 90 * i, "+Inf": 100 * i}),
        })
    return rows


class TestInboundMetrics(unittest.TestCase):
    def test_known_rates(self):
        m = t.inbound_metrics(inbound_rows())        # 12 rows, last 5 dropped -> rows 0..6, 6 s
        self.assertAlmostEqual(m["arrival"], 100.0)
        self.assertAlmostEqual(m["fail5xx"], 0.10)
        self.assertAlmostEqual(m["reset"], 0.05)
        self.assertAlmostEqual(m["sojourn_ms"], 200.0)
        self.assertAlmostEqual(m["over500"], 0.10)   # 90 of every 100 are <= 500 ms

    def test_too_few_rows_returns_empty(self):
        self.assertEqual(t.inbound_metrics(inbound_rows(3)), {})

    def test_missing_bucket_key_skips_over500_only(self):
        rows = inbound_rows()
        for r in rows:
            r["rq_time_buckets"] = "{}"
        m = t.inbound_metrics(rows)
        self.assertNotIn("over500", m)
        self.assertIn("sojourn_ms", m)


class TestCells(unittest.TestCase):
    def data(self, streak, svc="checkoutservice"):
        return {"abc": {"inbound": {svc: {"streak": streak, "high_samples": streak + 3}},
                        "overloaded": {svc: {"overloaded_ticks": 300, "ticks": 600, "share": 0.5}},
                        "retry_by_target": {svc: 42}}}

    def test_a_bold_only_for_controlled_service_at_30(self):
        self.assertEqual(t.cell_a(self.data(30), "checkoutservice"), "**30 / 33**")
        self.assertEqual(t.cell_a(self.data(29), "checkoutservice"), "29 / 32")
        self.assertEqual(t.cell_a(self.data(500, "frontend"), "frontend"), "500 / 503")

    def test_b_bold_at_half_and_c_is_the_target_sum(self):
        self.assertEqual(t.cell_b(self.data(1), "checkoutservice"), "**300/600 (50%)**")
        self.assertEqual(t.cell_c(self.data(1), "checkoutservice"), "42")
        self.assertEqual(t.cell_c(self.data(1), "adservice"), "0")

    def test_cpu_fraction_uses_quota_times_replicas(self):
        d = {"cpu": {"checkoutservice": {"mean": 800.0, "max": 1600.0, "quota": 1600}}}
        self.assertEqual(t.cell_cpu_frac(d, "checkoutservice"), "0.50 / 1.00")
        self.assertEqual(t.cell_cpu_frac({"cpu": {}}, "checkoutservice"), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python experiments/test_s2_probe_tables.py -v`
Expected: `ModuleNotFoundError: No module named 's2_probe_tables'`.

- [ ] **Step 3: Implement**

Create `experiments/s2_probe_tables.py`:

```python
"""Per-service comparison tables for a both-off S2 series (the layout of
Guides and Info/2026-10-04-s2-latch-probe-abc.md).

CLI:
  python experiments/s2_probe_tables.py --out <file.md> --block "A=128,129,130" --block "B=138,139"
Runs are read from experiments/results/new vms/baseline_no_topfull_sustained_overload_run<N>/.
(a)/(b)/(c) come from s2_both_off_abc.score_run; the other tables come from service_inbound.csv,
resource_usage.csv, service_capacity.json, topfull_detect.csv and the five Locust CSVs.
Locust rows drop the first 30 and the last 5; inbound rows drop the last 5 polls.
"""
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s2_both_off_abc as abc  # noqa: E402
import steal_stat  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "experiments" / "results" / "new vms"
SERVICES = ["frontend", "checkoutservice", "recommendationservice", "paymentservice",
            "emailservice", "productcatalogservice", "cartservice", "currencyservice",
            "shippingservice", "adservice", "redis-cart"]
UNCONTROLLED = {"frontend", "redis-cart"}
APIS = ["getproduct", "postcheckout", "getcart", "postcart", "emptycart"]


def run_dir(n: int) -> Path:
    return ROOT / f"baseline_no_topfull_sustained_overload_run{n}"


def _rows(path: Path) -> list:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _ts(s: str) -> float:
    return steal_stat._utc(s)


def inbound_metrics(rows: list) -> dict:
    """Cumulative Envoy inbound counters for one service, time-sorted. Last 5 polls dropped."""
    rows = rows[:-5]
    if len(rows) < 2:
        return {}
    a, b = rows[0], rows[-1]
    dt = _ts(b["timestamp"]) - _ts(a["timestamp"])
    dtotal = float(b["total"]) - float(a["total"])
    out = {"arrival": dtotal / dt if dt > 0 else None}
    if dtotal > 0:
        out["fail5xx"] = (float(b["5xx"]) - float(a["5xx"])) / dtotal
        out["reset"] = (float(b["resets"]) - float(a["resets"])) / dtotal
    dc = float(b["rq_time_count"]) - float(a["rq_time_count"])
    ds = float(b["rq_time_sum_ms"]) - float(a["rq_time_sum_ms"])
    if dc > 0:
        out["sojourn_ms"] = ds / dc
        try:
            le500 = json.loads(b["rq_time_buckets"])["500"] - json.loads(a["rq_time_buckets"])["500"]
            out["over500"] = max(0.0, 1.0 - le500 / dc)
        except (KeyError, ValueError, TypeError):
            pass
    return out


def locust_metrics(path: Path) -> dict:
    rows = _rows(path)[30:-5]
    if not rows:
        return {}
    rps = sum(float(r["RPS"]) for r in rows)
    fail = sum(float(r["Fail"]) for r in rows)
    return {"goodput": st.mean(float(r["Goodput"]) for r in rows),
            "fail": fail / rps if rps else None,
            "p95": st.mean(float(r["Latency95"]) for r in rows)}


def load(n: int) -> dict:
    d = run_dir(n)
    out = {"abc": abc.score_run(d), "inbound": {}, "cpu": {}, "util": {}, "locust": {}}
    by = defaultdict(list)
    for r in _rows(d / "service_inbound.csv"):
        by[r["service"]].append(r)
    for svc, rows in by.items():
        out["inbound"][svc] = inbound_metrics(rows)
    cap = json.loads((d / "service_capacity.json").read_text(encoding="utf-8"))
    cpu = defaultdict(list)
    for r in _rows(d / "resource_usage.csv"):
        cpu[r["service"]].append(float(r["cpu_millicores"]))
    for svc, vals in cpu.items():
        quota = None
        if svc in cap:
            quota = cap[svc]["cpu_limit_millicores"] * cap[svc]["replica_count"]
        out["cpu"][svc] = {"mean": st.mean(vals), "max": max(vals), "quota": quota}
    umax = defaultdict(float)
    for r in _rows(d / "topfull_detect.csv"):
        umax[r["service"]] = max(umax[r["service"]], float(r["utilization"]))
    out["util"] = dict(umax)
    for api in APIS:
        p = d / f"{api}.csv"
        if p.exists():
            out["locust"][api] = locust_metrics(p)
    return out


def _fmt(x, spec):
    return "" if x is None else format(x, spec)


def _bold(s, on):
    return f"**{s}**" if on else s


def cell_a(data, svc):
    v = data["abc"]["inbound"].get(svc)
    if not v:
        return ""
    return _bold(f"{v['streak']} / {v['high_samples']}", v["streak"] >= 30 and svc not in UNCONTROLLED)


def cell_b(data, svc):
    v = data["abc"]["overloaded"].get(svc)
    if not v:
        return ""
    return _bold(f"{v['overloaded_ticks']}/{v['ticks']} ({v['share']:.0%})", v["share"] >= 0.5)


def cell_c(data, svc):
    return str(data["abc"]["retry_by_target"].get(svc, 0))


def cell_cpu(data, svc):
    v = data["cpu"].get(svc)
    return "" if not v else f"{v['mean']:.0f} / {v['max']:.0f}"


def cell_cpu_frac(data, svc):
    v = data["cpu"].get(svc)
    if not v or not v["quota"]:
        return ""
    return f"{v['mean'] / v['quota']:.2f} / {v['max'] / v['quota']:.2f}"


def _inb(key, spec):
    return lambda data, svc: _fmt(data["inbound"].get(svc, {}).get(key), spec)


def cell_util(data, svc):
    return _fmt(data["util"].get(svc), ".2f")


# (title, per-service cell function). Locust tables are per API and handled separately.
SERVICE_TABLES = [
    ("(a) Inbound rejection streak / samples above 0.20", cell_a),
    ("(b) Detector overloaded ticks / ticks (share)", cell_b),
    ("(c) Outbound retry delta by target", cell_c),
    ("CPU mean / max (m, summed over replicas)", cell_cpu),
    ("Inbound arrival rate (req/s)", _inb("arrival", ".1f")),
    ("Inbound 5xx fraction", _inb("fail5xx", ".3f")),
    ("Inbound reset fraction", _inb("reset", ".3f")),
    ("Inbound sojourn (ms)", _inb("sojourn_ms", ".0f")),
    ("Share of inbound requests above 500 ms", _inb("over500", ".2f")),
    ("CPU use as a fraction of per-pod quota x replicas (mean / max)", cell_cpu_frac),
    ("Detector max utilization", cell_util),
]
LOCUST_TABLES = [("Locust goodput (req/s)", "goodput", ".1f"),
                 ("Locust fail rate (Fail / RPS)", "fail", ".3f"),
                 ("Locust P95 (ms)", "p95", ".0f")]


def _table(header, rows_spec, runs, data):
    lines = ["| " + " | ".join([header] + [f"run{n}" for n in runs]) + " |",
             "|" + "---|" * (len(runs) + 1)]
    for label, fn in rows_spec:
        lines.append("| " + " | ".join([label] + [fn(data[n]) for n in runs]) + " |")
    return "\n".join(lines)


def build(blocks: list) -> str:
    """blocks: [(name, [run numbers])]."""
    data = {n: load(n) for _, runs in blocks for n in runs}
    out = []
    for title, fn in SERVICE_TABLES:
        out.append(f"## {title}\n")
        for name, runs in blocks:
            out.append(f"### Block {name}\n")
            spec = [(svc + (" (not controlled)" if svc in UNCONTROLLED else ""),
                     (lambda d, s=svc, f=fn: f(d, s))) for svc in SERVICES]
            out.append(_table("Service", spec, runs, data) + "\n")
    for title, key, spec_fmt in LOCUST_TABLES:
        out.append(f"## {title}\n")
        for name, runs in blocks:
            out.append(f"### Block {name}\n")
            spec = [(api, (lambda d, a=api, k=key, f=spec_fmt: _fmt(d["locust"].get(a, {}).get(k), f)))
                    for api in APIS]
            out.append(_table("API", spec, runs, data) + "\n")
    out.append("## CPU steal % over the hold (hold % / worst 5 s interval)\n")
    for name, runs in blocks:
        out.append(f"### Block {name}\n")
        out.append("| Run | master | worker | load |\n|---|---|---|---|")
        for n in runs:
            row = steal_stat.md_row(f"run{n}", steal_stat.score_run(run_dir(n)))
            out.append(row)
        out.append("")
    return "\n".join(out)


def main(argv):
    blocks, out_path = [], None
    i = 1
    while i < len(argv):
        if argv[i] == "--out":
            out_path = argv[i + 1]
            i += 2
        elif argv[i] == "--block":
            name, runs = argv[i + 1].split("=")
            blocks.append((name, [int(x) for x in runs.split(",")]))
            i += 2
        else:
            print(__doc__)
            return 2
    if not blocks:
        print(__doc__)
        return 2
    text = build(blocks)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
        print(f"wrote {out_path} ({len(text)} chars)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run to verify pass, then try it on real folders**

```powershell
python experiments/test_s2_probe_tables.py -v
python experiments/s2_probe_tables.py --out .superpowers/latch/tables_smoke.md --block "A=111,112"
```

Expected: 6 tests OK; the second prints `wrote .superpowers/latch/tables_smoke.md (… chars)` (create `.superpowers/latch` first if it is missing). The steal table at the end of the file shows `n/a` for these two first-probe folders, which have no `state/steal_*` files. Open the file and confirm the (a) table for run112 shows `**145 / 538**` for recommendationservice.

- [ ] **Step 5: Save the scorecard script**

Create `.superpowers/latch/scorecard_v2.py` (this directory is never committed):

```python
"""Scorecard for the S2 latch probe v2 series. Saved by the plan to .superpowers/latch/scorecard_v2.py
(not committed). Run from the repo root:
  python .superpowers/latch/scorecard_v2.py                      # slots 128-147 from hold_order(20261004)
  python .superpowers/latch/scorecard_v2.py --extra 148=spawn10  # add an appended relaunch slot
  python .superpowers/latch/scorecard_v2.py --no-v2-order --extra 112=ck_rep2 --extra 119=ck_rep2   # any slots
Prints: per-hold rows, per-arm verdicts, control drift, steal by mode.
"""
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join("experiments"))
import s2_both_off_canon as canon  # noqa: E402
import s2_latch_probe as p  # noqa: E402
import steal_stat  # noqa: E402


def hold(slot, treatment, block):
    canon.ROOT = p.NEW_VMS
    d = p.NEW_VMS % slot
    if not os.path.isdir(d):
        return {"slot": slot, "treatment": treatment, "block": block, "missing": True}
    ok, notes = p.gate(slot, treatment)
    o = canon.score(slot)
    s = o["svc"]
    soj = p.sojourn_window(p.NEW_VMS, slot)
    try:
        steal = steal_stat.score_run(d)
    except Exception:  # folders without state/ or without service_inbound.csv
        steal = {n: {"hold_pct": None} for n in steal_stat.NODES}
    return {
        "slot": slot, "treatment": treatment, "block": block, "missing": False, "gate": ok,
        "notes": notes, "cls": p.classify(o), "blend": p.is_blend(o),
        "ck_streak": s.get("checkoutservice", {}).get("streak"),
        "ck_ov": s.get("checkoutservice", {}).get("ov"),
        "rc_streak": s.get("recommendationservice", {}).get("streak"),
        "rc_ov": s.get("recommendationservice", {}).get("ov"),
        "ret_rc": int(o["edges"].get(("frontend", "recommendationservice"), 0)),
        "ret_ck": int(o["edges"].get(("frontend", "checkoutservice"), 0)),
        "ck_sojourn": soj["mean_ms"], "over500": soj["share_over_500"],
        "steal": {n: steal[n]["hold_pct"] for n in steal_stat.NODES},
    }


def verdict(holds):
    scored = [h for h in holds if not h["missing"] and h["gate"]]
    if len(scored) < 2:
        return "incomplete"
    sticky = [h["cls"] == "sticky" for h in scored]
    if all(sticky):
        return "no effect seen"
    if not any(sticky):
        avoided = all((h["ck_streak"] or 0) < 30 for h in scored)
        return "moved" + (", latch avoided" if avoided else "")
    return "mixed"


def fmt(x, spec=".2f"):
    return "n/a" if x is None else format(x, spec)


def main(argv):
    extra, use_order = [], True
    i = 1
    while i < len(argv):
        if argv[i] == "--extra":
            slot, t = argv[i + 1].split("=")
            extra.append((int(slot), "R", t))
            i += 2
        elif argv[i] == "--no-v2-order":
            use_order = False
            i += 1
        else:
            print(__doc__)
            return 2
    plan = (p.hold_order(20261004, 128) if use_order else []) + extra
    holds = [hold(slot, t, b) for slot, b, t in plan]

    print("## Per hold")
    print("slot block treatment gate class blend ck(streak/ov) rc(streak/ov) ret_f>rc ret_f>ck "
          "ck_sojourn over500 steal(master/worker/load)")
    for h in holds:
        if h["missing"]:
            print(f"{h['slot']} {h['block']} {h['treatment']} NOT RUN")
            continue
        print(f"{h['slot']} {h['block']} {h['treatment']} {'PASS' if h['gate'] else 'FAIL'} {h['cls']} "
              f"{'blend' if h['blend'] else 'no-blend'} {h['ck_streak']}/{h['ck_ov']} "
              f"{h['rc_streak']}/{h['rc_ov']} {h['ret_rc']} {h['ret_ck']} {h['ck_sojourn']} {h['over500']} "
              + "/".join(fmt(h["steal"][n]) for n in steal_stat.NODES))

    print("\n## Per arm (honesty rule: moved = no hold sticky; no effect seen = every hold sticky; else mixed)")
    arms = sorted({h["treatment"] for h in holds if h["treatment"] != "control"})
    for a in arms:
        hs = [h for h in holds if h["treatment"] == a]
        cls = ", ".join(f"run{h['slot']} {'NOT RUN' if h['missing'] else h['cls'] + ('+blend' if h['blend'] else '')}"
                        for h in hs)
        blends = sum(1 for h in hs if not h["missing"] and h["blend"])
        print(f"{a}: {verdict(hs)} | {cls} | blends {blends}/{len(hs)}")

    print("\n## Controls (drift check: first vs last, then the trend)")
    ctl = [h for h in holds if h["treatment"] == "control" and not h["missing"]]
    for h in ctl:
        print(f"run{h['slot']} {h['block']} {h['cls']} {'blend' if h['blend'] else 'no-blend'} "
              f"ck {h['ck_streak']}/{h['ck_ov']} rc {h['rc_streak']}/{h['rc_ov']} ret_f>rc {h['ret_rc']} "
              f"steal worker {fmt(h['steal']['worker'])}")
    if len(ctl) >= 2:
        print(f"first control run{ctl[0]['slot']}: {ctl[0]['cls']}; last control run{ctl[-1]['slot']}: "
              f"{ctl[-1]['cls']}; sticky controls {sum(c['cls'] == 'sticky' for c in ctl)}/{len(ctl)}; "
              f"blend controls {sum(c['blend'] for c in ctl)}/{len(ctl)}")

    print("\n## Blend counts")
    done = [h for h in holds if not h["missing"] and h["gate"]]
    print(f"all scored holds: {sum(h['blend'] for h in done)}/{len(done)} blends, "
          f"{sum(h['cls'] == 'sticky' for h in done)}/{len(done)} sticky")

    print("\n## Steal by mode (hold % per node: min / mean / max)")
    for label, pick in (("sticky", lambda h: h["cls"] == "sticky"),
                        ("not sticky", lambda h: h["cls"] != "sticky")):
        grp = [h for h in done if pick(h)]
        for n in steal_stat.NODES:
            vals = [h["steal"][n] for h in grp if h["steal"][n] is not None]
            if vals:
                print(f"{label:11s} {n:6s} n={len(vals):2d} {min(vals):.2f} / {st.mean(vals):.2f} / {max(vals):.2f}")
            else:
                print(f"{label:11s} {n:6s} n=0 (no steal data)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

Smoke test (first-probe folders, so every gate shows FAIL for the new steal and pod-age checks and the verdict says `incomplete`; this only proves the script runs):

```powershell
python .superpowers/latch/scorecard_v2.py --no-v2-order --extra 112=ck_rep2 --extra 119=ck_rep2 --extra 111=control --extra 121=control
```

Expected: a `## Per hold` block with rows for runs 112, 119, 111, 121 (`released`, `released`, `released blend`, `released blend`), then the `## Per arm`, `## Controls`, `## Blend counts`, and `## Steal by mode` blocks without a traceback.

- [ ] **Step 6: Commit**

```powershell
git add experiments/s2_probe_tables.py experiments/test_s2_probe_tables.py
git commit -m "feat: all-services table generator for the latch probe guides"
```

---

### Task 6: Start the VMs and preflight

**Files:** none modified.

**Interfaces:**
- Consumes: Tasks 1–5 committed.
- Produces: three VMs RUNNING, SSH working, Paper-C1 base live (frontend HPA 4/4, catalog HPA 1/1, limits and sidecar request as in Global Constraints), slots 128–147 absent locally and on master, the steal capture proven on all three VMs, every arm fitting the worker.

- [ ] **Step 1: Start the VMs**

```powershell
gcloud config set project project-76deda76-55f1-42d2-abb
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: three rows `RUNNING` with a natIP. A `CPUS_ALL_REGIONS` error: stop and report. Do not resize. `gcloud auth list` must show `yoavnm98@gmail.com`, `idozacharia@gmail.com`, or `sagi151ps@gmail.com` active.

- [ ] **Step 2: Refresh SSH and confirm the API**

Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md) "Reconnect after VMs were stopped": `ssh-keygen -R` each old HostName and each new natIP, change only the three `HostName` lines in `~/.ssh/config`.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes"
```

Expected: `topfull-master` and `topfull-worker1` Ready. If the API is still starting, AwaitShell `block_until_ms: 60000` (no `shell_id`) and retry once.

- [ ] **Step 3: Confirm the slots are free**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ls /home/idozacharia/experiments/results | grep -E 'baseline_no_topfull_sustained_overload_run(12[89]|13[0-9]|14[0-9])$' || echo none"
Get-ChildItem "experiments\results\new vms","experiments\results\campaign_48\S2_sustained_overload" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'run(12[89]|13[0-9]|14[0-9])$' }
```

Expected: `none` and no local output. If anything exists, stop; shift every slot in the order table past the highest existing run and tell the user before continuing.

- [ ] **Step 4: Confirm the Paper-C1 base**

```powershell
cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s < experiments\latch_restore_check.sh"
```

Expected: ends with `RESTORE GATE PASS`. If an HPA or sidecar annotation drifted, re-apply only these, then rerun the check (do not reconcile paper CPU):

```powershell
cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s < experiments\latch_restore_fix.sh"
cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s < experiments\latch_restore_check.sh"
```

`latch_restore_fix.sh` pins both HPAs and sets the sidecar request to 100 m with no limit on every Deployment (a no-op where it already holds). A drifted CPU limit on checkout or recommendations is fixed by `.\experiments\latch_hold_pre.ps1 -Treatment control`. A drifted limit on any other service: stop and report, because Paper-C1 does not change those.

- [ ] **Step 5: Confirm the worker's allocatable CPU**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl describe node topfull-worker1 | grep -A6 -E '^Allocatable'"
```

Expected: `cpu: 16`. The fit ceiling (15600 m) assumes 16000 m allocatable. If it shows a different number, stop and report; the ceiling and the projected-requests table must be recomputed before any hold.

- [ ] **Step 6: Prove the steal capture on all three VMs**

```powershell
New-Item -ItemType Directory -Force ".superpowers/latch" | Out-Null
foreach ($h in "topfull-master","topfull-worker-1","topfull-load") {
  cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 $h bash -s -- start /tmp/latch_steal_smoke.txt < experiments\node_steal.sh"
}
```

AwaitShell, no `shell_id`, `block_until_ms: 20000`. Then:

```powershell
foreach ($h in "topfull-master","topfull-worker-1","topfull-load") {
  cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 $h bash -s -- stop /tmp/latch_steal_smoke.txt < experiments\node_steal.sh"
}
cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 bash -s -- snap < experiments\node_steal.sh > .superpowers\latch\snap_smoke.txt"
python -c "import sys; sys.path.insert(0,'experiments'); import steal_stat as s; a,b=s.parse_snapshot(open('.superpowers/latch/snap_smoke.txt',encoding='utf-8-sig').read()); print('worker steal % over the 10 s snapshot:', round(s.steal_pct(a,b),3))"
```

Expected: each `stop` prints `sampler stopped; N lines in /tmp/latch_steal_smoke.txt` with N >= 3 (a 20 s wait at 5 s steps); the python line prints a number (0.0 is fine). Clean up: `ssh -o BatchMode=yes topfull-master "rm -f /tmp/latch_steal_smoke.txt*"` and the same on `topfull-worker-1` and `topfull-load`. If N is 0 or the snapshot has no `proc_stat_b` section, the capture is broken: fix `node_steal.sh` (and its tests) before Task 7.

- [ ] **Step 7: Confirm the order and the fit once more on this machine**

```powershell
python experiments/s2_latch_probe.py order 20261004 128
foreach ($t in "ck_rep2_pc120","ck_cpu1000_pc120","recs_cpu1000") { python experiments/s2_latch_probe.py fit $t }
```

Expected: the Hold order table above and three `FITS` lines.

No commit in this task.

---

### Hold task pattern

Tasks 7–26 are the twenty holds, in slot order. Each has the same five steps with that hold's treatment and slot written into the commands:

1. `.\experiments\latch_hold_pre.ps1 -Treatment <T>` runs the fit gate, then sets the absolute starting state on master (checkout to 1 replica, patch both CPUs, roll both Deployments, scale checkout to the hold's count, wait, 20 s settle) and fails on a Pending pod or a worker over the CPU-request ceiling.
2. A 360 s cool-off via AwaitShell (no `shell_id`, `block_until_ms: 360000`).
3. `.\experiments\latch_hold_run.ps1 -Treatment <T> -Slot <N>` takes the t=0 snapshots and three steal snapshots, starts the 5 s steal samplers, launches the 600 s hold, stops the samplers and fetches their series, pulls, moves the folder, takes the end snapshots, copies `state/` into the run folder, then prints the gate result, the score line, and the steal line. Shell `block_until_ms: 1500000` (if the Shell tool backgrounds it, poll with AwaitShell). Exit 0 means the gate passed.
4. Treatment check from the gate output and the run folder.
5. Commit the run folder and the generated config (a failed gate uses the FAILED message from the Failure rules and the relaunch slot is appended at the end).

---
### Task 7: Hold run128 — `control` (block A, hold 1 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run128/`

**Interfaces:**
- Consumes: Task 6 done and the Paper-C1 base confirmed.
- Produces: the run128 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: nothing (plain base, `spawn_rate` 50). Projected worker CPU requests 14305 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `control: projected worker CPU requests 14305 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14305, and `PREP OK for control`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 128
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run128`, and a steal line starting `run128 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` in the run folder shows checkoutservice `cpu_limit_millicores` 800 with `replica_count` 1 and recommendationservice 1150.- The runner output lines for checkoutservice and recommendationservice read `already at …; skipping patch`. An applied patch instead: note it in the results guide.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run128" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run128 control"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run128 FAILED gate"` instead, and apply the Failure rules (append `control` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 8: Hold run129 — `spawn10` (block A, hold 2 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run129/`

**Interfaces:**
- Consumes: run128 committed (or recorded as FAILED). Whatever state run128 left on the cluster, `prep` below sets the absolute state.
- Produces: the run129 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: `spawn_rate` 50 -> 10. Projected worker CPU requests 14305 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment spawn10
```

Expected: `spawn10: projected worker CPU requests 14305 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14305, and `PREP OK for spawn10`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment spawn10 -Slot 129
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run129`, and a steal line starting `run129 steal master`.

- [ ] **Step 4: Treatment check**
- The runner output shows `export RATE=10`.- In `getproduct.csv` the user count reaches 275 within about 10–15 s of the first non-zero row (other holds take about 50 s). If not, the ramp change did not apply; say so in the results guide.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run129" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run129 spawn10"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run129 FAILED gate"` instead, and apply the Failure rules (append `spawn10` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 9: Hold run130 — `control` (block A, hold 3 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run130/`

**Interfaces:**
- Consumes: run129 committed (or recorded as FAILED). Whatever state run129 left on the cluster, `prep` below sets the absolute state.
- Produces: the run130 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: nothing (plain base, `spawn_rate` 50). Projected worker CPU requests 14305 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `control: projected worker CPU requests 14305 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14305, and `PREP OK for control`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 130
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run130`, and a steal line starting `run130 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` in the run folder shows checkoutservice `cpu_limit_millicores` 800 with `replica_count` 1 and recommendationservice 1150.- The runner output lines for checkoutservice and recommendationservice read `already at …; skipping patch`. An applied patch instead: note it in the results guide.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run130" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run130 control"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run130 FAILED gate"` instead, and apply the Failure rules (append `control` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 10: Hold run131 — `ck_cpu1000_pc120` (block A, hold 4 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run131/`

**Interfaces:**
- Consumes: run130 committed (or recorded as FAILED). Whatever state run130 left on the cluster, `prep` below sets the absolute state.
- Produces: the run131 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: checkoutservice 1000 m x 1, postcheckout 120. Projected worker CPU requests 14505 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_cpu1000_pc120
```

Expected: `ck_cpu1000_pc120: projected worker CPU requests 14505 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14505, and `PREP OK for ck_cpu1000_pc120`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_cpu1000_pc120 -Slot 131
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run131`, and a steal line starting `run131 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` shows checkoutservice `cpu_limit_millicores` 1000 with `replica_count` 1; the runner output reads `checkoutservice/server already at 1000m; skipping patch`.- Record the checkout 90–150 s sojourn from the score line.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run131" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run131 ck_cpu1000_pc120"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run131 FAILED gate"` instead, and apply the Failure rules (append `ck_cpu1000_pc120` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 11: Hold run132 — `recs_cpu1000_spawn10` (block A, hold 5 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run132/`

**Interfaces:**
- Consumes: run131 committed (or recorded as FAILED). Whatever state run131 left on the cluster, `prep` below sets the absolute state.
- Produces: the run132 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: recommendationservice 1000 m, `spawn_rate` 10. Projected worker CPU requests 14155 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment recs_cpu1000_spawn10
```

Expected: `recs_cpu1000_spawn10: projected worker CPU requests 14155 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14155, and `PREP OK for recs_cpu1000_spawn10`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment recs_cpu1000_spawn10 -Slot 132
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run132`, and a steal line starting `run132 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` shows recommendationservice `cpu_limit_millicores` 1000; the runner output reads `recommendationservice/server already at 1000m; skipping patch`.- The runner output shows `export RATE=10`; `getproduct.csv` reaches 275 users within about 10–15 s.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run132" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run132 recs_cpu1000_spawn10"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run132 FAILED gate"` instead, and apply the Failure rules (append `recs_cpu1000_spawn10` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 12: Hold run133 — `ck_rep2_pc120` (block A, hold 6 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run133/`

**Interfaces:**
- Consumes: run132 committed (or recorded as FAILED). Whatever state run132 left on the cluster, `prep` below sets the absolute state.
- Produces: the run133 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: checkoutservice 800 m x 2 replicas, postcheckout 90 -> 120. Projected worker CPU requests 15205 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_rep2_pc120
```

Expected: `ck_rep2_pc120: projected worker CPU requests 15205 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 15205, and `PREP OK for ck_rep2_pc120`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_rep2_pc120 -Slot 133
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run133`, and a steal line starting `run133 steal master`.

- [ ] **Step 4: Treatment check**
- `state/t0.txt` lists two checkoutservice pods, both under 20 minutes old, and `service_capacity.json` shows checkoutservice 800 with `replica_count` 2.- Record mean per-pod checkout CPU (sum of `cpu_millicores` for checkoutservice in `resource_usage.csv`, divided by 2, against 800 m) and the checkout 90–150 s sojourn from the score line.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run133" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run133 ck_rep2_pc120"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run133 FAILED gate"` instead, and apply the Failure rules (append `ck_rep2_pc120` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 13: Hold run134 — `recs_cpu1000` (block A, hold 7 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run134/`

**Interfaces:**
- Consumes: run133 committed (or recorded as FAILED). Whatever state run133 left on the cluster, `prep` below sets the absolute state.
- Produces: the run134 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: recommendationservice 1150 -> 1000 m. Projected worker CPU requests 14155 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment recs_cpu1000
```

Expected: `recs_cpu1000: projected worker CPU requests 14155 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14155, and `PREP OK for recs_cpu1000`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment recs_cpu1000 -Slot 134
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run134`, and a steal line starting `run134 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` shows recommendationservice `cpu_limit_millicores` 1000; the runner output reads `recommendationservice/server already at 1000m; skipping patch`.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run134" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run134 recs_cpu1000"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run134 FAILED gate"` instead, and apply the Failure rules (append `recs_cpu1000` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 14: Hold run135 — `control` (block A, hold 8 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run135/`

**Interfaces:**
- Consumes: run134 committed (or recorded as FAILED). Whatever state run134 left on the cluster, `prep` below sets the absolute state.
- Produces: the run135 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: nothing (plain base, `spawn_rate` 50). Projected worker CPU requests 14305 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `control: projected worker CPU requests 14305 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14305, and `PREP OK for control`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 135
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run135`, and a steal line starting `run135 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` in the run folder shows checkoutservice `cpu_limit_millicores` 800 with `replica_count` 1 and recommendationservice 1150.- The runner output lines for checkoutservice and recommendationservice read `already at …; skipping patch`. An applied patch instead: note it in the results guide.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run135" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run135 control"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run135 FAILED gate"` instead, and apply the Failure rules (append `control` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 15: Hold run136 — `ck_rep2_pc120_spawn10` (block A, hold 9 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run136/`

**Interfaces:**
- Consumes: run135 committed (or recorded as FAILED). Whatever state run135 left on the cluster, `prep` below sets the absolute state.
- Produces: the run136 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: checkoutservice 800 m x 2 replicas, postcheckout 120, `spawn_rate` 10. Projected worker CPU requests 15205 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_rep2_pc120_spawn10
```

Expected: `ck_rep2_pc120_spawn10: projected worker CPU requests 15205 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 15205, and `PREP OK for ck_rep2_pc120_spawn10`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_rep2_pc120_spawn10 -Slot 136
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run136`, and a steal line starting `run136 steal master`.

- [ ] **Step 4: Treatment check**
- `state/t0.txt` lists two checkoutservice pods, both under 20 minutes old, and `service_capacity.json` shows checkoutservice 800 with `replica_count` 2.- The runner output shows `export RATE=10`; `getproduct.csv` reaches 275 users within about 10–15 s.- Record mean per-pod checkout CPU (sum of `cpu_millicores` / 2 against 800 m) and the checkout 90–150 s sojourn.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run136" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run136 ck_rep2_pc120_spawn10"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run136 FAILED gate"` instead, and apply the Failure rules (append `ck_rep2_pc120_spawn10` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 16: Hold run137 — `ck_cpu1000_pc120_spawn10` (block A, hold 10 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run137/`

**Interfaces:**
- Consumes: run136 committed (or recorded as FAILED). Whatever state run136 left on the cluster, `prep` below sets the absolute state.
- Produces: the run137 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: checkoutservice 1000 m x 1, postcheckout 120, `spawn_rate` 10. Projected worker CPU requests 14505 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_cpu1000_pc120_spawn10
```

Expected: `ck_cpu1000_pc120_spawn10: projected worker CPU requests 14505 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14505, and `PREP OK for ck_cpu1000_pc120_spawn10`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_cpu1000_pc120_spawn10 -Slot 137
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run137`, and a steal line starting `run137 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` shows checkoutservice `cpu_limit_millicores` 1000 with `replica_count` 1; the runner output reads `checkoutservice/server already at 1000m; skipping patch`.- The runner output shows `export RATE=10`; `getproduct.csv` reaches 275 users within about 10–15 s.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run137" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run137 ck_cpu1000_pc120_spawn10"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run137 FAILED gate"` instead, and apply the Failure rules (append `ck_cpu1000_pc120_spawn10` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 17: Hold run138 — `spawn10` (block B, hold 11 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run138/`

**Interfaces:**
- Consumes: run137 committed (or recorded as FAILED). Whatever state run137 left on the cluster, `prep` below sets the absolute state.
- Produces: the run138 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: `spawn_rate` 50 -> 10. Projected worker CPU requests 14305 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment spawn10
```

Expected: `spawn10: projected worker CPU requests 14305 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14305, and `PREP OK for spawn10`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment spawn10 -Slot 138
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run138`, and a steal line starting `run138 steal master`.

- [ ] **Step 4: Treatment check**
- The runner output shows `export RATE=10`.- In `getproduct.csv` the user count reaches 275 within about 10–15 s of the first non-zero row (other holds take about 50 s). If not, the ramp change did not apply; say so in the results guide.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run138" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run138 spawn10"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run138 FAILED gate"` instead, and apply the Failure rules (append `spawn10` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 18: Hold run139 — `control` (block B, hold 12 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run139/`

**Interfaces:**
- Consumes: run138 committed (or recorded as FAILED). Whatever state run138 left on the cluster, `prep` below sets the absolute state.
- Produces: the run139 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: nothing (plain base, `spawn_rate` 50). Projected worker CPU requests 14305 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `control: projected worker CPU requests 14305 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14305, and `PREP OK for control`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 139
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run139`, and a steal line starting `run139 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` in the run folder shows checkoutservice `cpu_limit_millicores` 800 with `replica_count` 1 and recommendationservice 1150.- The runner output lines for checkoutservice and recommendationservice read `already at …; skipping patch`. An applied patch instead: note it in the results guide.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run139" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run139 control"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run139 FAILED gate"` instead, and apply the Failure rules (append `control` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 19: Hold run140 — `recs_cpu1000_spawn10` (block B, hold 13 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run140/`

**Interfaces:**
- Consumes: run139 committed (or recorded as FAILED). Whatever state run139 left on the cluster, `prep` below sets the absolute state.
- Produces: the run140 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: recommendationservice 1000 m, `spawn_rate` 10. Projected worker CPU requests 14155 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment recs_cpu1000_spawn10
```

Expected: `recs_cpu1000_spawn10: projected worker CPU requests 14155 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14155, and `PREP OK for recs_cpu1000_spawn10`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment recs_cpu1000_spawn10 -Slot 140
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run140`, and a steal line starting `run140 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` shows recommendationservice `cpu_limit_millicores` 1000; the runner output reads `recommendationservice/server already at 1000m; skipping patch`.- The runner output shows `export RATE=10`; `getproduct.csv` reaches 275 users within about 10–15 s.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run140" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run140 recs_cpu1000_spawn10"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run140 FAILED gate"` instead, and apply the Failure rules (append `recs_cpu1000_spawn10` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 20: Hold run141 — `ck_rep2_pc120_spawn10` (block B, hold 14 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run141/`

**Interfaces:**
- Consumes: run140 committed (or recorded as FAILED). Whatever state run140 left on the cluster, `prep` below sets the absolute state.
- Produces: the run141 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: checkoutservice 800 m x 2 replicas, postcheckout 120, `spawn_rate` 10. Projected worker CPU requests 15205 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_rep2_pc120_spawn10
```

Expected: `ck_rep2_pc120_spawn10: projected worker CPU requests 15205 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 15205, and `PREP OK for ck_rep2_pc120_spawn10`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_rep2_pc120_spawn10 -Slot 141
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run141`, and a steal line starting `run141 steal master`.

- [ ] **Step 4: Treatment check**
- `state/t0.txt` lists two checkoutservice pods, both under 20 minutes old, and `service_capacity.json` shows checkoutservice 800 with `replica_count` 2.- The runner output shows `export RATE=10`; `getproduct.csv` reaches 275 users within about 10–15 s.- Record mean per-pod checkout CPU (sum of `cpu_millicores` / 2 against 800 m) and the checkout 90–150 s sojourn.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run141" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run141 ck_rep2_pc120_spawn10"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run141 FAILED gate"` instead, and apply the Failure rules (append `ck_rep2_pc120_spawn10` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 21: Hold run142 — `ck_cpu1000_pc120` (block B, hold 15 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run142/`

**Interfaces:**
- Consumes: run141 committed (or recorded as FAILED). Whatever state run141 left on the cluster, `prep` below sets the absolute state.
- Produces: the run142 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: checkoutservice 1000 m x 1, postcheckout 120. Projected worker CPU requests 14505 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_cpu1000_pc120
```

Expected: `ck_cpu1000_pc120: projected worker CPU requests 14505 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14505, and `PREP OK for ck_cpu1000_pc120`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_cpu1000_pc120 -Slot 142
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run142`, and a steal line starting `run142 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` shows checkoutservice `cpu_limit_millicores` 1000 with `replica_count` 1; the runner output reads `checkoutservice/server already at 1000m; skipping patch`.- Record the checkout 90–150 s sojourn from the score line.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run142" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run142 ck_cpu1000_pc120"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run142 FAILED gate"` instead, and apply the Failure rules (append `ck_cpu1000_pc120` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 22: Hold run143 — `control` (block B, hold 16 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run143/`

**Interfaces:**
- Consumes: run142 committed (or recorded as FAILED). Whatever state run142 left on the cluster, `prep` below sets the absolute state.
- Produces: the run143 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: nothing (plain base, `spawn_rate` 50). Projected worker CPU requests 14305 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `control: projected worker CPU requests 14305 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14305, and `PREP OK for control`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 143
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run143`, and a steal line starting `run143 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` in the run folder shows checkoutservice `cpu_limit_millicores` 800 with `replica_count` 1 and recommendationservice 1150.- The runner output lines for checkoutservice and recommendationservice read `already at …; skipping patch`. An applied patch instead: note it in the results guide.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run143" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run143 control"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run143 FAILED gate"` instead, and apply the Failure rules (append `control` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 23: Hold run144 — `recs_cpu1000` (block B, hold 17 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run144/`

**Interfaces:**
- Consumes: run143 committed (or recorded as FAILED). Whatever state run143 left on the cluster, `prep` below sets the absolute state.
- Produces: the run144 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: recommendationservice 1150 -> 1000 m. Projected worker CPU requests 14155 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment recs_cpu1000
```

Expected: `recs_cpu1000: projected worker CPU requests 14155 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14155, and `PREP OK for recs_cpu1000`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment recs_cpu1000 -Slot 144
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run144`, and a steal line starting `run144 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` shows recommendationservice `cpu_limit_millicores` 1000; the runner output reads `recommendationservice/server already at 1000m; skipping patch`.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run144" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run144 recs_cpu1000"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run144 FAILED gate"` instead, and apply the Failure rules (append `recs_cpu1000` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 24: Hold run145 — `ck_cpu1000_pc120_spawn10` (block B, hold 18 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run145/`

**Interfaces:**
- Consumes: run144 committed (or recorded as FAILED). Whatever state run144 left on the cluster, `prep` below sets the absolute state.
- Produces: the run145 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: checkoutservice 1000 m x 1, postcheckout 120, `spawn_rate` 10. Projected worker CPU requests 14505 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_cpu1000_pc120_spawn10
```

Expected: `ck_cpu1000_pc120_spawn10: projected worker CPU requests 14505 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14505, and `PREP OK for ck_cpu1000_pc120_spawn10`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_cpu1000_pc120_spawn10 -Slot 145
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run145`, and a steal line starting `run145 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` shows checkoutservice `cpu_limit_millicores` 1000 with `replica_count` 1; the runner output reads `checkoutservice/server already at 1000m; skipping patch`.- The runner output shows `export RATE=10`; `getproduct.csv` reaches 275 users within about 10–15 s.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run145" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run145 ck_cpu1000_pc120_spawn10"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run145 FAILED gate"` instead, and apply the Failure rules (append `ck_cpu1000_pc120_spawn10` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 25: Hold run146 — `ck_rep2_pc120` (block B, hold 19 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run146/`

**Interfaces:**
- Consumes: run145 committed (or recorded as FAILED). Whatever state run145 left on the cluster, `prep` below sets the absolute state.
- Produces: the run146 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: checkoutservice 800 m x 2 replicas, postcheckout 90 -> 120. Projected worker CPU requests 15205 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_rep2_pc120
```

Expected: `ck_rep2_pc120: projected worker CPU requests 15205 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 15205, and `PREP OK for ck_rep2_pc120`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_rep2_pc120 -Slot 146
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run146`, and a steal line starting `run146 steal master`.

- [ ] **Step 4: Treatment check**
- `state/t0.txt` lists two checkoutservice pods, both under 20 minutes old, and `service_capacity.json` shows checkoutservice 800 with `replica_count` 2.- Record mean per-pod checkout CPU (sum of `cpu_millicores` for checkoutservice in `resource_usage.csv`, divided by 2, against 800 m) and the checkout 90–150 s sojourn from the score line.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run146" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run146 ck_rep2_pc120"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run146 FAILED gate"` instead, and apply the Failure rules (append `ck_rep2_pc120` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 26: Hold run147 — `control` (block B, hold 20 of 20)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run147/`

**Interfaces:**
- Consumes: run146 committed (or recorded as FAILED). Whatever state run146 left on the cluster, `prep` below sets the absolute state.
- Produces: the run147 folder with `state/` (nine steal files, `t0.txt`, `end.txt`). Change from base: nothing (plain base, `spawn_rate` 50). Projected worker CPU requests 14305 m (ceiling 15600 m).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `control: projected worker CPU requests 14305 m, ceiling 15600 m -> FITS`, the pod list, a `--- node_cpu_requests_m` value within about 150 m of 14305, and `PREP OK for control`. A bigger gap means something else is scheduled on the worker: report it before continuing. Pending pod or `OVER CEILING`: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 147
```

Shell `block_until_ms`: 1500000. Expected: the script ends with `PASS`, a score line starting `run147`, and a steal line starting `run147 steal master`.

- [ ] **Step 4: Treatment check**
- `service_capacity.json` in the run folder shows checkoutservice `cpu_limit_millicores` 800 with `replica_count` 1 and recommendationservice 1150.- The runner output lines for checkoutservice and recommendationservice read `already at …; skipping patch`. An applied patch instead: note it in the results guide.- The gate output lists `t0 pod ages s` for checkoutservice and recommendationservice, all under 1200, and no `WARN` for steal. A `WARN … steal … over the hold` line (above 2%) is not a failure; copy it into the results guide.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run147" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe v2 run147 control"
```

If the gate failed: `git commit -m "data: S2 latch probe v2 run147 FAILED gate"` instead, and apply the Failure rules (append `control` as the next unused slot at the end; a replica-mode failure or a Pending pod stops the series and you go to Task 28).

---
### Task 27: Relaunch slots (only if a hold failed a sampling-type gate)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run148/` (and run149 if a second hold failed)

**Interfaces:**
- Consumes: Task 26 finished and every failed hold committed as FAILED. Skip this task entirely if every hold passed.
- Produces: one appended hold per failed hold, same treatment, at most two.

- [ ] **Step 1: List what failed**

```powershell
python .superpowers/latch/scorecard_v2.py
```

Expected: rows with `FAIL` in the gate column are the failed holds. Each of them gets one appended hold with the same treatment. More than two failures: stop and report instead of appending.

- [ ] **Step 2: Run each appended hold with the standard five steps**

For the first failed treatment `<T>` and slot 148 (then the second failure's treatment with slot 149), run exactly the hold-task steps:

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment <T>
```

AwaitShell, no `shell_id`, `block_until_ms: 360000`, then:

```powershell
.\experiments\latch_hold_run.ps1 -Treatment <T> -Slot 148
```

Shell `block_until_ms`: 1500000. Commit with `git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run148" experiments/configs/scenario_2_latch_probe.yaml` and `git commit -m "data: S2 latch probe v2 run148 <T> (relaunch of runN)"`. These rows are in block `R` in every table and `--extra 148=<T>` is passed to `scorecard_v2.py` and a `R=148` block to `s2_probe_tables.py`.

---

### Task 28: Restore Paper-C1 and verify

**Files:** none modified.

**Interfaces:**
- Consumes: the last hold (or the stop point after a series-stopping failure).
- Produces: checkout 800 m x 1, recommendations 1150 m x 1, frontend HPA 4/4 with 4 ready, catalog HPA 1/1, sidecar request 100 m with no limit, no Pending pods, verified by `latch_restore_check.sh`.

- [ ] **Step 1: Restore**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `PREP OK for control` (checkout scaled to 1, CPU patched to 800 m / 1150 m if they were not already, both rolled).

- [ ] **Step 2: Verify with the gate**

```powershell
cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s < experiments\latch_restore_check.sh"
```

Expected: every line `ok`, ending `RESTORE GATE PASS`. Any `FAIL` line: run `latch_restore_fix.sh` and `latch_hold_pre.ps1 -Treatment control` (as in Task 6 Step 4), rerun the gate until it passes. Do not stop the VMs before it passes. Frontend HPA 4/4 and catalog HPA 1/1 are the state the earlier sessions left; paper CPU is not reconciled.

---

### Task 29: Results guide and ABC guide

**Files:**
- Create: `Guides and Info/2026-10-04-s2-latch-probe-v2-results.md`
- Create: `Guides and Info/2026-10-04-s2-latch-probe-v2-abc.md`
- Read for layout: `Guides and Info/2026-09-27-s2-cpu-variant-handoff.md` (the template), `Guides and Info/2026-10-04-s2-latch-probe-abc.md` (how the last probe did it), `Guides and Info/2026-10-03-s2-latch-probe-results.md`, `Guides and Info/2026-09-24-s2-both-off-abc-reading.md` (how (a)/(b)/(c) are read; leave it unchanged)

**Interfaces:**
- Consumes: all pulled folders `experiments/results/new vms/baseline_no_topfull_sustained_overload_run128` … `run147` (plus relaunch slots), `.superpowers/latch/scorecard_v2.py`, `experiments/s2_probe_tables.py`, `experiments/s2_both_off_abc.py`, `experiments/steal_stat.py`.
- Produces: two guides; the numbers in the results guide are copied from the scorecard output, not retyped from memory.

- [ ] **Step 1: Generate the scorecard**

```powershell
python .superpowers/latch/scorecard_v2.py > .superpowers/latch/scorecard_v2_out.txt
Get-Content .superpowers/latch/scorecard_v2_out.txt
```

Add `--extra 148=<T>` for every relaunch slot. Expected: `## Per hold` has 20 rows (plus relaunch rows), `## Per arm` has seven arms each with a verdict, `## Controls` has six controls, and `## Steal by mode` has six lines.

- [ ] **Step 2: Generate the all-services tables**

```powershell
python experiments/s2_probe_tables.py --out ".superpowers/latch/tables_v2.md" --block "A=128,129,130,131,132,133,134,135,136,137" --block "B=138,139,140,141,142,143,144,145,146,147"
```

Add a `--block "R=148"` argument for relaunch slots. Drop any slot whose gate failed from its block (a failed folder is omitted from the tables, as run116 was). Expected: `wrote .superpowers/latch/tables_v2.md`; open it and confirm the steal table at the end has numbers, not `n/a`, for every passed hold.

- [ ] **Step 3: Write the ABC guide**

Create `Guides and Info/2026-10-04-s2-latch-probe-v2-abc.md` in the layout of `2026-10-04-s2-latch-probe-abc.md` (that file is the standard; it copied the runs 35–38 layout). Section order:

1. Title `# S2 latch-probe v2, runs 128-147, all services`, then a setup paragraph: 600 s holds, both controllers off, `spawn_rate` 50 except the `*_spawn10` arms, Paper-C1, frontend pinned at 4, sidecar request 100 m with no CPU limit, one arm per hold from the run 89 mix (275 / 90 / 100 / 90 / 5), two shuffled blocks (seed 20261004), checkout and recommendations rolled before every hold. Name the holds that failed their gate and are omitted. Link `2026-09-24-s2-both-off-abc-reading.md` for how (a)/(b)/(c) are read and `2026-10-04-s2-latch-probe-v2-results.md` for the verdicts.
2. A hold index per block: Slot, Treatment, Change from the base, Counts (getproduct / postcheckout / getcart / postcart / emptycart). Copy the Treatment column from the "Hold order" table in this plan; counts are 275 / 90 / 100 / 90 / 5 except 275 / 120 / 100 / 90 / 5 for the four `*_pc120*` arms.
3. The tables from `.superpowers/latch/tables_v2.md`, pasted in this order, each split into Block A and Block B: (a), (b), (c), CPU mean / max, Locust goodput, Locust fail rate, Locust P95, inbound arrival rate, inbound 5xx fraction, inbound reset fraction, inbound sojourn, share of inbound requests above 500 ms, CPU use as a fraction of per-pod quota x replicas, detector max utilization, and the CPU steal table. Put the (a) / (b) bold rules as one sentence before the first table: **bold** in (a) is a streak of at least 30 on a controlled service (frontend and redis-cart stay plain); **bold** in (b) is an overloaded share of at least 0.5. For `ck_rep2_*` holds the CPU quota in the fraction table already uses limit x 2 because it is read from each run's `service_capacity.json`.
4. `## Per arm`: one paragraph per arm (seven) and one for control, each giving, for its holds, the pair `recommendations streak / overloaded ticks` and `checkout streak / overloaded ticks`, email and payment overloaded ticks, the frontend->recommendations and frontend->checkout retry totals, whether it is a blend, a near-miss (two of the three blend rows, the missing row at streak or overloaded ticks >= 5), or a miss, and the checkout hold-mean sojourn. Use the blend definition from Global Constraints.
5. `## Related` with links to the reading guide, the results guide, and the first probe's ABC guide.

- [ ] **Step 4: Write the results guide**

Create `Guides and Info/2026-10-04-s2-latch-probe-v2-results.md`. Mirror the template `2026-09-27-s2-cpu-variant-handoff.md` ("Where things stand" / "How to run" / "Post-run analysis" / "Read next") and the first probe's `2026-10-03-s2-latch-probe-results.md`. Sections, in this order, with every number copied from `.superpowers/latch/scorecard_v2_out.txt`:

1. **Setup** (one paragraph): base, arms, fresh-pod rule, steal capture (what was captured at t=0, during the hold every 5 s, and at the end), seed 20261004, any hold whose runner log showed an applied CPU patch, every failed hold with its gate message and the relaunch slot, and the clock time of the block boundary (end of run137).
2. **Per-hold scorecard**: one table, columns Slot, Block, Treatment, Class (sticky / released / other), Blend (yes/no), Ck streak/ov, Recs streak/ov, Email ov, Pay ov, Retries f>recs, Retries f>ck, Ck sojourn 90–150 s, Over-500, steal % over the hold for master / worker / load. A failed hold gets a blank row with its gate message.
3. **Per-arm verdicts**: for each of the seven arms, **moved** / **no effect seen** / **mixed** exactly as the honesty rule words it, plus "latch avoided" where it applies, plus per-pod checkout CPU for the replica arms (sum of checkout `cpu_millicores` divided by replicas, against 800 m) and the ramp length seen in `getproduct.csv` for the `*_spawn10` arms. Say in one sentence what each pair of related arms shows: `ck_rep2_pc120` vs `ck_rep2_pc120_spawn10`, `ck_cpu1000_pc120` vs `ck_cpu1000_pc120_spawn10`, `spawn10` vs control, `recs_cpu1000` vs `recs_cpu1000_spawn10`; and compare `ck_rep2_pc120` and `ck_cpu1000_pc120` with the first probe's `ck_rep2_pc120` (runs 115 and 123, both released blends) and `ck_cpu1000` (runs 113 and 122, both released, no blend), and `spawn10` with the first probe's (runs 109 and 120, both released blends).
4. **Control drift check**: the six controls (128, 130, 135, 139, 143, 147) as their own table with class, blend, checkout and recommendations streaks, `ret_f>rc`, and worker steal; then one sentence on first (128) versus last (147); the sticky and blend counts among the six; the same counts for the 7 earlier holds of this mix on the copy (3 blends, 4 sticky) and the 2 scored first-probe controls (2 blends); and whether the late-day holds (blocks' last three slots) are sticky more often than the early ones. If the first and last controls differ in class, say drift is possible and do not read any single arm as moved.
5. **Steal vs mode**: the `## Steal by mode` block from the scorecard (min / mean / max worker, master, load steal % for sticky vs not sticky holds), then one sentence: steal separates the modes only if the sticky range and the not-sticky range do not overlap on some node; otherwise say it does not. Report any hold above 2% steal and its class.
6. **Blend counts**: blends among all scored holds, among the 14 arm holds, among the six controls, per arm.
7. **What to replay next**: for each **moved** arm (and each with "latch avoided"), one line proposing three interleaved replays with three controls on Paper-C1; drop mixed and no-effect arms except to name them; if the controls drifted or steal separates the modes, say that comes first. Include the sample-size note that about eight holds of one configuration separate a 1-in-5 latch rate from a 3-in-5.
8. **Handoff** (mirrors the template's "Where things stand"): the VMs are TERMINATED (Task 32 confirms; write it after that step), the cluster was restored to Paper-C1 before the stop, `experiments/configs/scenario_2_baseline_no_topfull.yaml` points at the next free slot, run folders live in `experiments/results/new vms/`, and the list of folders not to overwrite (run85–run147 plus `_discarded`).
9. **Read next** links: the ABC guide, the first probe results, `2026-10-04-s2-checkout-latch.md`, `2026-10-03-s2-same-mix-replays-differ.md`.

- [ ] **Step 5: Check the guides**

```powershell
rg -n "TBD|TODO|XXX|<fill" "Guides and Info/2026-10-04-s2-latch-probe-v2-results.md" "Guides and Info/2026-10-04-s2-latch-probe-v2-abc.md"
```

Expected: no output. Spot-check three numbers in the results guide against the folders (for example `python experiments/s2_latch_probe.py score 128` and `python experiments/s2_latch_probe.py steal 128`).

No commit yet; Task 31 commits everything.

---

### Task 30: Bookkeeping (`AGENTS.md`, README, YAML slot)

**Files:**
- Modify: `AGENTS.md` (section 4 bullet, next-free-slot paragraph)
- Modify: `experiments/results/README.md`
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`

**Interfaces:**
- Consumes: the results guide (verdicts) and the highest slot used.
- Produces: the next free both-off slot recorded in the YAML and in `AGENTS.md`.

- [ ] **Step 1: Compute the next free slot**

```powershell
$used = Get-ChildItem "experiments/results/new vms" -Directory | Where-Object { $_.Name -match 'baseline_no_topfull_sustained_overload_run(\d+)$' } | ForEach-Object { [int]$Matches[1] }
$next = ($used | Measure-Object -Maximum).Maximum + 1
$next
```

Expected: 148 if no relaunch slot was used (149 or 150 otherwise). Use that number as `NEXT` below. (Runs under `campaign_48/` and `copy verification/` are all below 128.)

- [ ] **Step 2: Bump the YAML**

In `experiments/configs/scenario_2_baseline_no_topfull.yaml` change only these three fields (leave counts, `scale_constraints`, and `paper_cpu_reconcile: false` alone):

```yaml
run_number: NEXT
description: >
  Unused slot. Paper-C1 pin may still be live.
  Counts below are 275/85/100/90/5, already launched as run105-run107.
log_folder: baseline_no_topfull_sustained_overload_runNEXT
```

with `NEXT` replaced by the number from Step 1 in both places. Verify: `rg -n "run_number|log_folder" experiments/configs/scenario_2_baseline_no_topfull.yaml`.

- [ ] **Step 3: Update the results README**

In `experiments/results/README.md`, in the sentence that lists the `new vms/` runs ("… and latch-probe run108-run126 …"), extend it with: `, and latch-probe v2 run128-run147` (add the relaunch slots if used, and name any run whose gate failed). Keep every other sentence.

- [ ] **Step 4: Add the `AGENTS.md` bullet**

In `AGENTS.md` section 4, directly after the bullet that starts `- **S2 latch-probe series, runs 108–127 (2026-10-03 → 2026-10-04)**`, add one bullet in the same style (bold lead-in, facts, no filler). It must contain, taken from the results guide: the date, "twenty planned holds of the run 89 mix on Paper-C1, runs 128–147, seven arms twice (`ck_rep2_pc120`, `ck_rep2_pc120_spawn10`, `ck_cpu1000_pc120`, `ck_cpu1000_pc120_spawn10`, `spawn10`, `recs_cpu1000`, `recs_cpu1000_spawn10`) plus six controls, seed 20261004", the number that passed the gate and any failed slot, the per-arm verdicts (moved / no effect seen / mixed), the control drift result (first versus last control, sticky and blend counts), the steal result (does it separate the modes; any hold above 2%), the fresh-pod `prep` rule, the new files (`experiments/steal_stat.py`, `experiments/node_steal.sh`, `experiments/s2_probe_tables.py`, `experiments/latch_restore_check.sh`), links to `[2026-10-04-s2-latch-probe-v2-results.md](Guides%20and%20Info/2026-10-04-s2-latch-probe-v2-results.md)` and `[2026-10-04-s2-latch-probe-v2-abc.md](Guides%20and%20Info/2026-10-04-s2-latch-probe-v2-abc.md)`, "cluster returned to the Paper-C1 base (checkout 800 m × 1, recommendations 1150 m × 1, frontend HPA 4/4, catalog HPA 1/1)", "VMs **TERMINATED**", and "next free both-off slot **runNEXT**". Then update the "Next free YAML slots" paragraph: change the both-off slot from `run128` to `runNEXT` in both places it appears (`no-TopFull / both-off control YAML is **run128**` and `the next free slot is **run128**`) and add `latch-probe v2 run128–run147 are under experiments/results/new vms/` to that list. Find the places with `rg -n "run128" AGENTS.md`.

- [ ] **Step 5: Check**

```powershell
rg -n "run128" AGENTS.md experiments/results/README.md experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Expected: remaining `run128` mentions are only historical (the new bullet and the "latch-probe v2 run128–run147" list); no line still says run128 is the next free slot.

---

### Task 31: Commit everything and push

**Files:** everything produced by Tasks 1–30 that is not yet committed.

**Interfaces:**
- Consumes: Tasks 1–30.
- Produces: one docs commit and a pushed branch.

- [ ] **Step 1: Inspect `git status` first**

```powershell
git status --short
git branch --show-current
```

Expected: the new guides, `AGENTS.md`, README, YAML, the new plan file, and possibly leftovers from the earlier session (staged guides `Guides and Info/2026-10-04-s2-checkout-latch.md`, `Guides and Info/2026-10-04-s2-latch-probe-abc.md`, `AGENTS.md`, `Guides and Info/2026-10-03-s2-latch-probe-results.md`, plus the earlier plan files). Those earlier guides are the user's and belong in this commit. Anything else that looks unrelated (result folders from outside this series, scratch files, `s2_canon_*.json`, anything under `.superpowers/`) is not staged: leave it and name it in the summary.

- [ ] **Step 2: Stage specific paths only**

```powershell
git add "docs/superpowers/plans/2026-10-04-s2-latch-probe-v2-holds.md" "docs/superpowers/plans/2026-10-03-s2-latch-probe-holds.md"
git add "Guides and Info/2026-10-04-s2-latch-probe-v2-results.md" "Guides and Info/2026-10-04-s2-latch-probe-v2-abc.md" "Guides and Info/2026-10-04-s2-checkout-latch.md" "Guides and Info/2026-10-04-s2-latch-probe-abc.md" "Guides and Info/2026-10-03-s2-latch-probe-results.md"
git add AGENTS.md experiments/results/README.md experiments/configs/scenario_2_baseline_no_topfull.yaml
git add experiments/configs/scenario_2_latch_probe.yaml
git status --short
```

If a run folder is still uncommitted (a hold whose Step 5 was skipped), add it with `git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run<N>"`. Then check nothing sensitive or scratch is staged:

```powershell
git diff --cached --name-only | rg -i "id_rsa|id_ed25519|\.pem|\.key$|known_hosts|ssh/config|\.superpowers|s2_canon_"
```

Expected: no output. If anything prints, `git restore --staged <path>` it.

- [ ] **Step 3: Commit and push**

```powershell
git commit -m "docs: S2 latch probe v2 results (runs 128-147), ABC guide, AGENTS.md"
git push origin HEAD
git status -sb
```

Expected: one commit, the push succeeds, `git status -sb` shows no ahead/behind count. A rejected push (remote moved): `git pull --rebase origin <branch>`, resolve nothing by guessing (stop and report conflicts), push again.

---

### Task 32: Stop the VMs and verify

**Files:** none modified.

**Interfaces:**
- Consumes: Task 28's restore gate passed and Task 31's push succeeded.
- Produces: three VMs `TERMINATED` (stopped, not deleted). "Terminate" means stop here.

- [ ] **Step 1: Stop**

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
```

- [ ] **Step 2: Verify**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status)"
```

Expected: three rows, status `TERMINATED`. If any row is not `TERMINATED`, rerun the stop and check again; do not report done until all three are. Do not touch `networks-workshop`.

- [ ] **Step 3: Summary to the user**

The summary must contain: the class per hold in one table (slot, treatment, sticky / released / other, blend); the verdict per arm; the six-control result and the first-versus-last control drift sentence; whether steal separates the modes; the number of holds scored and any failed slots; the next free both-off slot; that the cluster was restored to Paper-C1 (Task 28 gate passed), the branch is pushed with `git rev-parse HEAD`, and the VMs are `TERMINATED`; and the file list from `git diff --name-status $(Get-Content .superpowers/latch/base_sha.txt) HEAD`, grouped as code and scripts, result folders (one line for run128–run147 naming any failed), guides and plans, `AGENTS.md` and README.

---

## Self-review

**Spec coverage.**
- Seven arms twice, plain controls, resets: Hold order table, Tasks 7–26 (14 arm holds, 6 controls); prep reset and fresh-pod rule in Global Constraints and Task 3's `_PREP`.
- Control count justified, one at the very start (128) and one at the very end (147), others spread across blocks: "Why six controls".
- Seeded shuffle with seed recorded (20261004), same arm never back to back (also same lever family), second hold of an arm in the second half (one per block): `hold_order`, `TestHoldOrder`, the table (computed by running the code; Task 3 Step 6 re-checks it).
- Prep before the cool-off, schedulability math per arm and a gate: Global Constraints, projected-requests column, `fit`, the ceiling check in `prep`, Pending stop rule.
- CPU steal at t=0 and end on master, worker, load, saved beside `t0.txt`, vmstat-style 10 s sample, SSH aliases only, TDD parser test, steal % per node per hold in the results table: Task 2, Task 4, the gate, the steal table in Task 5 / Task 29.
- Classifier 100000 -> 70000 in the old plan (applied) and in code/tests (code already correct; run101-like 76,303 test): Task 1 (first task).
- Results guide and ABC analysis mirroring the handoff template: Task 29 (per-hold scorecard, per-arm verdicts, control drift, steal vs mode, blend counts, replays next, handoff).
- `AGENTS.md` bullet (section 9 style), restore-to-Paper-C1 note, next-free slots: Task 30.
- Commit and push with specific paths, `git status` first, no keys: Task 31.
- Stop the VMs and verify `TERMINATED`; restore commands and gate before stopping: Tasks 28 and 32.
- 360 s cool-off, per-hold gates (rows >= 540, span about 690 s, replica pin, steal files), failure handling, YAML bumping rule: Global Constraints and Task 27 / 30.

**Placeholder scan.** The only deliberate fill-ins are in guide-writing steps (Tasks 29 and 30), where the content comes from the series' own output and each step names the exact source command and the required fields; the bookkeeping `NEXT` is computed in Task 30 Step 1. `<T>` in Task 27 is the treatment of the failed hold, named by the scorecard.

**Type consistency.** Treatment keys (`control`, `spawn10`, `ck_rep2_pc120`, `ck_rep2_pc120_spawn10`, `ck_cpu1000_pc120`, `ck_cpu1000_pc120_spawn10`, `recs_cpu1000`, `recs_cpu1000_spawn10`) are identical in `TREATMENTS`, `ARMS_V2`, the tests, the order table, the scripts' arguments, and every hold task. `steal_stat` function names used in `s2_latch_probe.py` (`score_run`, `NODES`, `format_line`) and `s2_probe_tables.py` (`score_run`, `md_row`, `_utc`) are defined in Task 2. State file names (`steal_t0_<node>.txt`, `steal_end_<node>.txt`, `steal_series_<node>.txt`; nodes `master`, `worker`, `load`) match in `node_steal.sh` usage, `latch_hold_run.ps1`, `steal_stat.score_run`, and the gate.

**Known limits.** Two holds per arm is a screen. Steal is read from the guest's `/proc/stat`; the clocks on the VMs are assumed NTP-synced (GCE default), so the hold window taken from `service_inbound.csv` timestamps lines up with the sampler's epochs within a second or two. The pod-age gate and the fresh-pod rule mean v2 holds are not comparable to the old-pod holds of runs 94–107. If the VMs must stop mid-series, note the stop time; pod ages reset anyway because every hold rolls its pods.
