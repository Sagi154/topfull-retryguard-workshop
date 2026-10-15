# S2 TopFull proxy logs and interleaved re-runs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Tasks 4–6 share one cluster. Run them in order in one session. Do not run two holds at once.

**Goal:** Keep the TopFull proxy's and RL loop's own output in every run folder, then re-run S2 TopFull-only and TopFull + burst in interleaved order, so we get clean holds for those two cells and can see why TopFull went blind.

**Architecture:** `run_scenario.py` starts the Go proxy and `deploy_rl.py` in tmux, and their output is lost when tmux is killed. Task 1 pipes each one through a small bash function that prefixes every line with a UTC stamp and appends it to `src/logs/topfull_proxy.log` and `src/logs/topfull_rl.log`. `collect_results` already copies `src/logs/.` into the run folder, so the pull picks them up with no other change. Task 2 adds `experiments/topfull_health.py`, which reads those two logs plus `topfull_throttle_collector.log` and reports whether the proxy's once-a-second monitor and the RL loop kept running. Tasks 3–6 run four S2 holds in the order TopFull-only, TopFull + burst, TopFull-only, TopFull + burst, then write the result.

**Tech Stack:** Python 3 (`unittest`, `re`, `dataclasses`), bash on `topfull-master`, PowerShell, `ssh`, `gcloud`. Existing tools: `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/bump_final_slot.py`, `experiments/s3s4_mode_matrix_gate.py`, `experiments/s2_cost_efficiency.py` (untracked, on disk).

## Why this plan exists

On the 2026-10-14 S2 matrix, three TopFull-on holds lost every read of the proxy's `/stats` and `/thresholds` part way through: `final_s2_tf_only_run2` from 12:08:35, `final_s2_both_burst_run1` from 12:58:40, `final_s2_both_burst_run2` from 13:15:30. `final_s2_rg_only_burst_run2` (TopFull RL off) also lost 45 s of reads from 12:48:05, so the proxy can stall without the RL loop running. In the KAIST code in `TopFull/`, `Detector.current_rps()` calls `requests.get(proxy_url + "/stats")` with no timeout, and both `deploy_rl.py`'s agent threads and `Detector.clustering()` call it. A stalled proxy can therefore freeze the RL loop. On `tf_only_run2`, Locust goodput fell from about 420 to about 310 req/s and master CPU from about 5.2 to about 3.9 cores in the minute of the first timeout. None of this can be confirmed today, because the proxy's and RL loop's output is not saved and `num_agent.csv` has no timestamps.

## Global Constraints

- Branch is `s2-topfull-proxy-logs`, created from `main` at `f636e7f1` in `c:\Users\Yoav\topfull-retryguard-workshop`. Work in that checkout. Do not merge. Do not push.
- The working tree has untracked analysis files (`Guides and Info/2026-10-15-s2-cost-efficiency*`, `experiments/s2_activation_analysis.py`, `experiments/s2_cost_efficiency.py`, `experiments/explore_out/**`, email drafts). Never `git add .` or `git add -A`. Add only the paths each commit step names.
- Do not change TopFull code (`TopFull/` submodule, or the copy on master). Do not add a timeout to `current_rps()`. This plan observes TopFull; it does not fix it.
- Do not change RetryGuard, the collectors, or any locked value. Locked RetryGuard values, already in the YAMLs: `retry_metric` `edge_rpr`, `sample_interval_seconds` 1, `interval_samples` 20, `rejection_threshold` 0.2, `retries_threshold` 0.4, `climb_rpr_1_to_2` 0.16, `climb_rpr_2_to_3` 0.32, `climb_interval_seconds` 10, `reenable_rejection` 0.25. Burst adds `burst_rpr` 2.0, `burst_window_seconds` 5, `burst_min_first_attempts` 20.
- S2 mix `275 / 90 / 100 / 90 / 5` (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50, 600 s, Paper-C1 on every row ([ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md)).
- Four holds, in this order: `s2_tf_only` run 3, `s2_both_burst` run 3, `s2_tf_only` run 4, `s2_both_burst` run 4. The only YAML edits are `run_number` and `log_folder`, and only through `python experiments/bump_final_slot.py <file>`, after that hold's pull and gate.
- A throttle **FLAG** (any `fetch failed` WARNING, or any API over 30 s with no fresh threshold or admitted read) is recorded. It does not fail the gate and does not trigger a replay. It is the thing this plan is trying to see, so the hold is kept and its proxy and RL logs are read.
- A failed collector gate keeps its folder. Replay that launch once from a copy under `experiments/configs/replays/` whose `log_folder` has an `_r2` suffix, then bump the canonical file once. Do not replay a second time.
- Cool-off is 120 s, starting when `run_scenario.py` exits. Pull, gate, and scoring happen during the wait.
- Paper-C1 replica pin for the whole campaign: frontend HPA min=max=4, `productcatalogservice-hpa` min=max=1, frontend sidecar `sidecar.istio.io/proxyCPU=90m`, `proxyCPULimit` unset. Restore at the end to frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset.
- SSH host aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`), Linux user `idozacharia`, project `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. Do not start anything in `networks-workshop`. Do not hardcode a public IP. Leave the three VMs RUNNING at the end.
- PowerShell eats backslashes inside `ssh "..."` JSON. Send `kubectl patch` and `kubectl annotate` as a bash script on stdin (`bash -s`).

## File Structure

- Modify: `experiments/run_scenario.py` — constants `TOPFULL_PROXY_LOG`, `TOPFULL_RL_LOG`, `STAMP_LINES_BASH`; the proxy and RL scripts in `_start_master_stack_after_kill`.
- Modify: `experiments/test_run_scenario.py` — new class `TestTopfullStdoutLogs`.
- Create: `experiments/topfull_health.py` — reads the two new logs and the throttle log, prints a short report.
- Create: `experiments/test_topfull_health.py`.
- Modify: `Guides and Info/METRICS-GATHERED.md` — two rows in "Also present, but not used as metrics".
- Modify: `AGENTS.md` §6 "After every hold" — one sentence on `topfull_health.py`; §4 Latest lines at the end.
- Modify during holds, slots only: `experiments/configs/final_configs/2/s2_tf_only.yaml`, `experiments/configs/final_configs/2/s2_both_burst.yaml`.
- Create during holds: `docs/superpowers/plans/2026-10-15-s2-topfull-proxy-logs-run-log.md`; four folders under `experiments/results/final results/`.
- Create at the end: `Guides and Info/2026-10-15-s2-topfull-proxy-reruns.md`.
- Modify at the end: `STATUS.md` (Done bullet, Next free slots), the top of `Guides and Info/2026-10-15-s2-controller-activation-analysis.md` (one pointer line, only if that file is tracked; it is created by the activation work and may still be untracked).

---

### Task 1: Save the proxy and RL output, stamped, into the run folder

**Files:**
- Modify: `experiments/run_scenario.py` (near the top-level constants, and `_start_master_stack_after_kill`, currently lines 801–867)
- Modify: `experiments/test_run_scenario.py` (add a class after `TestStartMasterStackTopfullRl`, currently ending at line 1586)
- Modify: `Guides and Info/METRICS-GATHERED.md` (table under "## Also present, but not used as metrics", currently lines 333–341)

**Interfaces:**
- Consumes: `write_remote_script(host: str, remote_path: str, content: str)`; `start_master_stack(cfg, proxy_ready=None)`; `cfg["infra"]["topfull_src_path"]`.
- Produces: `run_scenario.TOPFULL_PROXY_LOG == "topfull_proxy.log"`, `run_scenario.TOPFULL_RL_LOG == "topfull_rl.log"`, `run_scenario.STAMP_LINES_BASH` (a bash function named `stamp`). On master, every line the proxy and `deploy_rl.py` print lands in `{topfull_src_path}/logs/<name>` as `YYYY-MM-DDTHH:MM:SSZ  <original line>`. Task 2 parses exactly that shape.

- [ ] **Step 1: Write the failing tests**

Add this class to `experiments/test_run_scenario.py`, directly after `TestStartMasterStackTopfullRl`:

```python
class TestTopfullStdoutLogs(unittest.TestCase):
    """Proxy and deploy_rl output is appended, stamped, to src/logs."""

    SRC = "/home/idozacharia/TopFull/src"

    def setUp(self):
        patcher = mock.patch("run_scenario.ensure_proxy_uncapped")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _cfg(self, rl_enabled):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "topfull_src_path": self.SRC,
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
            },
            "topfull_rl": {"enabled": rl_enabled},
        }

    def _script(self, mock_write_script, remote_path):
        for c in mock_write_script.call_args_list:
            if c.args[1] == remote_path:
                return c.args[2]
        self.fail(f"{remote_path} was not written")

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    def test_proxy_output_goes_to_stamped_log(self, mock_ssh, mock_write_script, mock_wait):
        mock_ssh.return_value = mock.Mock(stdout="", returncode=0)
        run_scenario.start_master_stack(self._cfg(rl_enabled=False))
        script = self._script(mock_write_script, "/tmp/rg_proxy.sh")
        self.assertIn("export TZ=UTC\n", script)
        self.assertIn(run_scenario.STAMP_LINES_BASH, script)
        self.assertIn(
            f"go run proxy_online_boutique.go 2>&1 | stamp >> {self.SRC}/logs/topfull_proxy.log\n",
            script,
        )

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    def test_rl_output_goes_to_stamped_log(self, mock_ssh, mock_write_script, mock_wait):
        mock_ssh.return_value = mock.Mock(stdout="12345 python3 deploy_rl.py", returncode=0)
        run_scenario.start_master_stack(self._cfg(rl_enabled=True))
        script = self._script(mock_write_script, "/tmp/rg_rl.sh")
        self.assertIn("export TZ=UTC\n", script)
        self.assertIn(run_scenario.STAMP_LINES_BASH, script)
        self.assertIn(
            f"python3 -u deploy_rl.py 2>&1 | stamp >> {self.SRC}/logs/topfull_rl.log\n",
            script,
        )

    def test_stamp_function_shape(self):
        self.assertEqual(run_scenario.TOPFULL_PROXY_LOG, "topfull_proxy.log")
        self.assertEqual(run_scenario.TOPFULL_RL_LOG, "topfull_rl.log")
        self.assertIn("stamp() {", run_scenario.STAMP_LINES_BASH)
        self.assertIn("printf '%(%Y-%m-%dT%H:%M:%SZ)T  %s\\n' -1", run_scenario.STAMP_LINES_BASH)
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
python experiments/test_run_scenario.py TestTopfullStdoutLogs -v
```

Expected: 3 errors or failures, with `AttributeError: module 'run_scenario' has no attribute 'STAMP_LINES_BASH'` (or `TOPFULL_PROXY_LOG`).

- [ ] **Step 3: Write the implementation**

In `experiments/run_scenario.py`, add these constants next to the other module-level constants (above the first `def`):

```python
TOPFULL_PROXY_LOG = "topfull_proxy.log"
TOPFULL_RL_LOG = "topfull_rl.log"
# Bash builtin printf %()T, no fork per line. Needs bash >= 4.2 and TZ=UTC.
STAMP_LINES_BASH = (
    "stamp() { while IFS= read -r line; do "
    "printf '%(%Y-%m-%dT%H:%M:%SZ)T  %s\\n' -1 \"$line\"; done; }\n"
)
```

In `_start_master_stack_after_kill`, replace the `proxy_script` assignment with:

```python
    logs = f"{src}/logs"
    proxy_script = (
        "#!/bin/bash\n"
        "export TZ=UTC\n"
        + STAMP_LINES_BASH
        + f"cd {src}/proxy\n"
        f"go run proxy_online_boutique.go 2>&1 | stamp >> {logs}/{TOPFULL_PROXY_LOG}\n"
    )
```

and replace the `rl_script` assignment inside `if rl_enabled:` with:

```python
        rl_script = (
            "#!/bin/bash\n"
            "export TZ=UTC\n"
            + STAMP_LINES_BASH
            + f"source {venv}\n"
            f"cd {src}\n"
            f"python3 -u deploy_rl.py 2>&1 | stamp >> {logs}/{TOPFULL_RL_LOG}\n"
        )
```

Leave `mc_script`, `restart_proxy`, the tmux commands, and the `pgrep -fa deploy_rl.py` check unchanged. `>>` matters: `restart_proxy` re-runs `/tmp/rg_proxy.sh`, and the log must keep the first proxy's lines. `clear_logs` runs before the proxy starts, so each hold starts with an empty file. `apply_threshold_proxy` finds the proxy with `ps -ef | grep /exe/proxy | grep go-build`, which still matches the compiled child of `go run`, not the bash pipeline.

- [ ] **Step 4: Run the tests to verify they pass**

```powershell
python experiments/test_run_scenario.py TestTopfullStdoutLogs -v
python experiments/test_run_scenario.py
python experiments/test_run_scenario_proxy_guard.py
```

Expected: the three new tests `ok`; both full modules `OK`, exit code 0. `TestStartMasterStackTopfullRl` still passes, since the script paths and tmux session names did not change.

- [ ] **Step 5: Document the two files**

In `Guides and Info/METRICS-GATHERED.md`, in the table under "## Also present, but not used as metrics", insert these two rows directly after the `num_agent.csv` row:

```markdown
| `topfull_proxy.log` | Go proxy stdout and stderr. Each line starts with a UTC second stamp. `-------------------------` and one `<api>: <rps>` line per API come once a second from the proxy's own monitor. `Apply threshold to <api> : <cap>` appears when the RL loop sets a cap (Go prints the cap as `+1.230000e+002`) | Holds from 2026-10-15 on. Diagnostics only: read with `python experiments/topfull_health.py <run_dir>` |
| `topfull_rl.log` | `deploy_rl.py` stdout and stderr, same stamp. Ray startup, then the detector's CPU dict and overloaded list about every 2 s, and agent lines (`[...] running`, `All APIs clean`, `ttl done`) | TopFull-on holds from 2026-10-15 on. Diagnostics only. `num_agent.csv` has no timestamps; this log is the RL loop's clock |
```

- [ ] **Step 6: Commit**

```powershell
git add experiments/run_scenario.py experiments/test_run_scenario.py "Guides and Info/METRICS-GATHERED.md" docs/superpowers/plans/2026-10-15-s2-topfull-proxy-logs.md
git commit -m @"
Keep the TopFull proxy and RL output in every run folder.

Both now append to src/logs with a UTC stamp per line, so a stalled proxy or RL loop can be dated.
"@
```

---

### Task 2: `topfull_health.py` — did the proxy and RL loop keep running?

**Files:**
- Create: `experiments/topfull_health.py`
- Create: `experiments/test_topfull_health.py`
- Modify: `AGENTS.md` §6, the paragraph that starts `**After every hold: check throttle data quality.**`

**Interfaces:**
- Consumes: the log shape from Task 1 (`YYYY-MM-DDTHH:MM:SSZ  <line>`); `topfull_throttle_collector.log` lines (`2026-10-14T12:08:35Z  WARNING  thresholds fetch failed: timed out`, last line `... SHUTDOWN ...` or `... EXIT`).
- Produces: `topfull_health.report(run_dir: Path) -> str` and a CLI `python experiments/topfull_health.py <run_dir> [<run_dir> ...]`. Report lines start with `throttle:`, `proxy:`, `rl:`. Yes/no fields: `tick_gap_over_5s`, `rl_silent_over_30s`. Task 4 records those fields in the run log.

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_topfull_health.py`:

```python
"""Tests for topfull_health.py. Run: python experiments/test_topfull_health.py"""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_health

TICK = "-------------------------"


def ts(hms: str) -> datetime:
    return datetime.strptime(f"2026-10-14T{hms}Z", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def write(path: Path, rows: list[tuple[str, str]]) -> None:
    path.write_text("".join(f"2026-10-14T{hms}Z  {text}\n" for hms, text in rows), encoding="utf-8")


class TestParsing(unittest.TestCase):
    def test_read_stamped_skips_unstamped_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.log"
            p.write_text("garbage\n2026-10-14T12:00:01Z  hello world\n", encoding="utf-8")
            self.assertEqual(topfull_health.read_stamped(p), [(ts("12:00:01"), "hello world")])

    def test_longest_gap_counts_trailing_gap_to_end(self):
        gap = topfull_health.longest_gap([ts("12:00:00"), ts("12:00:01")], ts("12:00:31"))
        self.assertEqual(gap.seconds, 30)
        self.assertEqual(gap.start, ts("12:00:01"))

    def test_longest_gap_empty(self):
        self.assertEqual(topfull_health.longest_gap([], None).seconds, 0)


class TestReport(unittest.TestCase):
    def _hold(self, tmp: Path, *, proxy=True, rl=True):
        write(tmp / "topfull_throttle_collector.log", [
            ("12:00:00", "START  poll_interval=1s"),
            ("12:00:05", "WARNING  thresholds fetch failed: timed out"),
            ("12:00:20", "SHUTDOWN  signal=15"),
        ])
        if proxy:
            write(tmp / "topfull_proxy.log", [
                ("12:00:00", "Start"),
                ("12:00:01", TICK),
                ("12:00:02", TICK),
                ("12:00:03", "Apply threshold to  postcheckout  :  +7.000000e+001"),
                ("12:00:03", TICK),
                ("12:00:12", TICK),
            ])
        if rl:
            write(tmp / "topfull_rl.log", [
                ("12:00:01", "No overloaded services"),
                ("12:00:03", "['postcheckout'] running"),
            ])

    def test_report_on_a_new_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._hold(tmp)
            text = topfull_health.report(tmp)
        self.assertIn("throttle: first_fetch_failure=12:00:05Z end=12:00:20Z", text)
        self.assertIn("proxy: lines=6 ticks=4 longest_tick_gap_s=9 from 12:00:03Z tick_gap_over_5s=yes", text)
        self.assertIn("applies=1 last_apply=12:00:03Z", text)
        self.assertIn("rl: lines=2 longest_silence_s=17 from 12:00:03Z rl_silent_over_30s=no", text)

    def test_report_on_an_old_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._hold(tmp, proxy=False, rl=False)
            text = topfull_health.report(tmp)
        self.assertIn("proxy: topfull_proxy.log missing", text)
        self.assertIn("rl: topfull_rl.log missing", text)

    def test_cli_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._hold(Path(tmp))
            self.assertEqual(topfull_health.main([tmp]), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
python experiments/test_topfull_health.py -v
```

Expected: `ModuleNotFoundError: No module named 'topfull_health'`.

- [ ] **Step 3: Write the implementation**

Create `experiments/topfull_health.py`:

```python
"""Did TopFull's proxy and RL loop keep running through a hold?

    python experiments/topfull_health.py "<run_dir>" ["<run_dir>" ...]

Reads topfull_proxy.log and topfull_rl.log (stamped by run_scenario.py) and
topfull_throttle_collector.log. Holds pulled before 2026-10-15 have no proxy
or RL log; the report says "missing" for those.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PROXY_LOG = "topfull_proxy.log"
RL_LOG = "topfull_rl.log"
THROTTLE_LOG = "topfull_throttle_collector.log"
MONITOR_TICK = "-------------------------"
STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+(.*)$")
APPLY = re.compile(r"Apply threshold to\s+(\S+)\s+:\s+(\S+)")
PROXY_TICK_GAP_S = 5
RL_SILENCE_S = 30


def parse_ts(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def read_stamped(path: Path) -> list[tuple[datetime, str]]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = STAMP.match(line)
        if m:
            out.append((parse_ts(m.group(1)), m.group(2)))
    return out


@dataclass
class Gap:
    seconds: float
    start: datetime | None


def longest_gap(times: list[datetime], end: datetime | None) -> Gap:
    """Longest wait between consecutive times, including the wait from the last one to `end`."""
    points = sorted(times)
    if end is not None and points and end > points[-1]:
        points.append(end)
    best = Gap(0.0, None)
    for a, b in zip(points, points[1:]):
        seconds = (b - a).total_seconds()
        if seconds > best.seconds:
            best = Gap(seconds, a)
    return best


def _fmt(t: datetime | None) -> str:
    return t.strftime("%H:%M:%SZ") if t is not None else "none"


def _yes(flag: bool) -> str:
    return "yes" if flag else "no"


def throttle_times(run_dir: Path) -> tuple[datetime | None, datetime | None]:
    """(first `fetch failed` stamp, last stamp) of the throttle collector log."""
    path = run_dir / THROTTLE_LOG
    if not path.exists():
        return None, None
    entries = read_stamped(path)
    first_fail = next((t for t, text in entries if "fetch failed" in text), None)
    end = max((t for t, _ in entries), default=None)
    return first_fail, end


def proxy_line(run_dir: Path, end: datetime | None) -> str:
    path = run_dir / PROXY_LOG
    if not path.exists():
        return f"proxy: {PROXY_LOG} missing"
    entries = read_stamped(path)
    ticks = [t for t, text in entries if text.strip() == MONITOR_TICK]
    applies = [t for t, text in entries if APPLY.search(text)]
    gap = longest_gap(ticks, end)
    return (
        f"proxy: lines={len(entries)} ticks={len(ticks)} "
        f"longest_tick_gap_s={gap.seconds:.0f} from {_fmt(gap.start)} "
        f"tick_gap_over_{PROXY_TICK_GAP_S}s={_yes(gap.seconds > PROXY_TICK_GAP_S)} "
        f"applies={len(applies)} last_apply={_fmt(max(applies, default=None))}"
    )


def rl_line(run_dir: Path, end: datetime | None) -> str:
    path = run_dir / RL_LOG
    if not path.exists():
        return f"rl: {RL_LOG} missing"
    entries = read_stamped(path)
    gap = longest_gap([t for t, _ in entries], end)
    return (
        f"rl: lines={len(entries)} longest_silence_s={gap.seconds:.0f} from {_fmt(gap.start)} "
        f"rl_silent_over_{RL_SILENCE_S}s={_yes(gap.seconds > RL_SILENCE_S)}"
    )


def report(run_dir: Path) -> str:
    first_fail, end = throttle_times(run_dir)
    return "\n".join([
        f"TopFull health: {run_dir.name}",
        f"throttle: first_fetch_failure={_fmt(first_fail)} end={_fmt(end)}",
        proxy_line(run_dir, end),
        rl_line(run_dir, end),
    ])


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    for arg in argv:
        print(report(Path(arg)))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the tests to verify they pass**

```powershell
python experiments/test_topfull_health.py -v
```

Expected: 6 tests `ok`, exit code 0. In `test_report_on_a_new_hold`: proxy ticks at :01, :02, :03, :12 with end :20 give the longest gap 9 s from :03; RL lines at :01 and :03 with end :20 give 17 s from :03.

- [ ] **Step 5: Run it on an old hold**

```powershell
python experiments/topfull_health.py "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2"
```

Expected:

```
TopFull health: final_s2_tf_only_run2
throttle: first_fetch_failure=12:08:35Z end=12:13:11Z
proxy: topfull_proxy.log missing
rl: topfull_rl.log missing
```

- [ ] **Step 6: Point the after-hold check at it**

In `AGENTS.md` §6, at the end of the paragraph that starts `**After every hold: check throttle data quality.**`, append this sentence:

```markdown
On a TopFull-on hold, also run `python experiments/topfull_health.py "<run_dir>"`. Its `proxy:` line says whether the proxy's once-a-second monitor kept ticking and when the RL loop last set a cap; its `rl:` line gives the RL loop's longest silence. Holds before 2026-10-15 print `missing` for both.
```

- [ ] **Step 7: Commit**

```powershell
git add experiments/topfull_health.py experiments/test_topfull_health.py AGENTS.md
git commit -m @"
Add topfull_health.py to date a stalled TopFull proxy or RL loop.

It reads the stamped proxy and RL logs next to the throttle collector's first fetch failure.
"@
```

---

### Task 3: Bring the cluster up, check master's bash, pin replicas

**Files:** none.

**Interfaces:**
- Consumes: SSH aliases; project `project-76deda76-55f1-42d2-abb`.
- Produces: three VMs `RUNNING`, nodes `Ready`, frontend HPA 4/4, catalog HPA 1/1, sidecar `90m` with `proxyCPULimit` empty, `STAMP_OK` from master's bash, and no Locust or master writer alive. Task 4 assumes all of this.

- [ ] **Step 1: List and, if needed, start the VMs**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected names: `topfull-master`, `topfull-worker-1`, `topfull-load`. If any is `TERMINATED`:

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

For each old `HostName` in `~/.ssh/config` and each new public IP, run `ssh-keygen -R <ip>`, then set the three `HostName` lines to the new addresses. `User` stays `idozacharia`. Do not commit `~/.ssh/config`.

- [ ] **Step 2: Confirm SSH and an idle cluster**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-worker-1 "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-load "hostname; whoami"
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

Expected: hostname matches each alias, `whoami` is `idozacharia`, then `locust-clear` and `master-clear`. Any other process line means someone else is using the cluster. Stop the plan. Do not `pkill` it.

- [ ] **Step 3: Confirm the API server**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

Expected: both nodes `Ready`, Online Boutique pods `2/2`, VirtualServices present. Wait up to five minutes after a start. `connection to localhost:8080 refused` means a missing `~/.kube/config` (AGENTS.md §7), not a down API server.

- [ ] **Step 4: Check that master's bash runs the stamp function**

```powershell
@'
export TZ=UTC
stamp() { while IFS= read -r line; do printf '%(%Y-%m-%dT%H:%M:%SZ)T  %s\n' -1 "$line"; done; }
out=$(printf 'a\nb\n' | stamp)
echo "$out"
echo "$out" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z  b$' && echo STAMP_OK || echo STAMP_BAD
bash --version | head -1
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: two stamped lines ending in `a` and `b`, then `STAMP_OK`, then a bash version of 4.2 or later. `STAMP_BAD` means stop. Fix `STAMP_LINES_BASH` in Task 1 before any hold.

- [ ] **Step 5: Record whether master's TopFull calls `/stats` without a timeout**

This is for the write-up only. Do not edit these files.

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "grep -n 'requests.get' /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py"
```

Expected: the `current_rps` line reads `requests.get(url, proxies=proxies)` with no `timeout=`. Copy the output into the run log header in Task 4 Step 8.

- [ ] **Step 6: Pin replicas and the frontend sidecar**

```powershell
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":4,"maxReplicas":4}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":1}}'
kubectl patch deployment frontend -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"90m"}}}}}'
kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit-
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Wait for four frontend pods and one catalog pod at `2/2`:

```powershell
@'
set -e
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  fe=$(kubectl get pods -n default -l app=frontend --no-headers | awk '$2=="2/2" && $3=="Running"' | wc -l)
  cat=$(kubectl get pods -n default -l app=productcatalogservice --no-headers | awk '$2=="2/2" && $3=="Running"' | wc -l)
  echo "frontend_ready=$fe catalog_ready=$cat"
  if [ "$fe" -ge 4 ] && [ "$cat" -eq 1 ]; then exit 0; fi
  sleep 15
done
echo "PIN_NOT_READY"
exit 1
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: a final line with `frontend_ready=4 catalog_ready=1`. `PIN_NOT_READY` means stop.

---

### Task 4: Four interleaved S2 holds

**Files:**
- Modify, slots only: `experiments/configs/final_configs/2/s2_tf_only.yaml`, `experiments/configs/final_configs/2/s2_both_burst.yaml`
- Create: `docs/superpowers/plans/2026-10-15-s2-topfull-proxy-logs-run-log.md`
- Create during pulls: the four folders in the table

**Interfaces:**
- Consumes: Task 1's runner, Task 2's `topfull_health.py`, Task 3's pinned cluster. Both YAMLs start at `run_number: 3` (`log_folder: final_s2_tf_only_run3`, `final_s2_both_burst_run3`).
- Produces: four pulled folders, each with `topfull_proxy.log` and `topfull_rl.log`; both YAMLs at `run_number: 5`; four run-log lines.

| Hold | YAML | Gate kind | TF | Folder after pull | Bump print |
| --- | --- | --- | --- | --- | --- |
| 1 | `experiments/configs/final_configs/2/s2_tf_only.yaml` | `tf` | `on` | `experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run3` | `run 3 -> 4` |
| 2 | `experiments/configs/final_configs/2/s2_both_burst.yaml` | `burst20` | `on` | `experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run3` | `run 3 -> 4` |
| 3 | `experiments/configs/final_configs/2/s2_tf_only.yaml` | `tf` | `on` | `experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run4` | `run 4 -> 5` |
| 4 | `experiments/configs/final_configs/2/s2_both_burst.yaml` | `burst20` | `on` | `experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run4` | `run 4 -> 5` |

Repeat Steps 1–8 for each row. Command blocks show hold 1. On later rows, substitute the row's YAML, gate kind, and folder.

- [ ] **Step 0 (before hold 1 only): Confirm the starting slots and absent folders**

```powershell
Get-Content experiments/configs/final_configs/2/s2_tf_only.yaml | Select-String "^(run_number|log_folder):"
Get-Content experiments/configs/final_configs/2/s2_both_burst.yaml | Select-String "^(run_number|log_folder):"
foreach ($n in @(
  "S2_sustained_overload_normal/tf_only/final_s2_tf_only_run3",
  "S2_sustained_overload_normal/tf_only/final_s2_tf_only_run4",
  "S2_sustained_overload_burst/both/final_s2_both_burst_run3",
  "S2_sustained_overload_burst/both/final_s2_both_burst_run4")) {
  if (Test-Path "experiments/results/final results/$n") { "EXISTS $n" } else { "ABSENT $n" }
}
```

Expected: `run_number: 3` and `log_folder: final_s2_tf_only_run3`; `run_number: 3` and `log_folder: final_s2_both_burst_run3`; `ABSENT` four times. Anything else means stop.

- [ ] **Step 1: Stop leftover writers**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

Expected: `locust-clear` and `master-clear`. Anything else means repeat Step 1.

- [ ] **Step 3: Clear live logs and confirm they stay empty**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

Expected: `ls` prints nothing. A `topfull_proxy.log` or `topfull_rl.log` coming back means a stamp pipeline from an earlier hold is alive. Repeat Step 1.

- [ ] **Step 4: Run**

```powershell
python experiments/run_scenario.py experiments/configs/final_configs/2/s2_tf_only.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

About 12 minutes. A non-zero exit stops the campaign: do not pull, do not bump, do not start the next row.

- [ ] **Step 5: Pull, gate, health, bump**

```powershell
python experiments/pull_results.py experiments/configs/final_configs/2/s2_tf_only.yaml
$run = "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run3"
python experiments/s3s4_mode_matrix_gate.py $run tf on
python experiments/analysis_score.py $run
rg -c "fetch failed" "$run/topfull_throttle_collector.log"
python experiments/topfull_health.py $run
Get-Content "$run/topfull_proxy.log" -TotalCount 3
Get-Content "$run/topfull_rl.log" -Tail 3
```

Pass when all of these hold:

- `locust_rows` is 540–580.
- For `tf`: `start_missing=n/a` and no `retryguard.log`. For `burst20`: `start_missing=none`.
- `patch_fail=no`.
- `frontend_4` equals its denominator (at least 1). `catalog_1` equals its denominator (at least 1).
- TF `on`: `live5s_caps` is at least 1.
- No `missing=` line.
- `topfull_proxy.log` and `topfull_rl.log` exist and their first lines start with a `2026-` UTC stamp. `topfull_health.py` prints numbers on both the `proxy:` and `rl:` lines, not `missing`.

If hold 1 fails only the last check, stop the campaign. Task 1's change did not work on master. Do not run holds 2–4 until it is fixed.

Throttle: no `fetch failed` and no API over 30 s without a fresh read in the scorer's `Throttle data quality` table is `throttle clean`. Otherwise `throttle FLAG`. A flag does not fail the gate.

VirtualServices:

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value `3`, no route `timeout`.

On a pass, bump:

```powershell
python experiments/bump_final_slot.py experiments/configs/final_configs/2/s2_tf_only.yaml
```

Expected print: the row's `Bump print` column.

On a fail, keep the folder and do not bump yet. Copy the YAML that is still at the launched slot:

```powershell
New-Item -ItemType Directory -Force -Path experiments/configs/replays | Out-Null
Copy-Item experiments/configs/final_configs/2/s2_tf_only.yaml experiments/configs/replays/final_s2_tf_only_run3_r2.yaml
```

In the copy, change only `log_folder` to `final_s2_tf_only_run3_r2`. Run Steps 1–4 with the copy, pull and gate the `_r2` folder, then bump the canonical file once, whatever the replay's result. Do not replay a second time.

- [ ] **Step 6: If the hold is FLAGGED, read the proxy and RL logs at the first failure**

Take the `first_fetch_failure` time from `topfull_health.py` (for example `12:08:35Z`) and print 30 s either side of it:

```powershell
$t = "12:08:3"   # first 7 characters of first_fetch_failure, so the grep spans 10 s
rg -n "T$t" "$run/topfull_proxy.log" | Select-Object -First 40
rg -n "T$t" "$run/topfull_rl.log" | Select-Object -First 40
```

Write in the run-log line: whether proxy ticks continued after the failure (from `tick_gap_over_5s` and the printed lines), the `last_apply` time, and `rl_silent_over_30s` with its start time. Do not stop the campaign for a flag.

- [ ] **Step 7: Finish the 120 s cool-off**

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
```

Then Steps 1–3 before the next row. After hold 4, leave the remainder for Task 5.

- [ ] **Step 8: Append one line per launch**

Create `docs/superpowers/plans/2026-10-15-s2-topfull-proxy-logs-run-log.md` on hold 1:

```markdown
# S2 TopFull proxy logs — run log

One line per launch, including a failed launch and its single replay. Order: tf_only, both_burst, tf_only, both_burst.

Master `current_rps` call (Task 3 Step 5): <paste the grep output line>

`hold N | log_folder | PASS or INVALID | locust rows | note`
```

Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; users 275/90/100/90/5; tf or burst_rpr 2.0; TopFull on; toggles N (off N, up N, burst N) or n/a; frontend 4 on N/N; catalog_1=N/N; TF live5s_caps=N; throttle clean or throttle FLAG (N fetch warnings, first HH:MM:SS); proxy ticks=N tick_gap_over_5s=yes|no last_apply=HH:MM:SSZ; rl longest_silence_s=N from HH:MM:SSZ; VS attempts 3; START ok`

---

### Task 5: Restore the unpinned shape

**Files:** none.

**Interfaces:**
- Consumes: the cluster pinned in Task 3; a finished hold 4.
- Produces: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, frontend app `1150m`, checkout `800m`, catalog `800m`, email `120m`. VMs `RUNNING`.

- [ ] **Step 1: Wait out the cool-off and stop leftover writers**

If hold 4's `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder. Then run Task 4 Steps 1 and 2. Expected: `locust-clear` and `master-clear`.

- [ ] **Step 2: Restore HPA and the sidecar**

```powershell
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":4}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":2}}'
kubectl patch deployment frontend -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"100m"}}}}}'
kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit-
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
@'
kubectl get hpa frontend-hpa productcatalogservice-hpa -n default
kubectl get deployment frontend -n default -o jsonpath="{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPU}{\"\n\"}{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPULimit}{\"\n\"}"
kubectl get deployment frontend checkoutservice productcatalogservice emailservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.template.spec.containers[0].resources.limits.cpu}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, annotation `100m`, empty `proxyCPULimit` line, then `frontend 1150m`, `checkoutservice 800m`, `productcatalogservice 800m`, `emailservice 120m`.

- [ ] **Step 3: Leave the VMs RUNNING**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: all three `RUNNING`. Do not stop them.

---

### Task 6: Write the result, update STATUS and AGENTS, commit

**Files:**
- Create: `Guides and Info/2026-10-15-s2-topfull-proxy-reruns.md`
- Modify: `STATUS.md` (one Done bullet; the `final_configs/2/` Next free slots line)
- Modify: `AGENTS.md` §4 (replace the three Latest lines)
- Modify, only if tracked: `Guides and Info/2026-10-15-s2-controller-activation-analysis.md` (one pointer line under the title)

**Interfaces:**
- Consumes: the run log, the four folders, `topfull_health.py`, `analysis_score.py`, `s2_cost_efficiency.hold_metrics(directory: Path) -> dict`.
- Produces: one guide that answers the two questions below, and STATUS/AGENTS matching the new slots.

- [ ] **Step 1: Compute the numbers**

```powershell
python experiments/topfull_health.py `
  "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run3" `
  "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run3" `
  "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run4" `
  "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run4"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run1" `
  "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run3" `
  "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run4"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run3" `
  "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run4"
python -c @"
import sys
sys.path.insert(0, 'experiments')
from pathlib import Path
import s2_cost_efficiency as c
base = Path('experiments/results/final results')
rows = [
    ('tf_only', base / 'S2_sustained_overload_normal/tf_only', 'final_s2_tf_only', (1, 2, 3, 4)),
    ('both_burst', base / 'S2_sustained_overload_burst/both', 'final_s2_both_burst', (1, 2, 3, 4)),
    ('rg_only_burst', base / 'S2_sustained_overload_burst/rg_only', 'final_s2_rg_only_burst', (1, 2)),
]
print('| hold | goodput req/s | SLO-miss | P95 ms | retries per 1k good | app mc |')
print('| --- | ---: | ---: | ---: | ---: | ---: |')
for _, folder, stem, runs in rows:
    for r in runs:
        d = folder / f'{stem}_run{r}'
        m = c.hold_metrics(d)
        g, s, p, r95, cpu = (m[k] for k in ('goodput_rps', 'slo_miss', 'p95_ms', 'retries_per_1k_good', 'app_cpu_mc'))
        print(f'| {d.name} | {g:.0f} | {s:.3f} | {p:.0f} | {r95:.0f} | {cpu:.0f} |')
"@
```

If a replay `_r2` folder replaced a failed launch, use that path instead and say so in the guide.

- [ ] **Step 2: Write the guide**

Create `Guides and Info/2026-10-15-s2-topfull-proxy-reruns.md`. Do not type a number that is not in the Step 1 output, the run log, or a log line. Sections, in this order:

1. **Title and first paragraph: the answers.** (a) Did TopFull's proxy stop answering again on the four new holds, and when? (b) On each flagged hold, did the proxy's once-a-second monitor keep ticking, when did the RL loop last set a cap, and did the RL loop go silent? Say plainly which of these the logs show: the whole proxy froze (ticks stopped), only its admin answers stalled (ticks continued, RL silent), or the proxy was slow and TopFull kept working (ticks continued, RL kept applying caps).
2. **Setup.** Four holds, 600 s, mix 275 / 90 / 100 / 90 / 5, `spawn_rate` 50, Paper-C1, frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s, order tf_only, both_burst, tf_only, both_burst. The four folder paths. The master `current_rps` grep line from the run log.
3. **Health per hold.** Paste the four `topfull_health.py` reports, then a table: hold, throttle clean or FLAG, first fetch failure, proxy tick gap, last apply, RL longest silence.
4. **Goodput and cost.** Paste the Step 1 markdown table. Then one paragraph: which TopFull-only holds are clean (`run1` plus any of `run3`, `run4`), which TopFull + burst holds are clean, and the TopFull-only against TopFull + burst comparison on clean holds only. `rg_only_burst` rows are there as the burst-without-TopFull reference. Name every flagged hold and do not use its cap numbers.
5. **What this changes in the earlier S2 reading.** One paragraph per earlier claim in [2026-10-15-s2-controller-activation-analysis.md](2026-10-15-s2-controller-activation-analysis.md) conclusions 3 and 5 that the new holds confirm or contradict.
6. **What is still open.** If a cell still has fewer than two clean holds, say so and give the next free slot (the YAMLs are now at run 5).
7. **Related.** This plan, the run log, [METRICS-GATHERED.md](METRICS-GATHERED.md), [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md), [2026-10-14-s2-mode-matrix-abc.md](2026-10-14-s2-mode-matrix-abc.md).

If `Guides and Info/2026-10-15-s2-controller-activation-analysis.md` is tracked (`git ls-files --error-unmatch "Guides and Info/2026-10-15-s2-controller-activation-analysis.md"` exits 0), add this line directly under its title:

```markdown
**Follow-up:** the TopFull blind holds were re-run with the proxy and RL logs saved; see [2026-10-15-s2-topfull-proxy-reruns.md](2026-10-15-s2-topfull-proxy-reruns.md).
```

- [ ] **Step 3: Confirm the slots**

```powershell
python -c @"
import yaml
from pathlib import Path
root = Path('experiments/configs/final_configs/2')
want = {'s2_tf_only.yaml': 5, 's2_both_burst.yaml': 5, 's2_rg_only_normal.yaml': 3, 's2_both_normal.yaml': 3, 's2_rg_only_burst.yaml': 3}
for name, n in want.items():
    cfg = yaml.safe_load((root / name).read_text(encoding='utf-8'))
    assert cfg['run_number'] == n, (name, cfg['run_number'])
    assert cfg['log_folder'].endswith(f'_run{n}'), (name, cfg['log_folder'])
print('slots ok: tf_only and both_burst at 5, the other three at 3')
"@
python experiments/test_bump_final_slot.py
python experiments/test_run_scenario.py
python experiments/test_topfull_health.py
```

Expected: the print line, then all three test modules `OK`.

- [ ] **Step 4: Update STATUS and AGENTS**

In `STATUS.md` Next free slots, replace this line:

```markdown
- `experiments/configs/final_configs/2/` — `s2_{rg_only_burst,rg_only_normal,tf_only,both_burst,both_normal}.yaml` — 3
```

with these two:

```markdown
- `experiments/configs/final_configs/2/` — `s2_{rg_only_burst,rg_only_normal,both_normal}.yaml` — 3
- `experiments/configs/final_configs/2/` — `s2_{tf_only,both_burst}.yaml` — 5
```

In the sentence above that list, replace `S2 stays at run 3.` with `S2 is at run 3, except `s2_tf_only.yaml` and `s2_both_burst.yaml` at run 5.`

Append one bullet under Done in `STATUS.md`: name the four `log_folder` values, PASS/INVALID and throttle FLAG counts from the run log, what `topfull_health.py` showed on each flagged hold, the guide and run-log paths, that the runner now saves `topfull_proxy.log` and `topfull_rl.log`, that the cluster was restored, and that the VMs were left RUNNING.

Replace the three Latest lines in `AGENTS.md` §4 (the current three bullets start `**S1 and S3 mode matrix (2026-10-15).**`, `**20 PASS, 0 INVALID, 0 throttle FLAG.**`, `**Cluster restored.**`). Do not append a fourth. Move nothing else. The replacement is:

1. `**S2 TopFull re-runs (2026-10-15).**` Branch `s2-topfull-proxy-logs` from `f636e7f1`. Four holds in order `final_s2_tf_only_run3`, `final_s2_both_burst_run3`, `final_s2_tf_only_run4`, `final_s2_both_burst_run4`. The runner now saves `topfull_proxy.log` and `topfull_rl.log`; read them with `experiments/topfull_health.py`. Next free slot for `s2_tf_only` and `s2_both_burst` is run 5.
2. PASS, INVALID, and throttle FLAG counts from the run log, the one-sentence answer from the guide's first paragraph, and the guide path `Guides and Info/2026-10-15-s2-topfull-proxy-reruns.md`.
3. The restored cluster (frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m) and the three VMs left RUNNING.

- [ ] **Step 5: Commit**

```powershell
git add experiments/configs/final_configs/2/s2_tf_only.yaml experiments/configs/final_configs/2/s2_both_burst.yaml docs/superpowers/plans/2026-10-15-s2-topfull-proxy-logs-run-log.md "Guides and Info/2026-10-15-s2-topfull-proxy-reruns.md" STATUS.md AGENTS.md
git add -- "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run3" "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run4" "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run3" "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run4"
git ls-files --error-unmatch "Guides and Info/2026-10-15-s2-controller-activation-analysis.md" 2>$null; if ($LASTEXITCODE -eq 0) { git add "Guides and Info/2026-10-15-s2-controller-activation-analysis.md" }
git commit -m @"
Re-run S2 TopFull-only and TopFull plus burst with the proxy logs saved.

Four interleaved holds, and a guide on whether the proxy or the RL loop stalled.
"@
git status --short -- experiments/configs STATUS.md AGENTS.md docs "experiments/results/final results/S2_sustained_overload_normal/tf_only" "experiments/results/final results/S2_sustained_overload_burst/both"
git branch --show-current
```

Expected: no lines from `git status` for those paths (the untracked analysis files elsewhere stay untracked), and branch `s2-topfull-proxy-logs`. If a replay YAML or `_r2` folder exists, `git add` it as well. Do not push.
