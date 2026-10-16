# Proxy FD Limit and RL-Stall Flag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the TopFull Go proxy from running out of file descriptors, stop the TopFull RL loop from blocking forever on the proxy, put both causes into the run data, flag any hold where either happened, and give the user a decision list for the 11 holds that were materially damaged.

**Architecture:** (1) `run_scenario.py` raises the proxy's soft open-files limit to the hard limit in `/tmp/rg_proxy.sh` and, before Locust, reads `/proc/<proxy pid>/limits` and aborts if the limit is still low. (2) A new stdlib-only collector, `experiments/proxy_fd_collector.py`, writes `proxy_fds.csv` once a second. (3) A patch script, `experiments/patch_rl_timeout.py`, adds a request timeout and parseable `RL_*` log lines to the live copy of TopFull's `overload_detection.py` and `deploy_rl.py` on master; the runner refuses to start TopFull-on holds when the patch marker is missing. (4) `experiments/topfull_health.py` gets `assess()` and a separate `RL STALL` / `PROXY FD` verdict; `analysis_score.py` prints it as its own table. (5) A generator, `experiments/proxy_fd_decisions.py`, writes `Guides and Info/2026-10-16-proxy-fd-rerun-decisions.md`. Nothing is re-run in this plan except one verification hold.

**Tech Stack:** Python 3.14 (stdlib for the collector and patch script), pytest 9 running both `unittest.TestCase` classes and plain pytest functions, PyYAML, pandas (already used by `analysis_score.py`), bash on master, Windows PowerShell on the dev machine.

## Global Constraints

- Do not use `run_all_scenarios.py` (Phase 7 is closed; it is not a runner for anything here). Every hold goes through `python experiments/run_scenario.py <yaml>`.
- Always reach the VMs through the OpenSSH aliases `topfull-master`, `topfull-worker-1`, `topfull-load`. Never type a public IP. Connect as `idozacharia` (never `idoza` as `User`). Playbook: [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md).
- The VMs are **down** when this plan is written. Tasks 1–5 are offline. Task 6 starts the three VMs itself, refreshes SSH, and confirms the cluster is usable before it deploys anything. Task 7 runs only after Task 6's health check passed. Do not start the original VMs in `networks-workshop`; pass `--project=project-76deda76-55f1-42d2-abb` to every `gcloud` call. Do not stop the VMs unless the user asks.
- Never overwrite a results folder, on master or locally. Before any hold, read [STATUS.md](../../../STATUS.md) "Next free slots" and bump `run_number` and `log_folder` in that one YAML only. Never reuse August `run1–3` (S1–S4) or S5 `run1–2`.
- Cool-off between holds is **120 s**, started when `run_scenario.py` exits. After it, do the leftover-writer check in AGENTS.md §6 (which Task 2 updates to include the new collector) before launching.
- **No commits unless the user asks.** Every Commit step below is written out for the executor to run only on the user's say-so. Until then leave changes in the working tree.
- Do not edit, move, or reformat `docs/superpowers/plans/2026-10-15-throttle-flag-remediation.md`. Do not re-run any hold other than the one in Task 7. Re-runs of the 11 holds are the user's decision, after Task 7 passes.
- Existing files use LF. After every edit run `git diff --stat` and confirm only intended files changed. Do not write STATUS.md, a guide, or a script in a way that converts line endings.
- Run all Python from the repo root `C:\Users\sagi1\Projects\Workshop`. Tests: `python -m pytest <file> -v`.
- Do not modify the `TopFull/` submodule. The TopFull change in this plan is a patch applied to master's live copy (Task 3); the repo copy stays at upstream.
- No STATUS.md or AGENTS.md content is written before Task 8. Those two files are updated once, at the end (rule: `.cursor/rules/update-agents-and-status.mdc`).

## Prerequisites (from the 2026-10-15 remediation plan)

This plan runs **after** [2026-10-15-throttle-flag-remediation.md](2026-10-15-throttle-flag-remediation.md) is finished (its Tasks 1–10). It uses what that plan creates and does not redefine it. State of the disk when this plan was written (2026-10-16 00:45, tasks 1–7 of 10 in progress):

| Dependency | Source | State on disk at writing | Used by |
|---|---|---|---|
| `experiments/throttle_stale.py` with `STALE_GAP_S = 10.0` and `stale_stretches` | remediation Task 1 | exists | Task 5 (via `throttle_flags`) |
| `experiments/throttle_flags.py` with `scan(root) -> list[HoldFlag]`, `HoldFlag` (fields `path, scenario, mode, variant, name, topfull_on, flagged, warnings, first_warning, threshold_gap_s, admitted_gap_s, ...`), `name_pattern(name)`, `guide_note(h)`, `GUIDES_DIR`, `AUDIT_PATH`, and the `audit`, `status`, `guides` subcommands | remediation Tasks 5–7 | exists; the `rerun` subcommand is wired but returns 0 with no output until Task 8 | Tasks 4, 5 |
| `throttle_flags.py rerun` and `Guides and Info/2026-10-15-throttle-flag-rerun-decisions.md` (27 TopFull-on rows) | remediation Task 8 | pending | none. The new decision document in Task 5 is a **different, wider list** (it includes `rg_only` holds). Do not merge them |
| `analysis_score.THROTTLE_STALE_S = 10`, `throttle_quality(rows, log_path, topfull_on=True)`, `topfull_enabled(run_dir)`, `N/A: TopFull off` in the printed table | remediation Task 9 | **done** (the remediation plan finished 2026-10-16; `analysis_score.py` has `THROTTLE_STALE_S = 10`, `topfull_enabled`, and `throttle_quality(rows, log_path, topfull_on=True)`) | Tasks 4, 5 |
| Decision: a TopFull-off hold is `N/A: TopFull off` for the **throttle** flag | remediation "Decided" item 1 | decided; **partly superseded by this plan's Decided (f)**: it stays true for caps, but the hold is no longer reported as clean (`PROXY STALL SUSPECTED`, Task 4 Step 6a–6d) | Task 4 keeps the throttle flag as is and adds the second verdict |

**Gate: run these before Task 1.** Each must print what is shown; if one does not, the remediation plan is not finished and this plan must wait.

```powershell
python experiments/throttle_flags.py audit
```
Expected first line: `runs=146 flagged=27 topfull_on_flagged=27 topfull_off_flagged=0`.

```powershell
rg -n "^THROTTLE_STALE_S = 10|^def topfull_enabled|^def throttle_quality\(rows: list\[dict\], log_path: Path, topfull_on: bool = True\)" experiments/analysis_score.py
```
Expected: three matching lines.

```powershell
python -m pytest experiments/test_throttle_stale.py experiments/test_throttle_flags.py experiments/test_analysis_score.py experiments/test_topfull_health.py -q
```
Expected: all pass, no failures.

```powershell
Test-Path "Guides and Info/2026-10-15-throttle-flag-rerun-decisions.md"
```
Expected: `True`.

## Decided (user, 2026-10-16; do not reopen inside a task)

(a) Raise the proxy's open-files limit up to the hard limit in the proxy launch. (b) Add a flag for the RL-stall problem **and** address it. (c) The RL log carries what the flag needs. (d) An `rg_only` hold with a stalled proxy is **not harmless**. (e) Make a decision list for the 11 materially affected holds. (f) **Supersedes the remediation plan's "Decided" item 1 for labels (user, 2026-10-16):** a TopFull-off hold (`rg_only`, `both_off`) whose `topfull_throttle_collector.log` shows `fetch failed` warnings or a stale stretch over 10 s is **not** reported as `N/A: TopFull off` as if it were clean. Caps stay N/A (no cap to lose), the throttle flag count stays at TopFull-on only (27 holds), but a second verdict, `PROXY STALL SUSPECTED`, appears for it in the scorer's `Proxy and RL health` table and in a new `throttle_flags.py suspected` list. For holds with no proxy or descriptor log this is the only evidence of a proxy stall there is. It means "do not assume the hold's goodput, P95, rejection, and retry numbers are clean", not "re-run". Live count on 2026-10-16: 25 TopFull-off holds (the 25 `N/A` holds of the original audit) plus the 27 TopFull-on flags = 52.

## Corrections to the brief, recorded so the executor does not "fix" them back

1. **The RL main loop ticks every 2 s, not 1 s.** `deploy_rl.py` has `time.sleep(2)` at the top of its `while True:` loop; each per-API `Agent` thread sleeps `interval=1`. The heartbeat added in Task 3 is therefore one `RL_LOOP_START` line per 2 s.
2. **Two different flags, two different scopes.** `RL STALL` can only exist where an RL loop runs, so it is TopFull-on only. `PROXY FD` (descriptor exhaustion) hits every variant, because every Locust request goes through the Go proxy on `:8090`, including `rg_only` and `both_off`. The remediation plan's "TopFull-off is N/A" stays true for the **throttle** flag's cap handling (an `rg_only` hold has no cap to lose), but Decided (f) adds `PROXY STALL SUSPECTED` so that N/A is no longer read as "clean". It is **not** true for goodput, P95, rejection, and retry numbers. Task 4 removes every "stay valid" sentence the remediation plan wrote for that reason.
3. **Mechanism of the 1024 limit.** `go run proxy_online_boutique.go` compiles to `/tmp/go-build…/b001/exe/proxy_online_boutique` and `exec`s it; the child's `RLIMIT_NOFILE` is whatever the `go` process had, which is whatever the shell in `/tmp/rg_proxy.sh` had, which is whatever tmux had, which is whatever the SSH session had (soft 1024, hard 1048576). `ulimit -Sn` in the script, before `go run`, therefore reaches the proxy. Go 1.19+ raises its own soft limit at startup but restores the old one for children it starts. The proxy process was measured at soft 1024, which suggests master's Go predates that, but master's `go version` has not been read (Task 6 reads it). Either way the script change is correct.

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `experiments/run_scenario.py` | Modify | `proxy_nofile_bash`, `read_proxy_soft_limit`, `verify_proxy_nofile`, `verify_rl_patch`, `start_proxy_fd_collector`; kill/gate/stop lists; manifest key |
| `experiments/test_run_scenario.py` | Modify | Script-text test; collector wiring tests; three existing `setUp`s patch the new verifier |
| `experiments/test_run_scenario_proxy_guard.py` | Modify | Tests for the limit reader and verifier (existing injectable-ssh pattern) |
| `experiments/proxy_fd_collector.py` | Create | Samples the proxy's open fd count and soft limit from `/proc` once a second into `proxy_fds.csv` |
| `experiments/test_proxy_fd_collector.py` | Create | Tests on a fake `/proc` tree |
| `experiments/patch_rl_timeout.py` | Create | Idempotent patch of master's `overload_detection.py` and `deploy_rl.py` (timeout, skip-on-timeout, `RL_*` log lines) |
| `experiments/test_patch_rl_timeout.py` | Create | Applies the patch to temp copies of the upstream files in `TopFull/` |
| `Guides and Info/TOPFULL-UPSTREAM-DEVIATIONS.md` | Create | The one documented deviation from upstream TopFull, with the open decision |
| `experiments/topfull_health.py` | Modify | `Health`, `assess()`, `RL_EVENT` parsing, `health:` line in `report()` |
| `experiments/test_topfull_health.py` | Modify | Tests for `assess()` |
| `experiments/analysis_score.py` | Modify | `proxy_rl_health` in `score_run`; `## Proxy and RL health` table in `render` |
| `experiments/test_analysis_score.py` | Modify | Test for the table |
| `experiments/throttle_flags.py` | Modify | `guide_note` stops saying the four numbers "stay valid" |
| `experiments/test_throttle_flags.py` | Modify | Follows the `guide_note` wording |
| `experiments/retire_stay_valid.py` | Create | One-shot rewrite of the "stay valid / remain valid" sentences in `Guides and Info/*.md` |
| `experiments/test_retire_stay_valid.py` | Create | Tests for it |
| `experiments/proxy_fd_decisions.py` | Create | Generates the decision document |
| `experiments/test_proxy_fd_decisions.py` | Create | Tests on a synthetic tree |
| `Guides and Info/2026-10-16-proxy-fd-rerun-decisions.md` | Create (generated) | The decision list for the user |
| `AGENTS.md`, `Guides and Info/METRICS-GATHERED.md`, `Guides and Info/ANALYSIS-TEMPLATE.md` | Modify | New file rows, new after-hold check, corrected validity wording |
| `STATUS.md` | Modify (Task 8 only) | One Done bullet; Next free slots if a YAML moved |

## Background the executor needs

- **Where TopFull lives.** The repo's `TopFull/` is the unmodified upstream submodule (`https://github.com/kaist-ina/TopFull`). Its `overload_detection.py` and `deploy_rl.py` hard-code `/home/topfull-master/...`. The live copy that holds actually run is `/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/` on master (the runner's `infra.topfull_src_path`), with those paths rewritten to `/home/idozacharia` and a few other local edits ([RON-NEZER-SETUP-VS-WORKSHOP.md](../../../Guides%20and%20Info/RON-NEZER-SETUP-VS-WORKSHOP.md) lines 43–44). `run_scenario.py` does **not** copy TopFull's Python files; it only copies `retryguard.py` and the collectors via `deploy_repo_script`. Changes to TopFull's files therefore reach master only through a patch script run on master, the way `experiments/patch_metric_collector.py` already did for `metric_collector.py` (marker-checked, idempotent, `--dry-run`).
- **The no-timeout call.** `Detector.current_rps()` in `overload_detection.py` does `requests.get(url, proxies=proxies)` with no `timeout=` against the proxy's `/stats`. It is called by `Agent.run()` (`deploy_rl.py` ~line 115), `Agent.add_apis()` (~177), `Detector.clustering()` (~170 of `overload_detection.py`, reached from the main loop at `deploy_rl.py` ~288) and `Detector.apply_v2()` (~452, reached from `Agent.run()` ~168). The only other `requests.get` is in dead debug code (`main()`, a hard-coded `egg3.kaist.ac.kr` URL). `apply_threshold_proxy` writes cap files and sends `kill -10`; it makes no HTTP call.
- **How the runner stamps logs.** `TOPFULL_RL_LOG = "topfull_rl.log"`; the RL script is `python3 -u deploy_rl.py 2>&1 | stamp >> {src}/logs/topfull_rl.log`, so every `print` becomes `2026-10-15T13:23:32Z  <text>`. `topfull_health.read_stamped` already parses that.
- **Evidence for the numbers.** [2026-10-15-proxy-fd-evidence-flagged-holds.md](../../../Guides%20and%20Info/2026-10-15-proxy-fd-evidence-flagged-holds.md) (read its corrections box first) and [2026-10-15-s2-topfull-proxy-reruns.md](../../../Guides%20and%20Info/2026-10-15-s2-topfull-proxy-reruns.md). In the two logged holds descriptors hit 1024 about 50–190 s into load; the RL loop then blocked 422 s and 559 s in `current_rps()`.
- **Test style.** `test_run_scenario.py` is `unittest.TestCase` with `mock.patch`; `test_run_scenario_proxy_guard.py` is plain pytest functions with `mock.patch.object(run_scenario, "ssh", ...)`. `test_topfull_health.py` writes stamped logs with a `write(path, rows)` helper. Follow the file you are editing.

---

### Task 1: Raise the proxy's open-files limit and verify it before Locust

**Files:**
- Modify: `experiments/run_scenario.py` (constants near line 44; `_start_master_stack_after_kill`, lines ~809–845)
- Modify: `experiments/test_run_scenario.py` (`TestTopfullStdoutLogs` near line 1589; `setUp` of `TestStartMasterStackTopfullRl` near line 1490 and `TestOverlappedStartup` near line 1783)
- Test: `experiments/test_run_scenario_proxy_guard.py`

**Interfaces:**
- Produces: `PROXY_NOFILE_MIN: int = 4096`; `NOFILE_UNLIMITED: int = 2**31`; `proxy_nofile_bash(log_path: str) -> str`; `PROXY_LIMITS_SCRIPT: str`; `read_proxy_soft_limit(master: str) -> int | None`; `verify_proxy_nofile(master: str, minimum: int = PROXY_NOFILE_MIN, attempts: int = 3, pause: float = 2.0) -> int` (raises `RuntimeError`).
- Consumes: existing `ssh`, `step`, `STAMP_LINES_BASH`, `TOPFULL_PROXY_LOG`, `ensure_proxy_uncapped`.

- [ ] **Step 1: Write the failing tests for the verifier**

Append to `experiments/test_run_scenario_proxy_guard.py`:

```python
def test_read_proxy_soft_limit_takes_the_lowest_value():
    out = mock.Mock(stdout="1048576\n1024\n", returncode=0)
    with mock.patch.object(run_scenario, "ssh", return_value=out):
        assert run_scenario.read_proxy_soft_limit("m") == 1024


def test_read_proxy_soft_limit_is_none_without_a_proxy():
    with mock.patch.object(run_scenario, "ssh", return_value=mock.Mock(stdout="", returncode=0)):
        assert run_scenario.read_proxy_soft_limit("m") is None


def test_read_proxy_soft_limit_treats_unlimited_as_large():
    with mock.patch.object(run_scenario, "ssh", return_value=mock.Mock(stdout="unlimited\n", returncode=0)):
        assert run_scenario.read_proxy_soft_limit("m") == run_scenario.NOFILE_UNLIMITED


def test_limit_command_reads_the_go_binary_not_the_go_tool():
    seen = []

    def fake(host, cmd, check=True):
        seen.append(cmd)
        return mock.Mock(stdout="65536\n", returncode=0)

    with mock.patch.object(run_scenario, "ssh", fake):
        run_scenario.read_proxy_soft_limit("m")
    assert "[/]exe/proxy_online_boutique" in seen[0]
    assert "/proc/$p/limits" in seen[0]
    assert "Max open files" in seen[0]


def test_verify_returns_a_raised_limit():
    with mock.patch.object(run_scenario, "read_proxy_soft_limit", return_value=1048576), \
            mock.patch.object(run_scenario, "step"):
        assert run_scenario.verify_proxy_nofile("m") == 1048576


def test_verify_aborts_when_the_limit_is_still_1024():
    with mock.patch.object(run_scenario, "read_proxy_soft_limit", return_value=1024):
        with pytest.raises(RuntimeError, match="1024"):
            run_scenario.verify_proxy_nofile("m")


def test_verify_waits_for_the_proxy_pid_to_appear():
    reads = [None, None, 65536]
    with mock.patch.object(run_scenario, "read_proxy_soft_limit", side_effect=reads) as read, \
            mock.patch.object(run_scenario.time, "sleep") as sleep, \
            mock.patch.object(run_scenario, "step"):
        assert run_scenario.verify_proxy_nofile("m") == 65536
    assert read.call_count == 3
    assert sleep.call_count == 2


def test_verify_aborts_when_the_limit_cannot_be_read():
    with mock.patch.object(run_scenario, "read_proxy_soft_limit", return_value=None), \
            mock.patch.object(run_scenario.time, "sleep"):
        with pytest.raises(RuntimeError, match="could not read"):
            run_scenario.verify_proxy_nofile("m")


def _rl_off_cfg():
    return {
        "infra": {"master_ssh_host": "m", "topfull_src_path": "/src",
                  "venv_activate": "/venv/bin/activate"},
        "topfull_rl": {"enabled": False},
    }


def test_start_master_stack_verifies_the_limit_before_the_cap_check():
    order = []
    with mock.patch.object(run_scenario, "write_remote_script"), \
            mock.patch.object(run_scenario, "ssh", return_value=_ssh_ok()), \
            mock.patch.object(run_scenario, "wait_with_progress"), \
            mock.patch.object(run_scenario, "verify_proxy_nofile",
                              side_effect=lambda *a, **k: order.append("nofile")), \
            mock.patch.object(run_scenario, "ensure_proxy_uncapped",
                              side_effect=lambda *a, **k: order.append("caps")):
        run_scenario.start_master_stack(_rl_off_cfg())
    assert order[:2] == ["nofile", "caps"]


def test_a_low_limit_stops_the_stack_before_the_cap_check():
    with mock.patch.object(run_scenario, "write_remote_script"), \
            mock.patch.object(run_scenario, "ssh", return_value=_ssh_ok()), \
            mock.patch.object(run_scenario, "wait_with_progress"), \
            mock.patch.object(run_scenario, "verify_proxy_nofile",
                              side_effect=RuntimeError("soft limit 1024")), \
            mock.patch.object(run_scenario, "ensure_proxy_uncapped") as caps:
        with pytest.raises(RuntimeError, match="1024"):
            run_scenario.start_master_stack(_rl_off_cfg())
    caps.assert_not_called()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest experiments/test_run_scenario_proxy_guard.py -v`
Expected: the eleven new tests FAIL with `AttributeError: module 'run_scenario' has no attribute 'read_proxy_soft_limit'` (or `verify_proxy_nofile`). The earlier tests in the file still PASS.

- [ ] **Step 3: Write the failing script-text test**

In `experiments/test_run_scenario.py`, add `import shutil` and `import subprocess` to the imports at the top (after `import json`). Add the following three tests to `class TestTopfullStdoutLogs` (after `test_proxy_output_goes_to_stamped_log`), and add the `verify_proxy_nofile` patch to its `setUp`:

```python
    def setUp(self):
        patcher = mock.patch("run_scenario.ensure_proxy_uncapped")
        patcher.start()
        self.addCleanup(patcher.stop)
        nofile = mock.patch("run_scenario.verify_proxy_nofile")
        nofile.start()
        self.addCleanup(nofile.stop)
```

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    def test_proxy_script_raises_the_soft_limit_before_go_run(
        self, mock_ssh, mock_write_script, mock_wait
    ):
        mock_ssh.return_value = mock.Mock(stdout="", returncode=0)
        run_scenario.start_master_stack(self._cfg(rl_enabled=False))
        script = self._script(mock_write_script, "/tmp/rg_proxy.sh")
        stamp_at = script.index("stamp() {")
        limit_at = script.index('ulimit -Sn "$TARGET"')
        run_at = script.index("go run proxy_online_boutique.go")
        self.assertLess(stamp_at, limit_at)
        self.assertLess(limit_at, run_at)
        self.assertIn("HARD=$(ulimit -Hn)", script)
        self.assertIn('[ "$HARD" = "unlimited" ]', script)
        self.assertIn('echo "nofile soft=$(ulimit -Sn) hard=$HARD"', script)
        self.assertIn(f"{self.SRC}/logs/topfull_proxy.log", script)

    def test_nofile_block_warns_when_the_hard_limit_is_low(self):
        block = run_scenario.proxy_nofile_bash("/x/topfull_proxy.log")
        self.assertIn(f'[ "$TARGET" -lt {run_scenario.PROXY_NOFILE_MIN} ]', block)
        self.assertIn("WARN hard nofile limit", block)
        self.assertIn("WARN could not raise soft nofile", block)

    def test_nofile_block_is_valid_bash_and_raises_the_limit(self):
        bash = shutil.which("bash")
        if bash is None or subprocess.run([bash, "-c", "true"], capture_output=True).returncode != 0:
            self.skipTest("no working bash on this machine")
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp, "proxy.log").as_posix()
            script = (
                "export TZ=UTC\n" + run_scenario.STAMP_LINES_BASH
                + run_scenario.proxy_nofile_bash(log)
                + "ulimit -Sn\n"
            )
            result = subprocess.run([bash, "-c", script], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("nofile soft=", Path(log).read_text(encoding="utf-8"))
            self.assertGreater(int(result.stdout.strip().splitlines()[-1] or 0), 1024)
```

In `TestStartMasterStackTopfullRl.setUp` and `TestOverlappedStartup.setUp`, add the same patcher after the `ensure_proxy_uncapped` one:

```python
        nofile = mock.patch("run_scenario.verify_proxy_nofile")
        nofile.start()
        self.addCleanup(nofile.stop)
```

- [ ] **Step 4: Run to verify the script-text tests fail**

Run: `python -m pytest experiments/test_run_scenario.py::TestTopfullStdoutLogs -v`
Expected: FAIL with `AttributeError: module 'run_scenario' does not have the attribute 'verify_proxy_nofile'` (the `setUp` patch) — that is the intended red state.

- [ ] **Step 5: Implement**

In `experiments/run_scenario.py`, after the `STAMP_LINES_BASH` definition (line ~46) add:

```python
# The proxy is started with `go run`, which execs the compiled binary; the binary keeps
# the limits of the shell in /tmp/rg_proxy.sh. A soft limit of 1024 was reached 50-190 s
# into load on 2026-10-15 (accept4: too many open files). Raise it to the hard limit.
PROXY_NOFILE_MIN = 4096
NOFILE_UNLIMITED = 2 ** 31


def proxy_nofile_bash(log_path: str) -> str:
    """Bash lines for /tmp/rg_proxy.sh: raise the soft open-files limit, log what it became.

    Needs `stamp` defined above it. `unlimited` hard limit is capped at 1048576.
    """
    return (
        "HARD=$(ulimit -Hn)\n"
        'if [ "$HARD" = "unlimited" ]; then TARGET=1048576; else TARGET=$HARD; fi\n'
        f'if [ "$TARGET" -lt {PROXY_NOFILE_MIN} ]; then '
        f'echo "WARN hard nofile limit $TARGET is below {PROXY_NOFILE_MIN}" | stamp >> {log_path}; fi\n'
        'ulimit -Sn "$TARGET" 2>/dev/null || '
        f'echo "WARN could not raise soft nofile to $TARGET" | stamp >> {log_path}\n'
        f'echo "nofile soft=$(ulimit -Sn) hard=$HARD" | stamp >> {log_path}\n'
    )
```

In `_start_master_stack_after_kill`, change the `proxy_script` assignment to:

```python
    proxy_script = (
        "#!/bin/bash\n"
        "export TZ=UTC\n"
        + STAMP_LINES_BASH
        + proxy_nofile_bash(f"{logs}/{TOPFULL_PROXY_LOG}")
        + f"cd {src}/proxy\n"
        f"go run proxy_online_boutique.go 2>&1 | stamp >> {logs}/{TOPFULL_PROXY_LOG}\n"
    )
```

Directly after the `wait_with_progress(5, "proxy init")` that follows `step("Started: Go proxy (tmux session: proxy)")`, and before the `ensure_proxy_uncapped(master, src, restart_proxy)` call, add:

```python
    verify_proxy_nofile(master)
```

Above `start_master_stack` (next to `ensure_proxy_uncapped`) add:

```python
# The Go binary, not the `go run` parent: `go run` has no `/exe/` in its command line.
PROXY_LIMITS_SCRIPT = (
    "for p in $(pgrep -f '[/]exe/proxy_online_boutique'); do "
    "awk '/^Max open files/ {print $4}' /proc/$p/limits; done"
)


def read_proxy_soft_limit(master: str) -> int | None:
    """Lowest soft open-files limit among the proxy binary's processes, or None if none found."""
    out = ssh(master, PROXY_LIMITS_SCRIPT, check=False).stdout or ""
    values = []
    for token in out.split():
        if token == "unlimited":
            values.append(NOFILE_UNLIMITED)
        elif token.isdigit():
            values.append(int(token))
    return min(values) if values else None


def verify_proxy_nofile(master: str, minimum: int = PROXY_NOFILE_MIN,
                        attempts: int = 3, pause: float = 2.0) -> int:
    """Abort before Locust unless the proxy binary runs with a raised open-files limit."""
    soft = None
    for attempt in range(attempts):
        soft = read_proxy_soft_limit(master)
        if soft is not None:
            break
        if attempt < attempts - 1:
            time.sleep(pause)
    if soft is None:
        raise RuntimeError(
            "could not read the proxy's open-files limit: no process matching "
            "'/exe/proxy_online_boutique' (is the proxy up?)"
        )
    if soft < minimum:
        raise RuntimeError(
            f"proxy soft open-files limit is {soft} (needs at least {minimum}); "
            "the proxy would refuse new connections under load. Check `ulimit -Hn` on master "
            "and the nofile lines at the top of topfull_proxy.log"
        )
    step(f"Proxy open-files soft limit {soft} [OK]")
    return soft
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest experiments/test_run_scenario_proxy_guard.py experiments/test_run_scenario.py -q`
Expected: all pass. If a class not named above fails with `could not read the proxy's open-files limit`, it calls `start_master_stack` without the new patch; add the same `verify_proxy_nofile` patcher to that class's `setUp`.

- [ ] **Step 7: Commit (only if the user asked for commits)**

```powershell
git add experiments/run_scenario.py experiments/test_run_scenario.py experiments/test_run_scenario_proxy_guard.py
git commit -m "fix: raise the proxy's open-files limit and verify it before Locust"
```

---

### Task 2: `proxy_fds.csv` — a descriptor sampler on master

**Files:**
- Create: `experiments/proxy_fd_collector.py`
- Create: `experiments/test_proxy_fd_collector.py`
- Modify: `experiments/run_scenario.py` (`start_proxy_fd_collector`, `kill_stale_master_processes` ~line 669, `MASTER_PROCESS_GATE` ~line 1196, `require_master_processes`, `start_overlapped_services` ~line 1225, `stop_master_stack` ~line 1381, manifest dict ~line 1627)
- Modify: `experiments/test_run_scenario.py` (new wiring class; `TestOverlappedStartup` gate list)
- Modify: `AGENTS.md` (§6 `/tmp` clear list, steps 2–5; §2 repo layout)
- Modify: `Guides and Info/METRICS-GATHERED.md` (file table near line 341)

**Interfaces:**
- Produces: `proxy_fds.csv` columns `timestamp,pid,open_fds,soft_limit` (UTC `%Y-%m-%dT%H:%M:%SZ`, `soft_limit` -1 means unlimited); `proxy_fd_collector.log` with `START` / `WARNING` / `SHUTDOWN` / `EXIT` lines; `run_scenario.start_proxy_fd_collector(cfg: dict) -> None`; YAML key `proxy_fd_collector: {enabled: bool (default true), poll_interval_seconds: float (default 1)}`; tmux session `proxyfd`; remote script `/tmp/rg_proxy_fd.sh`; params `/tmp/proxy_fd_params.json`.
- Consumes: `deploy_repo_script`, `write_remote_json`, `write_remote_script`, `ssh`, `banner`, `step`.

The collector is on by default (omitted key = on) so existing YAMLs sample without edits.

- [ ] **Step 1: Write the failing collector tests**

Create `experiments/test_proxy_fd_collector.py`:

```python
"""Tests for proxy_fd_collector.py. Run: python -m pytest experiments/test_proxy_fd_collector.py -v"""
import csv
import logging
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import proxy_fd_collector as pfc

LIMITS = (
    "Limit                     Soft Limit           Hard Limit           Units\n"
    "Max cpu time              unlimited            unlimited            seconds\n"
    "Max open files            {soft}                 {hard}              files\n"
    "Max locked memory         65536                65536                bytes\n"
)


def make_proc(root: Path, pid: int, cmdline: bytes, fds: int, soft="1024", hard="1048576"):
    d = root / str(pid)
    (d / "fd").mkdir(parents=True)
    for i in range(fds):
        (d / "fd" / str(i)).write_text("", encoding="utf-8")
    (d / "cmdline").write_bytes(cmdline)
    (d / "limits").write_text(LIMITS.format(soft=soft, hard=hard), encoding="utf-8")


GO_EXE = b"/tmp/go-build123/b001/exe/proxy_online_boutique\0"
GO_TOOL = b"go\0run\0proxy_online_boutique.go\0"


class TestFindAndSample(unittest.TestCase):
    def test_finds_the_binary_and_not_the_go_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_proc(root, 100, GO_TOOL, 4)
            make_proc(root, 200, GO_EXE, 7)
            (root / "self").mkdir()
            self.assertEqual(pfc.find_proxy_pids(str(root)), [200])

    def test_sample_reads_fds_and_soft_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_proc(root, 200, GO_EXE, 7, soft="1024")
            rows = pfc.sample_once(1760620800, str(root))
        self.assertEqual(rows, [{"timestamp": "2025-10-16T12:00:00Z",
                                 "pid": 200, "open_fds": 7, "soft_limit": 1024}])

    def test_unlimited_is_minus_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_proc(root, 200, GO_EXE, 2, soft="unlimited", hard="unlimited")
            self.assertEqual(pfc.sample_once(0, str(root))[0]["soft_limit"], -1)

    def test_missing_proc_root_gives_no_rows(self):
        self.assertEqual(pfc.sample_once(0, "/no/such/proc"), [])


class TestRunCollector(unittest.TestCase):
    def test_writes_one_header_and_appends_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proc"
            root.mkdir()
            make_proc(root, 200, GO_EXE, 3)
            out = Path(tmp) / "out"
            out.mkdir()
            times = iter([1000.0, 1000.2, 1001.0, 1001.2])
            pfc.run_collector({"poll_interval_seconds": 1}, out, proc_root=str(root),
                              max_polls=2, clock=lambda: next(times), sleep=lambda s: None)
            pfc.run_collector({"poll_interval_seconds": 1}, out, proc_root=str(root),
                              max_polls=1, clock=lambda: 1002.0, sleep=lambda s: None)
            rows = list(csv.DictReader((out / "proxy_fds.csv").open(encoding="utf-8")))
        self.assertEqual(list(rows[0].keys()), ["timestamp", "pid", "open_fds", "soft_limit"])
        self.assertEqual(len(rows), 3)
        self.assertEqual({r["open_fds"] for r in rows}, {"3"})

    def test_no_proxy_writes_no_csv_and_warns_once_per_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proc"
            root.mkdir()
            out = Path(tmp) / "out"
            out.mkdir()
            with self.assertLogs("proxy_fd_collector", level=logging.WARNING) as logs:
                times = iter([1000.0, 1001.0, 1002.0, 1040.0])
                pfc.run_collector({"poll_interval_seconds": 1}, out, proc_root=str(root),
                                  max_polls=4, clock=lambda: next(times), sleep=lambda s: None)
            self.assertFalse((out / "proxy_fds.csv").exists())
        self.assertEqual(len(logs.records), 2)  # t=1000 and t=1040; not 1001, 1002


if __name__ == "__main__":
    unittest.main()
```

Sanity check of the literal used in `test_sample_reads_fds_and_soft_limit` (epoch `1760620800`): `python -c "from datetime import datetime,timezone;print(datetime.fromtimestamp(1760620800,tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))"` must print `2025-10-16T12:00:00Z`. If it prints anything else, change the epoch in the test to the value that gives that string.

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest experiments/test_proxy_fd_collector.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'proxy_fd_collector'`.

- [ ] **Step 3: Implement the collector**

Create `experiments/proxy_fd_collector.py`:

```python
#!/usr/bin/env python3
"""
proxy_fd_collector.py — open file descriptors of the TopFull Go proxy, once a second.

The proxy ran out of descriptors (soft limit 1024) 50-190 s into load on 2026-10-15; the cause
had to be inferred from `accept4: too many open files`. This puts the count in the data.
Stdlib only. Reads /proc, never touches the proxy.

Usage (on master):
    python3 proxy_fd_collector.py --params /tmp/proxy_fd_params.json
params: {"output_dir": "<src>/logs", "poll_interval_seconds": 1}
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

CSV_NAME = "proxy_fds.csv"
LOG_NAME = "proxy_fd_collector.log"
CSV_COLUMNS = ["timestamp", "pid", "open_fds", "soft_limit"]
# `go run` execs the compiled binary at /tmp/go-build.../exe/proxy_online_boutique.
PROXY_EXE_MARK = "/exe/proxy_online_boutique"
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
NO_PROXY_WARN_EVERY_S = 30.0
UNLIMITED = -1
_LIMITS = re.compile(r"^Max open files\s+(\S+)\s+(\S+)", re.MULTILINE)

_shutdown = False
log = logging.getLogger("proxy_fd_collector")


def utc_stamp(now: float) -> str:
    return datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_proxy_pids(proc_root: str = "/proc") -> list[int]:
    pids = []
    try:
        names = os.listdir(proc_root)
    except OSError:
        return pids
    for name in names:
        if not name.isdigit():
            continue
        try:
            raw = Path(proc_root, name, "cmdline").read_bytes()
        except OSError:
            continue
        if PROXY_EXE_MARK in raw.replace(b"\0", b" ").decode("utf-8", "replace"):
            pids.append(int(name))
    return sorted(pids)


def count_open_fds(pid: int, proc_root: str = "/proc") -> Optional[int]:
    try:
        return len(os.listdir(Path(proc_root, str(pid), "fd")))
    except OSError:
        return None


def read_soft_limit(pid: int, proc_root: str = "/proc") -> Optional[int]:
    try:
        text = Path(proc_root, str(pid), "limits").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = _LIMITS.search(text)
    if not match:
        return None
    return UNLIMITED if match.group(1) == "unlimited" else int(match.group(1))


def sample_once(now: float, proc_root: str = "/proc") -> list[dict]:
    rows = []
    for pid in find_proxy_pids(proc_root):
        fds = count_open_fds(pid, proc_root)
        soft = read_soft_limit(pid, proc_root)
        if fds is None or soft is None:
            continue  # the process exited between the listing and the read
        rows.append({"timestamp": utc_stamp(now), "pid": pid, "open_fds": fds, "soft_limit": soft})
    return rows


def append_rows(path: Path, rows: list[dict]) -> None:
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        if new:
            writer.writeheader()
        writer.writerows(rows)


def run_collector(
    params: dict,
    out_dir: Path,
    proc_root: str = "/proc",
    max_polls: Optional[int] = None,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    interval = float(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    csv_path = Path(out_dir) / CSV_NAME
    last_warn: Optional[float] = None
    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        now = clock()
        rows = sample_once(now, proc_root)
        if rows:
            append_rows(csv_path, rows)
        elif last_warn is None or now - last_warn >= NO_PROXY_WARN_EVERY_S:
            log.warning("%s  WARNING  no process matching %s", utc_stamp(now), PROXY_EXE_MARK)
            last_warn = now
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
        sleep(max(0.0, interval - (clock() % interval)))


def _handle_signal(signum, _frame) -> None:
    global _shutdown
    _shutdown = True
    log.info("%s  SHUTDOWN  signal=%s", utc_stamp(time.time()), signum)


def setup_logging(out_dir: Path) -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    log.addHandler(stream)
    try:
        handler = logging.FileHandler(str(Path(out_dir) / LOG_NAME), mode="a")
        handler.setFormatter(fmt)
        log.addHandler(handler)
    except OSError as exc:
        print(f"could not open {LOG_NAME}: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="TopFull proxy open-descriptor sampler.")
    parser.add_argument("--params", required=True, help="Path to collector params JSON")
    args = parser.parse_args()
    params = json.loads(Path(args.params).read_text(encoding="utf-8"))
    out_dir = Path(params["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(out_dir)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    log.info("%s  START  poll_interval=%ss", utc_stamp(time.time()),
             params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    run_collector(params, out_dir)
    log.info("%s  EXIT", utc_stamp(time.time()))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the collector tests**

Run: `python -m pytest experiments/test_proxy_fd_collector.py -v`
Expected: all pass. (`test_no_proxy_writes_no_csv_and_warns_once_per_window` passes because the 30 s window suppresses the polls at t=1001 and 1002.)

- [ ] **Step 5: Write the failing runner-wiring tests**

Append to `experiments/test_run_scenario.py` after `TestTopfullThrottleCollectorWiring`:

```python
class TestProxyFdCollectorWiring(unittest.TestCase):
    def _cfg(self, **block):
        cfg = {
            "infra": {
                "master_ssh_host": "topfull-master",
                "topfull_src_path": "/home/idozacharia/TopFull/src",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
            },
        }
        if block:
            cfg["proxy_fd_collector"] = block
        return cfg

    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_on_by_default_deploys_and_launches(self, mock_deploy, mock_ssh, mock_json, mock_script):
        run_scenario.start_proxy_fd_collector(self._cfg())
        mock_deploy.assert_called_once_with(
            "topfull-master", "proxy_fd_collector.py",
            "/home/idozacharia/experiments/proxy_fd_collector.py",
        )
        path, params = mock_json.call_args[0][1:3]
        self.assertEqual(path, "/tmp/proxy_fd_params.json")
        self.assertEqual(params, {
            "output_dir": "/home/idozacharia/TopFull/src/logs",
            "poll_interval_seconds": 1.0,
        })
        script_path, body = mock_script.call_args[0][1:3]
        self.assertEqual(script_path, "/tmp/rg_proxy_fd.sh")
        self.assertIn("proxy_fd_collector.py --params /tmp/proxy_fd_params.json", body)
        tmux = [c for c in mock_ssh.call_args_list if "tmux new-session -d -s proxyfd" in c.args[1]]
        self.assertEqual(len(tmux), 1)

    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_disabled_does_nothing(self, mock_deploy, mock_ssh, mock_json, mock_script):
        run_scenario.start_proxy_fd_collector(self._cfg(enabled=False))
        mock_deploy.assert_not_called()
        mock_ssh.assert_not_called()

    def test_process_lists_name_the_collector(self):
        self.assertIn("[p]roxy_fd_collector.py", run_scenario.MASTER_PROCESS_GATE)
```

In `TestOverlappedStartup._run_startup`'s `fake_ssh`, add `"proxy_fd_collector.py",` to the `stdout = "\n".join([...])` list (after `"topfull_throttle_collector.py",`). Add a test to `TestOverlappedStartup`:

```python
    def test_proxy_fd_collector_starts_after_the_proxy_and_before_locust(self):
        events, exited = self._run_startup(self._cfg())
        self.assertFalse(exited)
        proxy_wait = next(i for i, e in enumerate(events) if e == "wait:proxy init")
        fd = next(i for i, e in enumerate(events) if "tmux new-session -d -s proxyfd" in e)
        locust = next(i for i, e in enumerate(events) if "tmux new-session -d -s loadgen" in e)
        self.assertLess(proxy_wait, fd)
        self.assertLess(fd, locust)
```

- [ ] **Step 6: Run to verify they fail**

Run: `python -m pytest experiments/test_run_scenario.py::TestProxyFdCollectorWiring experiments/test_run_scenario.py::TestOverlappedStartup -v`
Expected: FAIL with `AttributeError: module 'run_scenario' has no attribute 'start_proxy_fd_collector'` and the `MASTER_PROCESS_GATE` assertion.

- [ ] **Step 7: Implement the wiring**

In `experiments/run_scenario.py`, after `start_topfull_throttle_collector` add:

```python
def start_proxy_fd_collector(cfg: dict):
    """
    Start the proxy descriptor sampler on master (writes src/logs/proxy_fds.csv).

    On by default for every variant: the proxy carries all Locust traffic, so
    descriptor exhaustion hits rg_only and both_off holds too.
    """
    pfc_cfg = cfg.get("proxy_fd_collector", {})
    if not pfc_cfg.get("enabled", True):
        return

    banner("Starting proxy descriptor collector")
    master = cfg["infra"]["master_ssh_host"]
    src = cfg["infra"]["topfull_src_path"]
    venv = cfg["infra"]["venv_activate"]
    script = cfg["infra"].get(
        "proxy_fd_collector_script",
        "/home/idozacharia/experiments/proxy_fd_collector.py",
    )
    deploy_repo_script(master, "proxy_fd_collector.py", script)
    params = {
        "output_dir": f"{src}/logs",
        "poll_interval_seconds": float(pfc_cfg.get("poll_interval_seconds", 1)),
    }
    write_remote_json(master, "/tmp/proxy_fd_params.json", params)
    start_script = (
        "#!/bin/bash\n"
        f"source {venv}\n"
        f"python3 {script} --params /tmp/proxy_fd_params.json\n"
    )
    write_remote_script(master, "/tmp/rg_proxy_fd.sh", start_script)
    ssh(master, "tmux new-session -d -s proxyfd /tmp/rg_proxy_fd.sh")
    step(f"Started: proxy descriptor collector (tmux session: proxyfd, script: {script})")
```

In `start_overlapped_services`, change `cpu_then_throttle` to:

```python
    def cpu_then_throttle():
        start_resource_usage_collector(cfg)
        proxy_ready.wait()
        start_proxy_fd_collector(cfg)
        start_topfull_throttle_collector(cfg)
```

Add the process name everywhere the others appear:
- `kill_stale_master_processes`: after the `[t]opfull_throttle_collector.py` line add `"pkill -9 -f '[p]roxy_fd_collector.py' 2>/dev/null; "`.
- `stop_master_stack`: after the `[t]opfull_throttle_collector.py` line add `"pkill -f '[p]roxy_fd_collector.py' 2>/dev/null; "`, and extend the `step(...)` text with `proxy descriptor collector,`.
- `MASTER_PROCESS_GATE`: `"[t]opfull_throttle_collector.py|[p]roxy_fd_collector.py|[d]eploy_rl.py|[r]etryguard.py' || true"`.
- `require_master_processes`: after the throttle block add

```python
    if cfg.get("proxy_fd_collector", {}).get("enabled", True):
        needed.append("proxy_fd_collector.py")
```
- `collect_results` manifest: after the `"topfull_throttle_collector"` line add `"proxy_fd_collector": cfg.get("proxy_fd_collector", {"enabled": True}),`.

`collect_results` already copies `src/logs/.` to the run folder, so `proxy_fds.csv` and `proxy_fd_collector.log` are pulled with the folder; `pull_results.py` runs `scp -r` on the whole folder. No change there.

- [ ] **Step 8: Run the runner tests**

Run: `python -m pytest experiments/test_run_scenario.py experiments/test_run_scenario_proxy_guard.py experiments/test_proxy_fd_collector.py -q`
Expected: all pass.

- [ ] **Step 9: Update AGENTS.md §6 and §2, and METRICS-GATHERED.md**

`AGENTS.md` §6, the `/tmp` clear command: append `/tmp/rg_proxy_fd.sh /tmp/proxy_fd_params.json` inside the `sudo rm -f` list.

§6 step 2 (kill list): add `proxy_fd_collector.py` to the prose "mesh collector, throttle collector, CPU collector, ..." and `pkill -f '[p]roxy_fd_collector.py' 2>/dev/null; ` after the `[t]opfull_throttle_collector.py` pkill in the code block.

§6 step 3 (pgrep): change the master pattern to `...|[t]opfull_throttle_collector.py|[p]roxy_fd_collector.py' || echo master-clear`.

§6 step 4 (clear live logs) needs no change (`*.csv` / `*.log` cover `proxy_fds.csv`, `proxy_fd_collector.log`); step 5 "a `.csv` or `.log` is back" now also covers them.

§2 repo layout: after the `resource_usage_collector.py` line add:

```
 proxy_fd_collector.py ← samples the Go proxy's open fd count and soft limit into `proxy_fds.csv` (deployed to master by the runner; on by default)
```

`Guides and Info/METRICS-GATHERED.md`, in the file table after the `topfull_rl.log` row add:

```
| `proxy_fds.csv` | `timestamp, pid, open_fds, soft_limit` once a second for the Go proxy binary (`soft_limit` -1 = unlimited). Written by `experiments/proxy_fd_collector.py` | Holds from the Task-2 runner change on, every variant (the proxy carries all Locust traffic). Earlier holds have no file. The descriptor count is how a stalled proxy shows up: `open_fds` reaches `soft_limit` |
```
and change the `envoy_retry_collector.log / ...` row's first cell to `` `envoy_retry_collector.log` / `resource_usage_collector.log` / `topfull_throttle_collector.log` / `proxy_fd_collector.log` ``.

- [ ] **Step 10: Check the diff and commit (commit only if the user asked)**

Run: `git diff --stat`
Expected: only the files listed under Task 2 Files, plus Task 1's files.

```powershell
git add experiments/proxy_fd_collector.py experiments/test_proxy_fd_collector.py experiments/run_scenario.py experiments/test_run_scenario.py AGENTS.md "Guides and Info/METRICS-GATHERED.md"
git commit -m "feat: sample the proxy's open descriptors into proxy_fds.csv"
```

---

### Task 3: RL-loop timeout, skip-on-timeout, and parseable `RL_*` log lines

**Files:**
- Create: `experiments/patch_rl_timeout.py`
- Create: `experiments/test_patch_rl_timeout.py`
- Create: `Guides and Info/TOPFULL-UPSTREAM-DEVIATIONS.md`
- Modify: `experiments/run_scenario.py` (`verify_rl_patch`, called from `_start_master_stack_after_kill` when RL is on)
- Modify: `experiments/test_run_scenario_proxy_guard.py`
- Modify: `AGENTS.md` (§3 guides table row; §7 known-fixes sentence — wording in Step 9)

**Interfaces:**
- Produces: `patch_rl_timeout.MARKER = "RL_TIMEOUT_PATCH v1"`; `patch_rl_timeout.apply(text_overload: str, text_deploy: str) -> tuple[str, str]` (pure, idempotent, raises `PatchError` if an anchor is missing); `python experiments/patch_rl_timeout.py [--src DIR] [--dry-run]`; `run_scenario.verify_rl_patch(master: str, src: str) -> None` (raises `RuntimeError`).
- Log line format written by the patched TopFull (all go to `topfull_rl.log` through the runner's `stamp`). Parsed by Task 4:

```
RL_LOOP_START iter=<int>
RL_RPS_START caller=<clustering|agent|add_apis|unknown>
RL_RPS_END caller=<..> elapsed_s=<float> ok=1
RL_RPS_TIMEOUT caller=<..> elapsed_s=<float> timeout_s=<float> error=<ExceptionName>
RL_SKIP where=<agent|add_apis|clustering> reason=proxy_stats_unavailable
RL_CAP_APPLY api=<name> threshold=<float>
```

**What the patch changes in behavior.** `current_rps()` gets `timeout=2.0`. On a timeout or connection error it raises `ProxyStatsUnavailable`; the three callers in `deploy_rl.py` catch it and **skip that tick** (the next tick retries). When the proxy answers, nothing changes: same data, same decisions. This is a robustness fix for a call that today can block for 7–9 minutes, not a change to TopFull's control algorithm. The 2.0 s value is the RL main loop's own tick; a `/stats` answer takes milliseconds when the proxy can accept (the throttle collector, which uses 0.8 s, gets a fresh read every 5 s on every clean hold).

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_patch_rl_timeout.py`:

```python
"""Tests for patch_rl_timeout.py. Run: python -m pytest experiments/test_patch_rl_timeout.py -v

The tests patch temp copies of the upstream files in the TopFull submodule. The submodule
itself is never written.
"""
import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import patch_rl_timeout as prt

UPSTREAM = (Path(__file__).resolve().parent.parent / "TopFull" / "TopFull_master"
            / "online_boutique_scripts" / "src")


@pytest.fixture
def upstream():
    over = UPSTREAM / "overload_detection.py"
    dep = UPSTREAM / "deploy_rl.py"
    if not over.is_file() or not dep.is_file():
        pytest.skip("TopFull submodule is not checked out")
    return over.read_text(encoding="utf-8"), dep.read_text(encoding="utf-8")


def test_patched_files_are_valid_python(upstream):
    over, dep = prt.apply(*upstream)
    ast.parse(over)
    ast.parse(dep)


def test_requests_get_in_current_rps_has_a_timeout(upstream):
    over, _ = prt.apply(*upstream)
    tree = ast.parse(over)
    method = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "current_rps")
    gets = [c for c in ast.walk(method)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            and c.func.attr == "get"]
    assert gets, "no requests.get left in current_rps"
    assert all(any(k.arg == "timeout" for k in c.keywords) for c in gets)


def test_the_three_callers_catch_the_exception(upstream):
    over, dep = prt.apply(*upstream)
    assert dep.count("except ProxyStatsUnavailable") == 4  # run(rps), run(apply_v2), add_apis, main loop
    assert 'caller="agent"' in dep
    assert 'caller="add_apis"' in dep
    assert 'caller="clustering"' in over


def test_log_lines_are_present(upstream):
    over, dep = prt.apply(*upstream)
    for token in ("RL_RPS_START", "RL_RPS_END", "RL_RPS_TIMEOUT", "RL_CAP_APPLY"):
        assert token in over
    for token in ("RL_LOOP_START", "RL_SKIP"):
        assert token in dep


def test_marker_is_in_both_files_and_apply_is_idempotent(upstream):
    over, dep = prt.apply(*upstream)
    assert prt.MARKER in over and prt.MARKER in dep
    assert prt.apply(over, dep) == (over, dep)


def test_crlf_files_round_trip(upstream):
    over, dep = (t.replace("\r\n", "\n").replace("\n", "\r\n") for t in upstream)
    new_over, new_dep = prt.apply(over, dep)
    assert "\r\n" in new_over and "\n" not in new_over.replace("\r\n", "")
    ast.parse(new_over.replace("\r\n", "\n"))


def test_a_changed_file_is_refused_not_guessed():
    with pytest.raises(prt.PatchError, match="anchor"):
        prt.apply("print('not overload_detection')\n", "print('not deploy_rl')\n")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest experiments/test_patch_rl_timeout.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'patch_rl_timeout'`.

- [ ] **Step 3: Check the two assumptions the patch makes about upstream**

Run:
```powershell
rg -n "__all__" TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py
rg -n "^import time|^from time|import \*" TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py
```
Expected: no `__all__` (so `from overload_detection import *` in `deploy_rl.py` exports `ProxyStatsUnavailable`); `import *` lines exist. If `__all__` exists, stop and put the exception's name in it in the patch (add a NEW line after the class).

- [ ] **Step 4: Implement the patch script**

Create `experiments/patch_rl_timeout.py`:

```python
#!/usr/bin/env python3
"""
Patch master's TopFull RL loop so a stalled proxy cannot block it, and so its log
carries the facts needed to see a stall. Safe to run more than once.

Run ON MASTER (the live copy is not in this repo's TopFull/ submodule):

    python3 patch_rl_timeout.py [--src DIR] [--dry-run]

Changes (see Guides and Info/TOPFULL-UPSTREAM-DEVIATIONS.md):
  overload_detection.py  current_rps(): requests.get(..., timeout=2.0); on failure raise
                         ProxyStatsUnavailable; RL_RPS_START / RL_RPS_END / RL_RPS_TIMEOUT
                         lines; RL_CAP_APPLY line per applied cap.
  deploy_rl.py           Agent.run(), Agent.add_apis() and the main loop skip the tick on
                         ProxyStatsUnavailable; RL_LOOP_START heartbeat; RL_SKIP lines.
The paths rewritten for this VM (global_config_path) are not touched.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_SRC = Path(
    "/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src"
)
MARKER = "RL_TIMEOUT_PATCH v1"


class PatchError(RuntimeError):
    pass


# --- overload_detection.py --------------------------------------------------

OD_IMPORT_OLD = "import random\nimport threading\n"
OD_IMPORT_NEW = f'''import random
import threading
import time as _rl_time
import requests as _rl_requests

# {MARKER}: deviation from upstream TopFull, see Guides and Info/TOPFULL-UPSTREAM-DEVIATIONS.md
RL_PROXY_TIMEOUT_S = 2.0


class ProxyStatsUnavailable(Exception):
    """The proxy's /stats did not answer within RL_PROXY_TIMEOUT_S."""
'''

OD_CAP_OLD = "        print(f\"{api['name']}: {api['threshold']}\")\n        total += api['threshold']\n"
OD_CAP_NEW = (
    "        print(f\"{api['name']}: {api['threshold']}\")\n"
    "        print(f\"RL_CAP_APPLY api={api['name']} threshold={api['threshold']}\", flush=True)\n"
    "        total += api['threshold']\n"
)

OD_DEF_OLD = "    def current_rps(self):\n"
OD_DEF_NEW = "    def current_rps(self, caller=\"unknown\"):\n"

OD_GET_OLD = (
    "        response = requests.get(url, proxies=proxies)\n"
    "        if not response.ok:\n"
    "            return None\n"
)
OD_GET_NEW = (
    "        print(f\"RL_RPS_START caller={caller}\", flush=True)\n"
    "        _t0 = _rl_time.time()\n"
    "        try:\n"
    "            response = requests.get(url, proxies=proxies, timeout=RL_PROXY_TIMEOUT_S)\n"
    "        except _rl_requests.exceptions.RequestException as exc:\n"
    "            print(f\"RL_RPS_TIMEOUT caller={caller} elapsed_s={_rl_time.time() - _t0:.2f} \"\n"
    "                  f\"timeout_s={RL_PROXY_TIMEOUT_S} error={type(exc).__name__}\", flush=True)\n"
    "            raise ProxyStatsUnavailable(str(exc))\n"
    "        print(f\"RL_RPS_END caller={caller} elapsed_s={_rl_time.time() - _t0:.2f} \"\n"
    "              f\"ok={int(response.ok)}\", flush=True)\n"
    "        if not response.ok:\n"
    "            return None\n"
)

OD_CLUSTER_OLD = "        rps = self.current_rps()\n        # print(rps)\n"
OD_CLUSTER_NEW = "        rps = self.current_rps(caller=\"clustering\")\n        # print(rps)\n"

# --- deploy_rl.py -----------------------------------------------------------

DR_RUN_OLD = (
    "        goodput = 0\n"
    "        clean_apis = []\n"
    "        rps = self.detector.current_rps()\n"
)
DR_RUN_NEW = (
    "        goodput = 0\n"
    "        clean_apis = []\n"
    f"        # {MARKER}\n"
    "        try:\n"
    "            rps = self.detector.current_rps(caller=\"agent\")\n"
    "        except ProxyStatsUnavailable:\n"
    "            print(\"RL_SKIP where=agent reason=proxy_stats_unavailable\", flush=True)\n"
    "            return\n"
)

DR_APPLY_OLD = "        self.detector.apply_v2(float(action), self.target_apis, [])\n"
DR_APPLY_NEW = (
    "        try:\n"
    "            self.detector.apply_v2(float(action), self.target_apis, [])\n"
    "        except ProxyStatsUnavailable:\n"
    "            print(\"RL_SKIP where=agent reason=proxy_stats_unavailable\", flush=True)\n"
    "            return\n"
)

DR_ADD_OLD = (
    "    def add_apis(self, new_apis):\n"
    "        rps = self.detector.current_rps()\n"
)
DR_ADD_NEW = (
    "    def add_apis(self, new_apis):\n"
    "        try:\n"
    "            rps = self.detector.current_rps(caller=\"add_apis\")\n"
    "        except ProxyStatsUnavailable:\n"
    "            print(\"RL_SKIP where=add_apis reason=proxy_stats_unavailable\", flush=True)\n"
    "            return\n"
)

DR_LOOP_OLD = "# Start Loop\nwhile True:\n    time.sleep(2)\n    # Clean stopped agents\n"
DR_LOOP_NEW = (
    "# Start Loop\n"
    "_rl_iter = 0\n"
    "while True:\n"
    "    time.sleep(2)\n"
    "    _rl_iter += 1\n"
    "    print(f\"RL_LOOP_START iter={_rl_iter}\", flush=True)\n"
    "    # Clean stopped agents\n"
)

DR_CLUSTER_OLD = "        cluster_apis = detector.clustering([svc])\n        print(cluster_apis)\n"
DR_CLUSTER_NEW = (
    "        try:\n"
    "            cluster_apis = detector.clustering([svc])\n"
    "        except ProxyStatsUnavailable:\n"
    "            print(f\"RL_SKIP where=clustering svc={svc} reason=proxy_stats_unavailable\", flush=True)\n"
    "            continue\n"
    "        print(cluster_apis)\n"
)

OVERLOAD_EDITS = [
    (OD_IMPORT_OLD, OD_IMPORT_NEW),
    (OD_CAP_OLD, OD_CAP_NEW),
    (OD_DEF_OLD, OD_DEF_NEW),
    (OD_GET_OLD, OD_GET_NEW),
    (OD_CLUSTER_OLD, OD_CLUSTER_NEW),
]
DEPLOY_EDITS = [
    (DR_RUN_OLD, DR_RUN_NEW),
    (DR_APPLY_OLD, DR_APPLY_NEW),
    (DR_ADD_OLD, DR_ADD_NEW),
    (DR_LOOP_OLD, DR_LOOP_NEW),
    (DR_CLUSTER_OLD, DR_CLUSTER_NEW),
]


def _apply_one(text: str, edits: list, name: str) -> str:
    crlf = "\r\n" in text
    body = text.replace("\r\n", "\n")
    if MARKER in body:
        return text
    for old, new in edits:
        if body.count(old) != 1:
            raise PatchError(
                f"{name}: anchor not found exactly once ({body.count(old)} matches): "
                f"{old.strip().splitlines()[0]!r}. The live file differs from upstream; "
                "patch by hand and keep the marker."
            )
        body = body.replace(old, new)
    return body.replace("\n", "\r\n") if crlf else body


def apply(text_overload: str, text_deploy: str) -> tuple[str, str]:
    """Return both files patched. Idempotent per file. Raises PatchError on a missing anchor."""
    return (
        _apply_one(text_overload, OVERLOAD_EDITS, "overload_detection.py"),
        _apply_one(text_deploy, DEPLOY_EDITS, "deploy_rl.py"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    over_path = args.src / "overload_detection.py"
    dep_path = args.src / "deploy_rl.py"
    try:
        over, dep = apply(over_path.read_text(encoding="utf-8"), dep_path.read_text(encoding="utf-8"))
    except PatchError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for path, new in ((over_path, over), (dep_path, dep)):
        old = path.read_text(encoding="utf-8")
        if new == old:
            print(f"{path.name}: already patched")
            continue
        if args.dry_run:
            print(f"{path.name}: would patch")
            continue
        shutil.copy2(path, path.with_name(f"{path.name}.orig-{stamp}"))
        path.write_text(new, encoding="utf-8")
        print(f"{path.name}: patched (backup {path.name}.orig-{stamp})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

The marker reaches `deploy_rl.py` through `DR_RUN_NEW`'s comment line and `overload_detection.py` through `OD_IMPORT_NEW`. Both are asserted by `test_marker_is_in_both_files_and_apply_is_idempotent`. Because `_apply_one` returns early when the marker is already present, a second run changes nothing.

- [ ] **Step 5: Run the tests**

Run: `python -m pytest experiments/test_patch_rl_timeout.py -v`
Expected: 7 passed (or `skipped` for the fixture-based ones only if the submodule is not checked out; then run `git submodule update --init` and re-run). If `test_the_three_callers_catch_the_exception` fails on the count, print `dep.count("except ProxyStatsUnavailable")`: it must be 4 (`run` rps, `run` apply_v2, `add_apis`, main loop).

- [ ] **Step 6: Write the failing runner check for the patch marker**

Append to `experiments/test_run_scenario_proxy_guard.py`:

```python
def test_verify_rl_patch_passes_when_the_marker_is_in_both_files():
    out = mock.Mock(stdout="2\n", returncode=0)
    with mock.patch.object(run_scenario, "ssh", return_value=out) as ssh, \
            mock.patch.object(run_scenario, "step"):
        run_scenario.verify_rl_patch("m", "/src")
    cmd = ssh.call_args[0][1]
    assert "RL_TIMEOUT_PATCH v1" in cmd
    assert "/src/overload_detection.py" in cmd and "/src/deploy_rl.py" in cmd


def test_verify_rl_patch_aborts_when_a_file_lacks_the_marker():
    out = mock.Mock(stdout="1\n", returncode=0)
    with mock.patch.object(run_scenario, "ssh", return_value=out):
        with pytest.raises(RuntimeError, match="patch_rl_timeout"):
            run_scenario.verify_rl_patch("m", "/src")


def test_rl_start_checks_the_patch_and_rl_off_does_not():
    cfg = _rl_off_cfg()
    with mock.patch.object(run_scenario, "write_remote_script"), \
            mock.patch.object(run_scenario, "ssh", return_value=mock.Mock(stdout="x deploy_rl.py", returncode=0)), \
            mock.patch.object(run_scenario, "wait_with_progress"), \
            mock.patch.object(run_scenario, "verify_proxy_nofile"), \
            mock.patch.object(run_scenario, "ensure_proxy_uncapped"), \
            mock.patch.object(run_scenario, "verify_rl_patch") as patch_check:
        run_scenario.start_master_stack(cfg)
        patch_check.assert_not_called()
        cfg["topfull_rl"] = {"enabled": True}
        run_scenario.start_master_stack(cfg)
        patch_check.assert_called_once_with("m", "/src")
```

Run: `python -m pytest experiments/test_run_scenario_proxy_guard.py -v`
Expected: the three new tests FAIL with `AttributeError: module 'run_scenario' has no attribute 'verify_rl_patch'`.

- [ ] **Step 7: Implement the runner check**

In `experiments/run_scenario.py`, next to `verify_proxy_nofile` add:

```python
RL_PATCH_MARKER = "RL_TIMEOUT_PATCH v1"  # keep equal to patch_rl_timeout.MARKER


def verify_rl_patch(master: str, src: str) -> None:
    """Abort a TopFull-on hold if master's RL files lack the timeout patch.

    The patch lives in master's live TopFull copy, not in this repo; the runner does
    not copy TopFull files. Without it `current_rps()` can block with no timeout.
    """
    out = ssh(
        master,
        f"grep -l '{RL_PATCH_MARKER}' {src}/overload_detection.py {src}/deploy_rl.py | wc -l",
        check=False,
    ).stdout or ""
    if out.strip() != "2":
        raise RuntimeError(
            f"master's overload_detection.py / deploy_rl.py lack '{RL_PATCH_MARKER}'. "
            "Run experiments/patch_rl_timeout.py on master "
            "(plan 2026-10-16, Task 6) before a TopFull-on hold."
        )
    step("RL timeout patch present on master [OK]")
```

In `_start_master_stack_after_kill`, inside `if rl_enabled:` and **before** `rl_script = (`, add `verify_rl_patch(master, src)`. Add to `TestStartMasterStackTopfullRl.setUp`, `TestTopfullStdoutLogs.setUp` and `TestOverlappedStartup.setUp` (all three call `start_master_stack` with RL on in some test) a patcher:

```python
        rlpatch = mock.patch("run_scenario.verify_rl_patch")
        rlpatch.start()
        self.addCleanup(rlpatch.stop)
```

Add a test to `test_patch_rl_timeout.py` that keeps the two marker constants equal:

```python
def test_runner_and_patch_agree_on_the_marker():
    import run_scenario
    assert run_scenario.RL_PATCH_MARKER == prt.MARKER
```

- [ ] **Step 8: Run all affected tests**

Run: `python -m pytest experiments/test_patch_rl_timeout.py experiments/test_run_scenario_proxy_guard.py experiments/test_run_scenario.py -q`
Expected: all pass.

- [ ] **Step 9: Write the deviation record and the AGENTS.md lines**

Create `Guides and Info/TOPFULL-UPSTREAM-DEVIATIONS.md`:

```markdown
# Deviations from upstream TopFull in the live copy

The repo's `TopFull/` submodule is upstream (kaist-ina/TopFull) and is not edited. The live copy on master (`/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/`) already differs from it by path rewrites and Ron's local edits ([RON-NEZER-SETUP-VS-WORKSHOP.md](RON-NEZER-SETUP-VS-WORKSHOP.md)). This file lists changes **we** made to TopFull's code, so a paper reader can tell what ran.

## 1. RL loop proxy timeout and log lines (2026-10-16, plan [2026-10-16-proxy-fd-limit-and-rl-stall-flag.md](../docs/superpowers/plans/2026-10-16-proxy-fd-limit-and-rl-stall-flag.md))

| File on master | Change | Why |
|---|---|---|
| `overload_detection.py` | `Detector.current_rps()` calls `requests.get(..., timeout=2.0)`; on failure raises `ProxyStatsUnavailable`. New `RL_RPS_*` and `RL_CAP_APPLY` print lines | Upstream has no timeout. When the proxy ran out of file descriptors on 2026-10-15 the call blocked the RL loop for 422 s and 559 s ([evidence](2026-10-15-proxy-fd-evidence-flagged-holds.md)) |
| `deploy_rl.py` | `Agent.run()`, `Agent.add_apis()` and the main loop catch `ProxyStatsUnavailable` and skip that tick. New `RL_LOOP_START` and `RL_SKIP` print lines | The skipped tick retries on the next one (every 1-2 s) |

Applied by `experiments/patch_rl_timeout.py` (marker `RL_TIMEOUT_PATCH v1`); the runner refuses a TopFull-on hold if the marker is missing. Originals are kept as `*.orig-<timestamp>` next to the files on master.

**Behavior.** When the proxy answers, the data, the decisions, and the caps are identical to upstream. The only changed behavior is the failure case: upstream waits until the proxy answers (or forever); the patched loop waits 2 s and retries on its next tick. That is a robustness fix, not a change to the control algorithm. It is still a change to TopFull's code.

**Open decision (user and mentors):** do the mentors accept a modified TopFull for the paper, with this table as the disclosure? If not, the alternative is to leave TopFull untouched and rely only on the descriptor fix: with the limit raised the stall should not occur, and the `RL STALL` flag would then mark any hold where it still does. Until answered, holds run with the patch are labelled by this file, not silently.
```

In `AGENTS.md` §3 guides table add the row:

```
| [TOPFULL-UPSTREAM-DEVIATIONS.md](Guides%20and%20Info/TOPFULL-UPSTREAM-DEVIATIONS.md) | See what we changed in TopFull's code on master versus upstream (the RL timeout patch). The `TopFull/` submodule stays upstream |
```
(The §7 "known fixes" sentence is written in Task 8, not here.)

- [ ] **Step 10: Commit (only if the user asked)**

```powershell
git add experiments/patch_rl_timeout.py experiments/test_patch_rl_timeout.py experiments/run_scenario.py experiments/test_run_scenario.py experiments/test_run_scenario_proxy_guard.py "Guides and Info/TOPFULL-UPSTREAM-DEVIATIONS.md" AGENTS.md
git commit -m "feat: RL loop proxy timeout patch, RL_* log lines, and a runner check for the patch"
```

---

### Task 4: The `RL STALL` and `PROXY FD` flags, and the corrected validity wording

**Files:**
- Modify: `experiments/topfull_health.py`
- Modify: `experiments/test_topfull_health.py`
- Modify: `experiments/analysis_score.py` (`score_run`, `render`, imports)
- Modify: `experiments/test_analysis_score.py`
- Modify: `experiments/throttle_flags.py` (`guide_note`; `HoldFlag.would_flag`, `suspected_text`, the `suspected` subcommand), `experiments/test_throttle_flags.py`
- Create: `experiments/retire_stay_valid.py`, `experiments/test_retire_stay_valid.py`
- Modify: `AGENTS.md` (§6 after-hold paragraph), `Guides and Info/METRICS-GATHERED.md`, `Guides and Info/ANALYSIS-TEMPLATE.md` (item 17), guides under `Guides and Info/` that carry the old sentence

**Interfaces:**
- Consumes: Prerequisites (`analysis_score.topfull_enabled`, `throttle_flags.guide_note`).
- Produces: `topfull_health.Health` (frozen dataclass: `assessable: bool`, `rl_stall: bool`, `proxy_fd: bool`, `reasons: tuple[str, ...]`, property `status: str` in `{"ok", "RL STALL", "PROXY FD", "RL STALL + PROXY FD", NOT_ASSESSABLE}`); `topfull_health.assess(run_dir: Path, topfull_on: bool = True) -> Health`; constants `RL_SILENCE_S = 30`, `RL_RPS_SLOW_S = 3.0`, `FD_FILE`, `EMFILE_TEXT`, `NOT_ASSESSABLE`; `score_run(...)["proxy_rl_health"]` (a `Health`); a `## Proxy and RL health` table in `analysis_score.render`.

**Definitions (chosen here; the tests pin them).**

| Flag | Applies to | Fires when (any) |
|---|---|---|
| `RL STALL` | TopFull-on holds that have `topfull_rl.log` | the RL log is silent longer than **30 s** (including the wait from its last line to the end of the hold); any `RL_RPS_TIMEOUT` line; any `RL_RPS_END` with `elapsed_s` above **3.0** |
| `PROXY FD` | **every** variant that has a proxy log or `proxy_fds.csv` | the proxy log has any `too many open files` line; any `proxy_fds.csv` row with `open_fds >= soft_limit` (and `soft_limit > 0`) |
| `PROXY STALL SUSPECTED` (Decided (f)) | **every** variant that has **no** proxy log and no `proxy_fds.csv` | `topfull_throttle_collector.log` has any `fetch failed` WARNING or an API goes over 10 s with no fresh read (`throttle_quality()["would_flag"]`). TopFull-off holds included; the throttle flag itself still counts TopFull-on holds only. Meaning: do not assume the numbers are clean, not "re-run". A hold that has logs and collector warnings but no descriptor exhaustion reads `admin timeouts, no fd cause` instead |
| not assessable | holds with no `topfull_proxy.log`, no `proxy_fds.csv`, and (TopFull-on) no `topfull_rl.log` | every hold before 2026-10-15 and every `campaign_48/` / `august_38/` folder. Reported as `not assessable`, never as `ok` |

Why 30 s: the RL main loop prints a heartbeat every 2 s and each agent thread every 1 s, so a healthy patched log has no gap over about 2 s and 30 s is 15 ticks; it also equals the old throttle stale rule and `topfull_health.RL_SILENCE_S`, which this file already printed as `rl_silent_over_30s`. The observed stalls were 422 s and 559 s, so the verdict does not depend on the exact N. On a pre-patch log (no `RL_*` lines) only the silence rule can fire, so the flag is conservative there. The flags are independent of the throttle flag: an RL stall with fresh admin reads still flags, and a throttle flag does not by itself raise `RL STALL`. `RL STALL` is never raised for a TopFull-off hold (no RL loop exists); `PROXY FD` is.

- [ ] **Step 1: Write the failing health tests**

Append to `experiments/test_topfull_health.py` (before `if __name__ == "__main__":`):

```python
def fd_csv(path: Path, rows: list[tuple[str, int, int]]) -> None:
    lines = ["timestamp,pid,open_fds,soft_limit"]
    lines += [f"2026-10-14T{hms}Z,4242,{fds},{soft}" for hms, fds, soft in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestAssess(unittest.TestCase):
    def _base(self, tmp: Path, end="12:00:20"):
        write(tmp / "topfull_throttle_collector.log", [
            ("12:00:00", "START  poll_interval=1s"),
            (end, "SHUTDOWN  signal=15"),
        ])

    def _healthy_rl(self, tmp: Path):
        rows = [(f"12:00:{s:02d}", f"RL_LOOP_START iter={s // 2}") for s in range(0, 21, 2)]
        rows.append(("12:00:03", "RL_RPS_START caller=agent"))
        rows.append(("12:00:03", "RL_RPS_END caller=agent elapsed_s=0.01 ok=1"))
        write(tmp / "topfull_rl.log", rows)

    def test_a_healthy_patched_hold_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            self._healthy_rl(tmp)
            write(tmp / "topfull_proxy.log", [("12:00:01", TICK)])
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 40, 1048576), ("12:00:02", 90, 1048576)])
            h = topfull_health.assess(tmp)
        self.assertTrue(h.assessable)
        self.assertEqual(h.status, "ok")
        self.assertEqual(h.reasons, ())

    def test_rl_silence_flags_even_when_the_throttle_log_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp, end="12:01:20")  # throttle collector alive to the end
            write(tmp / "topfull_rl.log", [("12:00:00", "RL_LOOP_START iter=1"),
                                           ("12:00:02", "RL_LOOP_START iter=2")])
            h = topfull_health.assess(tmp)
        self.assertTrue(h.rl_stall)
        self.assertFalse(h.proxy_fd)
        self.assertEqual(h.status, "RL STALL")
        self.assertIn("silent 78 s", h.reasons[0])

    def test_a_timeout_line_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            write(tmp / "topfull_rl.log", [
                ("12:00:01", "RL_LOOP_START iter=1"),
                ("12:00:03", "RL_RPS_TIMEOUT caller=clustering elapsed_s=2.01 timeout_s=2.0 error=ReadTimeout"),
                ("12:00:05", "RL_LOOP_START iter=2"),
            ] + [(f"12:00:{s:02d}", "RL_LOOP_START iter=9") for s in range(7, 21, 2)])
            h = topfull_health.assess(tmp)
        self.assertTrue(h.rl_stall)
        self.assertIn("RL_RPS_TIMEOUT", " ".join(h.reasons))

    def test_a_slow_call_flags_and_a_fast_one_does_not(self):
        for elapsed, expected in (("4.20", True), ("0.01", False)):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self._base(tmp)
                rows = [(f"12:00:{s:02d}", "RL_LOOP_START iter=1") for s in range(0, 21, 2)]
                rows.append(("12:00:05", f"RL_RPS_END caller=agent elapsed_s={elapsed} ok=1"))
                write(tmp / "topfull_rl.log", rows)
                self.assertEqual(topfull_health.assess(tmp).rl_stall, expected, elapsed)

    def test_accept_error_in_the_proxy_log_flags_a_topfull_off_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            write(tmp / "topfull_proxy.log", [
                ("12:00:01", TICK),
                ("12:00:09", "http: Accept error: accept tcp [::]:8090: accept4: too many open files; retrying in 5ms"),
            ])
            h = topfull_health.assess(tmp, topfull_on=False)
        self.assertTrue(h.proxy_fd)
        self.assertFalse(h.rl_stall)
        self.assertEqual(h.status, "PROXY FD")
        self.assertIn("first 12:00:09Z", h.reasons[0])

    def test_a_topfull_off_hold_is_never_rl_stall(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp, end="12:05:00")
            write(tmp / "topfull_rl.log", [("12:00:00", "x")])  # would be silent for 300 s
            write(tmp / "topfull_proxy.log", [("12:00:01", TICK)])
            h = topfull_health.assess(tmp, topfull_on=False)
        self.assertFalse(h.rl_stall)

    def test_descriptor_csv_at_the_limit_flags_and_below_it_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 600, 1024), ("12:00:02", 1024, 1024)])
            h = topfull_health.assess(tmp, topfull_on=False)
            self.assertTrue(h.proxy_fd)
            self.assertIn("reached the soft limit 1024", h.reasons[0])
            self.assertIn("peak 1024", h.reasons[0])
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 600, 1024), ("12:00:02", 1023, 1024)])
            self.assertFalse(topfull_health.assess(tmp, topfull_on=False).proxy_fd)

    def test_unlimited_soft_limit_never_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 900000, -1)])
            self.assertFalse(topfull_health.assess(tmp, topfull_on=False).proxy_fd)

    def test_both_flags_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp, end="12:02:00")
            write(tmp / "topfull_rl.log", [("12:00:00", "RL_LOOP_START iter=1")])
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 1024, 1024)])
            self.assertEqual(topfull_health.assess(tmp).status, "RL STALL + PROXY FD")

    def test_an_old_hold_is_not_assessable_and_not_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)  # only the throttle collector log, like every pre-2026-10-15 hold
            h = topfull_health.assess(tmp)
        self.assertFalse(h.assessable)
        self.assertFalse(h.rl_stall or h.proxy_fd)
        self.assertEqual(h.status, topfull_health.NOT_ASSESSABLE)
        self.assertNotEqual(h.status, "ok")

    def test_a_topfull_off_hold_without_proxy_logs_is_not_assessable(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            write(tmp / "topfull_rl.log", [("12:00:00", "x")])
            self.assertFalse(topfull_health.assess(tmp, topfull_on=False).assessable)

    def test_report_has_a_health_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            self._healthy_rl(tmp)
            self.assertIn("health: ok", topfull_health.report(tmp))
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest experiments/test_topfull_health.py -v`
Expected: the new tests FAIL with `AttributeError: module 'topfull_health' has no attribute 'assess'`. The five older tests still PASS.

- [ ] **Step 3: Implement `assess` in `topfull_health.py`**

Add to the imports `import csv`. After the `RL_SILENCE_S = 30` line add:

```python
FD_FILE = "proxy_fds.csv"
EMFILE_TEXT = "too many open files"
RL_RPS_SLOW_S = 3.0
NOT_ASSESSABLE = "not assessable (no proxy, descriptor, or RL log)"
KV = re.compile(r"(\w+)=(\S+)")
```

After `rl_line` add:

```python
@dataclass(frozen=True)
class Health:
    assessable: bool
    rl_stall: bool
    proxy_fd: bool
    reasons: tuple

    @property
    def status(self) -> str:
        if not self.assessable:
            return NOT_ASSESSABLE
        names = [n for n, on in (("RL STALL", self.rl_stall), ("PROXY FD", self.proxy_fd)) if on]
        return " + ".join(names) if names else "ok"


def _fd_rows(path: Path) -> list[tuple[datetime, int, int]]:
    rows = []
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                rows.append((parse_ts(row["timestamp"]), int(row["open_fds"]), int(row["soft_limit"])))
            except (KeyError, ValueError):
                continue
    return rows


def assess(run_dir: Path, topfull_on: bool = True) -> Health:
    """RL STALL (TopFull-on only) and PROXY FD (every variant) for one hold.

    Independent of the throttle flag. A hold with none of the logs is not assessable.
    """
    run_dir = Path(run_dir)
    proxy_path, rl_path, fd_path = run_dir / PROXY_LOG, run_dir / RL_LOG, run_dir / FD_FILE
    _, end = throttle_times(run_dir)
    reasons: list[str] = []
    proxy_fd = rl_stall = False
    assessable = proxy_path.exists() or fd_path.exists() or (topfull_on and rl_path.exists())

    if proxy_path.exists():
        hits = [t for t, text in read_stamped(proxy_path) if EMFILE_TEXT in text]
        if hits:
            proxy_fd = True
            reasons.append(f"proxy log has {len(hits)} '{EMFILE_TEXT}' lines, first {_fmt(hits[0])}")
    if fd_path.exists():
        rows = _fd_rows(fd_path)
        peak = max((fds for _, fds, _ in rows), default=0)
        hit = next(((t, soft) for t, fds, soft in rows if soft > 0 and fds >= soft), None)
        if hit is not None:
            proxy_fd = True
            reasons.append(
                f"open fds reached the soft limit {hit[1]} at {_fmt(hit[0])} (peak {peak})"
            )
    if topfull_on and rl_path.exists():
        entries = read_stamped(rl_path)
        gap = longest_gap([t for t, _ in entries], end)
        if gap.seconds > RL_SILENCE_S:
            rl_stall = True
            reasons.append(f"RL log silent {gap.seconds:.0f} s from {_fmt(gap.start)}")
        timeouts = [t for t, text in entries if text.startswith("RL_RPS_TIMEOUT")]
        if timeouts:
            rl_stall = True
            reasons.append(f"{len(timeouts)} RL_RPS_TIMEOUT lines, first {_fmt(timeouts[0])}")
        slow = [
            t for t, text in entries
            if text.startswith("RL_RPS_END") and float(dict(KV.findall(text)).get("elapsed_s", 0)) > RL_RPS_SLOW_S
        ]
        if slow:
            rl_stall = True
            reasons.append(f"{len(slow)} current_rps calls over {RL_RPS_SLOW_S:g} s, first {_fmt(slow[0])}")
    return Health(assessable, rl_stall, proxy_fd, tuple(reasons))
```

Change `report` to take and use it:

```python
def report(run_dir: Path, topfull_on: bool = True) -> str:
    first_fail, end = throttle_times(run_dir)
    health = assess(run_dir, topfull_on)
    detail = f" ({'; '.join(health.reasons)})" if health.reasons else ""
    return "\n".join([
        f"TopFull health: {run_dir.name}",
        f"throttle: first_fetch_failure={_fmt(first_fail)} end={_fmt(end)}",
        proxy_line(run_dir, end),
        rl_line(run_dir, end),
        f"health: {health.status}{detail}",
    ])
```

In `main`, replace `print(report(Path(arg)))` with:

```python
    for arg in argv:
        run_dir = Path(arg)
        print(report(run_dir, _topfull_on(run_dir)))
        print()
```
and add above `main`:

```python
def _topfull_on(run_dir: Path) -> bool:
    """run_manifest.json says whether the RL loop was on; imported lazily (analysis_score imports this module)."""
    try:
        import analysis_score
    except ImportError:
        return True
    return analysis_score.topfull_enabled(run_dir)
```
Also update the module docstring's last sentence: `Holds pulled before 2026-10-15 have no proxy or RL log; the report says "missing" for those and the health line says "not assessable".`

- [ ] **Step 4: Run the health tests**

Run: `python -m pytest experiments/test_topfull_health.py -v`
Expected: all pass (5 old + 12 new).

- [ ] **Step 5: Write the failing scorer test**

Append to `class TestThrottleQuality` neighbour — add a new class at the end of `experiments/test_analysis_score.py` (before any `if __name__` block):

```python
class TestProxyRlHealth(unittest.TestCase):
    def _hold(self, tmp: str, *, topfull_on: bool, proxy_lines: list[str]):
        folder = Path(tmp) / "final_s2_rg_only_normal_run9"
        folder.mkdir()
        (folder / "run_manifest.json").write_text(
            '{"topfull_rl": {"enabled": %s}}' % ("true" if topfull_on else "false"), encoding="utf-8")
        _write(
            folder / "topfull_throttle.csv",
            ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"],
            [["2026-10-13T00:00:00Z", "getproduct", 10000, 0, 1, 1],
             ["2026-10-13T00:00:05Z", "getproduct", 10000, 0, 1, 1]],
        )
        if proxy_lines:
            (folder / "topfull_proxy.log").write_text("\n".join(proxy_lines) + "\n", encoding="utf-8")
        return folder

    def test_proxy_fd_is_a_separate_table_and_flags_a_topfull_off_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, proxy_lines=[
                "2026-10-13T00:00:02Z  http: Accept error: accept tcp [::]:8090: accept4: too many open files",
            ])
            item = score.score_run(folder)
            text = score.render([item], ["9"])
        self.assertEqual(item["proxy_rl_health"].status, "PROXY FD")
        self.assertIn("## Proxy and RL health", text)
        self.assertIn("| 9 | **PROXY FD** |", text)
        self.assertIn("| 9 | N/A: TopFull off |", text)  # the throttle table is unchanged

    def test_old_hold_reads_not_assessable(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=True, proxy_lines=[])
            text = score.render([score.score_run(folder)], ["9"])
        self.assertIn("| 9 | not assessable |", text)
        self.assertNotIn("| 9 | ok |", text.split("## Proxy and RL health")[1].split("##")[0])
```

Run: `python -m pytest experiments/test_analysis_score.py::TestProxyRlHealth -v`
Expected: FAIL with `KeyError: 'proxy_rl_health'`.

- [ ] **Step 6: Implement the scorer integration**

In `experiments/analysis_score.py`, add near the other module imports: `import topfull_health`. In `score_run`, directly after the `"throttle_quality": throttle_quality(...)` entry's closing `),` add:

```python
        "proxy_rl_health": topfull_health.assess(run_dir, topfull_on=topfull_enabled(run_dir)),
```
(If `score_run` builds that dict as a `return {...}`, the key goes inside it; if it assigns `item = {...}`, inside that.)

In `render`, after the throttle table loop (the `lines.append("")` that follows the last `lines.append(f"| {label} | {status} | ...")`) and before `lines.append("## TopFull live caps")`, insert:

```python
    lines.append("## Proxy and RL health")
    lines.append("")
    lines.append(
        "Separate from the throttle flag. **PROXY FD**: the Go proxy ran out of file descriptors "
        "(`too many open files` in `topfull_proxy.log`, or `proxy_fds.csv` reached its soft limit). "
        "It refuses new connections on every variant, `rg_only` and `both_off` included, so "
        "goodput, P95, rejection, and retry numbers of that hold are not assumed clean. "
        "**RL STALL** (TopFull on only): the RL loop was silent over 30 s, a `current_rps` call "
        "timed out or took over 3 s; caps stopped moving. `not assessable` means the hold has no "
        "proxy, descriptor, or RL log (every hold before 2026-10-15)."
    )
    lines.append("")
    lines.append("| Hold | Status | Detail |")
    lines.append("| --- | --- | --- |")
    for label, item in zip(labels, scored):
        health = item["proxy_rl_health"]
        if not health.assessable:
            status = "not assessable"
        elif health.rl_stall or health.proxy_fd:
            status = f"**{health.status}**"
        else:
            status = "ok"
        lines.append(f"| {label} | {status} | {'; '.join(health.reasons) or '—'} |")
    lines.append("")
```

Run: `python -m pytest experiments/test_analysis_score.py experiments/test_topfull_health.py -q`
Expected: all pass.

- [ ] **Step 6a: Write the failing tests for `PROXY STALL SUSPECTED` (Decided (f))**

Append to `experiments/test_analysis_score.py` (after `TestProxyRlHealth`):

```python
class TestProxyStallSuspected(unittest.TestCase):
    def _hold(self, tmp: str, *, topfull_on: bool, warnings: int, proxy_lines: list[str]):
        folder = Path(tmp) / "final_s2_rg_only_normal_run9"
        folder.mkdir()
        (folder / "run_manifest.json").write_text(
            '{"topfull_rl": {"enabled": %s}}' % ("true" if topfull_on else "false"), encoding="utf-8")
        _write(
            folder / "topfull_throttle.csv",
            ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"],
            [["2026-10-13T00:00:00Z", "getproduct", 10000, 0, 1, 1],
             ["2026-10-13T00:00:05Z", "getproduct", 10000, 0, 1, 1]],
        )
        lines = ["2026-10-13T00:00:00Z  START  x"]
        lines += [f"2026-10-13T00:00:0{i % 10}Z  WARNING  stats fetch failed: timed out"
                  for i in range(warnings)]
        (folder / "topfull_throttle_collector.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if proxy_lines:
            (folder / "topfull_proxy.log").write_text("\n".join(proxy_lines) + "\n", encoding="utf-8")
        return folder

    def test_throttle_quality_reports_would_flag_for_a_topfull_off_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=3, proxy_lines=[])
            q = score.score_run(folder)["throttle_quality"]
        self.assertFalse(q["flagged"])        # the throttle flag is unchanged: TopFull off
        self.assertTrue(q["would_flag"])      # the collector evidence is still there

    def test_topfull_off_hold_with_collector_warnings_is_suspected_not_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=3, proxy_lines=[])
            text = score.render([score.score_run(folder)], ["9"])
        self.assertIn("| 9 | N/A: TopFull off |", text)             # throttle table unchanged
        health = text.split("## Proxy and RL health")[1]
        self.assertIn("| 9 | **PROXY STALL SUSPECTED** |", health)
        self.assertIn("3 fetch warning", health)
        self.assertIn("no proxy or descriptor log", health)

    def test_clean_old_hold_stays_not_assessable(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=0, proxy_lines=[])
            text = score.render([score.score_run(folder)], ["9"])
        health = text.split("## Proxy and RL health")[1]
        self.assertIn("| 9 | not assessable |", health)
        self.assertNotIn("SUSPECTED", health)

    def test_logged_hold_with_timeouts_but_no_fd_cause_is_named_not_suspected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=3, proxy_lines=[
                "2026-10-13T00:00:01Z  monitor tick"])
            text = score.render([score.score_run(folder)], ["9"])
        health = text.split("## Proxy and RL health")[1]
        self.assertIn("| 9 | admin timeouts, no fd cause |", health)
        self.assertNotIn("SUSPECTED", health)

    def test_proxy_fd_still_wins_over_suspected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=3, proxy_lines=[
                "2026-10-13T00:00:02Z  http: Accept error: accept tcp [::]:8090: accept4: too many open files"])
            text = score.render([score.score_run(folder)], ["9"])
        health = text.split("## Proxy and RL health")[1]
        self.assertIn("| 9 | **PROXY FD** |", health)
        self.assertNotIn("SUSPECTED", health)
```

Append to `experiments/test_throttle_flags.py`, inside `class TestScan` after the existing scan tests (the `make_hold` helper writes `topfull_throttle.csv` and the collector log with `warnings` `WARNING ... fetch failed` lines):

```python
    def test_topfull_off_hold_is_not_flagged_but_is_suspected(self):
        flags = self.scan(lambda r: make_hold(
            r, "S2_sustained_overload_burst", "rg_only", "run_off", warnings=4))
        h = flags[0]
        self.assertFalse(h.flagged)       # the throttle flag stays TopFull-on only
        self.assertTrue(h.would_flag)     # collector evidence of a proxy stall
        self.assertFalse(h.topfull_on)

    def test_clean_topfull_off_hold_is_not_suspected(self):
        flags = self.scan(lambda r: make_hold(
            r, "S2_sustained_overload_burst", "rg_only", "run_off_clean"))
        self.assertFalse(flags[0].would_flag)
```

and, at the top of the file with the other imports, `import dataclasses`. Then a new class at the end of the file (before any `if __name__` block):

```python
class TestSuspected(unittest.TestCase):
    def test_suspected_text_counts_both_variants_and_lists_holds(self):
        flags = [
            hold("a", on=True),
            hold("b", on=False, flagged=False),
            hold("c", on=False, flagged=False),
        ]
        flags = [dataclasses.replace(h, would_flag=True) for h in flags[:2]] + flags[2:]
        text = throttle_flags.suspected_text(flags)
        self.assertEqual(
            text.splitlines()[0],
            "runs=3 suspected=2 suspected_topfull_off=1 suspected_topfull_on=1")
        self.assertIn("S2_sustained_overload_burst/rg_only/b  off", text)
        self.assertNotIn("/c ", text)
```

Run: `python -m pytest experiments/test_analysis_score.py::TestProxyStallSuspected experiments/test_throttle_flags.py -q`
Expected: FAIL (`KeyError: 'would_flag'`, `AttributeError: ... has no attribute 'would_flag'` / `suspected_text`).

- [ ] **Step 6b: Implement in `analysis_score.py`**

In `throttle_quality`, add one key to the returned dict, next to `"flagged"`:

```python
        "would_flag": bool(would_flag),
```

Directly above `def mesh_gate`, add:

```python
SUSPECTED = "PROXY STALL SUSPECTED"


def proxy_stall_status(quality: dict, health) -> tuple[str, str]:
    """(status, detail) for one row of the Proxy and RL health table.

    Direct evidence (`PROXY FD`, `RL STALL`) wins. Without a proxy, descriptor, or RL
    log (every hold before 2026-10-15) the throttle collector's own warnings and stale
    stretches are the only record of a proxy stall, and they exist on every variant,
    TopFull off included. A hold with logs and collector warnings but no descriptor
    exhaustion is named, not accused: the timeouts then have another cause.
    """
    if health.rl_stall or health.proxy_fd:
        return f"**{health.status}**", "; ".join(health.reasons) or "—"
    evidence = bool(quality.get("would_flag") and quality.get("has_csv"))
    worst = max([g for g in (quality.get("threshold_gap_s"), quality.get("admitted_gap_s"))
                 if g is not None], default=0.0)
    seen = (f"throttle collector: {quality.get('warnings', 0)} fetch warning(s), "
            f"longest no-fresh read {worst:.0f} s")
    if not health.assessable:
        if evidence:
            return f"**{SUSPECTED}**", f"{seen}; no proxy or descriptor log to confirm"
        return "not assessable", "no proxy, descriptor, or RL log"
    if evidence:
        return "admin timeouts, no fd cause", f"{seen}; the proxy log and descriptor file show no exhaustion"
    return "ok", "—"
```

Replace the status block of the `## Proxy and RL health` loop in `render` (the lines from `health = item["proxy_rl_health"]` through the `lines.append(f"| {label} | {status} | ...")`) with:

```python
        health = item["proxy_rl_health"]
        status, detail = proxy_stall_status(item["throttle_quality"], health)
        lines.append(f"| {label} | {status} | {detail} |")
```

and add one sentence to the paragraph above that table: `**PROXY STALL SUSPECTED**: no proxy or descriptor log exists, but the throttle collector saw fetch warnings or a stale stretch, which on any variant (TopFull off included) is the only trace of a proxy stall; do not assume the hold's goodput, P95, rejection, and retry numbers are clean.`

- [ ] **Step 6c: Implement in `throttle_flags.py`**

Add the label next to `TF_OFF_LABEL`:

```python
PROXY_SUSPECT_LABEL = "PROXY STALL SUSPECTED"
```

Add the last field to `HoldFlag` (a default, so `hold()` in the tests keeps working):

```python
    would_flag: bool = False
```

In `scan_hold`, add to the `HoldFlag(...)` call:

```python
        would_flag=bool(quality["would_flag"] and quality["has_csv"]),
```

Below `audit_text` add:

```python
def suspected_text(flags: list[HoldFlag]) -> str:
    """Holds whose collector log suggests a proxy stall, any variant (Decided (f))."""
    sus = [h for h in flags if h.would_flag]
    off = [h for h in sus if not h.topfull_on]
    lines = [
        f"runs={len(flags)} suspected={len(sus)} "
        f"suspected_topfull_off={len(off)} suspected_topfull_on={len(sus) - len(off)}",
    ]
    for h in sus:
        lines.append(
            f"{h.path}  {'on' if h.topfull_on else 'off'}  warnings={h.warnings}  "
            f"gap_s={h.threshold_gap_s:.0f}/{h.admitted_gap_s:.0f}"
        )
    return "\n".join(lines)
```

In `main`, change the tuple to `("audit", "status", "guides", "rerun", "suspected")` and add, after the `audit` branch:

```python
    if args.cmd == "suspected":
        print(suspected_text(flags))
        return 0
```

Leave `label()`, `TF_OFF_LABEL`, `audit_text`, and the gate line `runs=146 flagged=27 ...` unchanged: the throttle flag still counts TopFull-on only.

- [ ] **Step 6d: Run the tests and check the live tree**

Run: `python -m pytest experiments/test_analysis_score.py experiments/test_throttle_flags.py experiments/test_topfull_health.py -q`
Expected: all pass.

Run: `python experiments/throttle_flags.py suspected`
Expected first line: `runs=146 suspected=52 suspected_topfull_off=25 suspected_topfull_on=27` (25 = the TopFull-off flags of the original audit; the 27 are the TopFull-on flags). Run `python experiments/throttle_flags.py audit` and confirm its first line is still `runs=146 flagged=27 topfull_on_flagged=27 topfull_off_flagged=0`. If the `suspected` counts differ, stop and compare with the audit before continuing.

Run: `python experiments/analysis_score.py "experiments/results/final results/S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep1"`
Expected: its `Throttle data quality` row says `N/A: TopFull off`, and its `Proxy and RL health` row says `**PROXY STALL SUSPECTED**` with `224 fetch warning(s), longest no-fresh read 565 s`.

- [ ] **Step 7: Stop saying the four numbers "stay valid" — generator and tests**

Write the failing tests first. Create `experiments/test_retire_stay_valid.py`:

```python
"""Tests for retire_stay_valid.py. Run: python -m pytest experiments/test_retire_stay_valid.py -v"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import retire_stay_valid as rsv

OLD_A = "Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid."
OLD_B = "Goodput, P95, rejection, and retry numbers do not use that file and remain valid."
OLD_C = "Goodput, P95 and rejection do not use this file."  # a different, true sentence: not rewritten


def test_both_known_sentences_are_rewritten_and_nothing_else():
    text = f"x {OLD_A} y {OLD_B} z {OLD_C}"
    new, n = rsv.rewrite(text)
    assert n == 2
    assert "stay valid" not in new and "remain valid" not in new
    assert OLD_C in new
    assert new.count(rsv.REPLACEMENT) == 2


def test_rewrite_is_idempotent():
    once, _ = rsv.rewrite(OLD_A)
    twice, n = rsv.rewrite(once)
    assert (twice, n) == (once, 0)


def test_the_evidence_report_and_this_plan_are_skipped(tmp_path):
    (tmp_path / rsv.EVIDENCE).write_text(OLD_A, encoding="utf-8")
    (tmp_path / "other.md").write_text(OLD_A, encoding="utf-8")
    changed = rsv.run(tmp_path, write=True)
    assert changed == {"other.md": 1}
    assert (tmp_path / rsv.EVIDENCE).read_text(encoding="utf-8") == OLD_A


def test_dry_run_writes_nothing(tmp_path):
    (tmp_path / "g.md").write_text(OLD_A, encoding="utf-8")
    assert rsv.run(tmp_path, write=False) == {"g.md": 1}
    assert (tmp_path / "g.md").read_text(encoding="utf-8") == OLD_A


def test_crlf_files_keep_their_endings(tmp_path):
    (tmp_path / "g.md").write_bytes(f"a\r\n{OLD_A}\r\n".encode("utf-8"))
    rsv.run(tmp_path, write=True)
    assert b"\r\n" in (tmp_path / "g.md").read_bytes()
```

Run: `python -m pytest experiments/test_retire_stay_valid.py -v` → expected collection error `ModuleNotFoundError: No module named 'retire_stay_valid'`.

Create `experiments/retire_stay_valid.py`:

```python
"""One-shot: replace the "stay valid / remain valid" sentence in Guides and Info/*.md.

    python experiments/retire_stay_valid.py            # dry run: counts per file
    python experiments/retire_stay_valid.py --write

The throttle-flag notes (and the 2026-10-15 re-run guide) said goodput, P95, rejection, and
retry numbers of a flagged hold stay valid because they do not read topfull_throttle.csv.
The proxy descriptor evidence shows they are not safe to assume: a proxy that ran out of
file descriptors refuses new connections on every variant. Only the two known sentences
are rewritten; leftovers are printed for manual review.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

GUIDES = Path(__file__).resolve().parent.parent / "Guides and Info"
EVIDENCE = "2026-10-15-proxy-fd-evidence-flagged-holds.md"
REPLACEMENT = (
    "Goodput, P95, rejection, and retry numbers do not come from that file, but a proxy that ran "
    f"out of file descriptors refuses new connections on every variant, so whether they are clean "
    f"for this hold is decided by [{EVIDENCE}]({EVIDENCE}), not by this flag."
)
PATTERNS = [
    re.compile(r"Goodput, P95, rejection, and retry numbers do not use `topfull_throttle\.csv` and stay valid\."),
    re.compile(r"Goodput, P95, rejection, and retry numbers do not use that file and remain valid\."),
]


def rewrite(text: str) -> tuple[str, int]:
    total = 0
    for pattern in PATTERNS:
        text, n = pattern.subn(lambda _m: REPLACEMENT, text)
        total += n
    return text, total


def run(guides_dir: Path, write: bool) -> dict:
    changed = {}
    for path in sorted(Path(guides_dir).glob("*.md")):
        if path.name == EVIDENCE:
            continue
        raw = path.read_bytes().decode("utf-8")
        eol = "\r\n" if "\r\n" in raw else "\n"
        new, n = rewrite(raw.replace("\r\n", "\n"))
        if n:
            changed[path.name] = n
            if write:
                path.write_bytes(new.replace("\n", eol).encode("utf-8"))
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    changed = run(GUIDES, args.write)
    for name, n in changed.items():
        print(f"{name}: {n}")
    print(f"{'rewrote' if args.write else 'would rewrite'} {sum(changed.values())} sentence(s) in {len(changed)} file(s)")
    for path in sorted(GUIDES.glob("*.md")):
        if path.name == EVIDENCE:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if re.search(r"(stay|stays|remain)s? valid", line) and "Goodput" in line:
                print(f"REVIEW {path.name}:{number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `python -m pytest experiments/test_retire_stay_valid.py -v` → expected: 5 passed.

Then `throttle_flags.guide_note`: in `experiments/throttle_flags.py` replace the last line of the returned f-string

```python
        f"Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid."
```
with
```python
        "Goodput, P95, rejection, and retry numbers do not come from `topfull_throttle.csv`, but a "
        "proxy that ran out of file descriptors refuses new connections on every variant, so whether "
        "they are clean for this hold is decided by "
        "`2026-10-15-proxy-fd-evidence-flagged-holds.md`, not by this flag."
```
(keep the two strings adjacent inside the existing `return (...)` so Python concatenates them). In `experiments/test_throttle_flags.py` find assertions on that sentence with `rg -n "stay valid" experiments/test_throttle_flags.py` and change each to `self.assertIn("not by this flag", note)` (use the local variable name of that test).

Run: `python -m pytest experiments/test_throttle_flags.py -q` → expected: all pass.

- [ ] **Step 8: Rewrite the guides (dry run first)**

Run: `python experiments/retire_stay_valid.py`
Expected: a list of `<guide>.md: <n>` lines and a final `would rewrite N sentence(s) in M file(s)` with N > 0. Any `REVIEW <file>:<line>` lines are sentences the patterns missed: fix each by hand with the same replacement meaning.

Run: `python experiments/retire_stay_valid.py --write`, then `git diff --stat "Guides and Info"` — expected: only guides that had the sentence changed, each by the sentence only. `python experiments/throttle_flags.py guides` must still show `none` in every `Missing` cell (the `FLAGGED` tokens were not touched).

- [ ] **Step 9: AGENTS.md, ANALYSIS-TEMPLATE.md, METRICS-GATHERED.md wording**

`AGENTS.md` §6 "After every hold" paragraph (after remediation Task 4/9 it reads as the new text). Replace the sentence `Goodput, P95, rejection, and retry numbers do not use that file and remain valid.` with:

```
Goodput, P95, rejection, and retry numbers do not come from that file, but they are not automatically clean: a proxy that ran out of file descriptors refuses new connections on every variant, `rg_only` included (evidence: [2026-10-15-proxy-fd-evidence-flagged-holds.md](Guides%20and%20Info/2026-10-15-proxy-fd-evidence-flagged-holds.md)).
```
Replace the last two sentences of that paragraph (`On a TopFull-on hold, also run python experiments/topfull_health.py ... Holds before 2026-10-15 print missing for both.`) with:

```
On every hold also run `python experiments/topfull_health.py "<run_dir>"` (or read the scorer's `Proxy and RL health` table). Its `health:` line is a second flag, independent of the throttle flag. **PROXY FD** (any variant): `topfull_proxy.log` has `too many open files`, or `proxy_fds.csv` reached its soft limit; treat the hold's goodput, P95, rejection, and retry numbers as not clean, tell the user, and the repeat slot is a bump of `run_number`. **RL STALL** (TopFull-on only): the RL loop was silent over 30 s, or a `current_rps` call timed out or took over 3 s; the cap and admitted-rate numbers describe a controller that stopped adjusting. Holds before 2026-10-15 print `not assessable`, which is not the same as clean; when their throttle collector log shows fetch warnings or a stale stretch (TopFull-off holds included) the scorer's `Proxy and RL health` row reads **PROXY STALL SUSPECTED**, the only trace of a proxy stall those holds have (`python experiments/throttle_flags.py suspected` lists them). Its `proxy:` and `rl:` lines still give the proxy monitor's longest tick gap and the RL loop's longest silence.
```

`Guides and Info/ANALYSIS-TEMPLATE.md` item 17: replace `Goodput, P95, rejection, and retry numbers do not use this file and stay valid.` with:

```
Goodput, P95, rejection, and retry numbers do not come from this file, but do not call them valid on that basis: paste the scorer's `Proxy and RL health` table next. A hold marked **PROXY FD** (the proxy ran out of file descriptors, any variant) has numbers that are not assumed clean; name it and cite its measured effect from [2026-10-15-proxy-fd-evidence-flagged-holds.md](2026-10-15-proxy-fd-evidence-flagged-holds.md). A hold marked **RL STALL** (TopFull on) had a controller that stopped adjusting caps; say so wherever you quote its caps or admitted rate. `not assessable` means a pre-2026-10-15 hold with no proxy or RL log. **PROXY STALL SUSPECTED** is the same warning read from the throttle collector alone, on any variant including TopFull off; name the hold and do not call its numbers clean.
```
and replace `A flagged hold with TopFull off (`rg_only`) has no cap to lose; say so rather than dropping it.` with `A TopFull-off hold (`rg_only`) has no cap to lose, but its proxy can still run out of descriptors; read its `Proxy and RL health` row.`

`Guides and Info/METRICS-GATHERED.md`: extend the `topfull_rl.log` row's description with ``From the Task-3 patch on it also carries `RL_LOOP_START`, `RL_RPS_START/END/TIMEOUT`, `RL_SKIP`, and `RL_CAP_APPLY` lines (format in the plan 2026-10-16), the input to the `RL STALL` flag``. Add a short paragraph after the table: `**Proxy and RL health flags.** topfull_health.assess() (and the scorer's Proxy and RL health table) read topfull_proxy.log, topfull_rl.log, and proxy_fds.csv. PROXY FD applies to every variant; RL STALL only to TopFull-on holds; holds before 2026-10-15 are not assessable.`

- [ ] **Step 10: Run the whole affected set and commit (commit only if the user asked)**

Run: `python -m pytest experiments/test_topfull_health.py experiments/test_analysis_score.py experiments/test_throttle_flags.py experiments/test_throttle_stale.py experiments/test_retire_stay_valid.py -q`
Expected: all pass.

Run: `python experiments/topfull_health.py "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run3"`
Expected: the `health:` line reads `RL STALL` with a `silent 4xx s` reason (the 422 s stall; the exact digits come from the log) and `PROXY FD` with `proxy log has 429 'too many open files' lines, first 13:23:32Z`, so the line is `health: RL STALL + PROXY FD (...)`. This is the one on-disk hold that can prove both rules on real data; if the numbers differ from the evidence report, read the log before trusting the rule.

Run: `python experiments/topfull_health.py "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2"`
Expected: `health: not assessable (no proxy, descriptor, or RL log)`.

```powershell
git add experiments/topfull_health.py experiments/test_topfull_health.py experiments/analysis_score.py experiments/test_analysis_score.py experiments/throttle_flags.py experiments/test_throttle_flags.py experiments/retire_stay_valid.py experiments/test_retire_stay_valid.py AGENTS.md "Guides and Info"
git commit -m "feat: RL STALL and PROXY FD flags; stop calling flagged holds' numbers valid"
```

---

### Task 5: The decision document for the materially affected holds

**Files:**
- Create: `experiments/proxy_fd_decisions.py`
- Create: `experiments/test_proxy_fd_decisions.py`
- Create (generated): `Guides and Info/2026-10-16-proxy-fd-rerun-decisions.md`

**Interfaces:**
- Consumes: `throttle_flags.scan`, `throttle_flags.name_pattern`, `throttle_flags.AUDIT_PATH`, `throttle_flags.DEFAULT_ROOT`; `analysis_score.throttle_quality`, `analysis_score._rows`.
- Produces: `proxy_fd_decisions.AFFECTED` (11 `Hold` rows copied from the evidence report), `legacy_flagged(root) -> list[tuple[str, str, bool]]`, `next_slot(configs_root: Path, yaml_rel: str) -> int`, `render(root: Path, configs_root: Path, audit_text: str) -> str`, CLI `python experiments/proxy_fd_decisions.py [--root DIR] [--out PATH] [--check]`.

**What the document says (all generated, nothing hand-typed except the per-hold effect text copied from the evidence report).**
Section A: the 11 materially affected holds, with variant, TopFull, whether the name starts with `final_` (the locked set), onset, before→after goodput / P95 / rejection, the effect versus clean controls, the YAML that owns the cell, that YAML's next free `run_number` (read from the YAML, which is what STATUS.md "Next free slots" mirrors), and a blank **Decision** column. Section B: the other flagged holds the evidence does not recommend re-running (mild, brief, healthy through the stall), each with its reason. Section C: the flagged S4A-constrained holds that are **confounded** (any stall damage sits on the clean constrained collapse floor, goodput about 40 req/s and rejection about 0.93; confounded does not mean unaffected), derived from the scan, with blank Decision. Section D: the holds missing from the 2026-10-15 audit and the true counts. Preconditions: nothing is re-run until Task 7 passes.

The "flagged" rule for this document is the **collector rule at every variant** (`throttle_quality(..., topfull_on=True)`), because `rg_only` holds are now in scope. That is the audit's rule, so the count must come out 52 of 146.

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_proxy_fd_decisions.py`:

```python
"""Tests for proxy_fd_decisions.py. Run: python -m pytest experiments/test_proxy_fd_decisions.py -v"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import proxy_fd_decisions as pfd

HEADER = "timestamp,api,threshold,admitted_rps,threshold_fresh,admitted_fresh\n"


def make_hold(root: Path, scenario: str, variant: str, name: str, *, flagged: bool):
    d = root / scenario / variant / name
    d.mkdir(parents=True)
    rows = ["2026-10-13T00:00:00Z,getproduct,10000,0,1,1"]
    rows.append("2026-10-13T00:%s:00Z,getproduct,10000,0,1,1" % ("05" if flagged else "00"))
    (d / "topfull_throttle.csv").write_text(HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return d


def make_yaml(configs: Path, rel: str, run_number: int):
    p = configs / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"run_number: {run_number}\nlog_folder: x_run{run_number}\n", encoding="utf-8")


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "final results"
    configs = tmp_path / "final_configs"
    for rel, n in {
        "2/s2_tf_only.yaml": 4, "2/s2_both_burst.yaml": 4, "2/s2_both_normal.yaml": 3,
        "2/s2_rg_only_normal.yaml": 3,
        "4/4a_constrained/4a_constrained_rg_only_burst.yaml": 7,
        "4/4a_constrained/4a_constrained_rg_only_normal.yaml": 5,
        "4/4a_constrained/4a_constrained_tf_only.yaml": 5,
        "4/4a_constrained/4a_constrained_both_burst.yaml": 5,
    }.items():
        make_yaml(configs, rel, n)
    # one of the eleven, flagged
    make_hold(root, "S2_sustained_overload_normal", "tf_only", "final_s2_tf_only_run2", flagged=True)
    # a confounded S4A-constrained hold (flagged, not one of the three affected)
    make_hold(root, "S4A_topology_position_burst", "both", "final_4a_constrained_both_burst_run3", flagged=True)
    # a healthy-through-stall S4A-unconstrained hold (flagged)
    make_hold(root, "S4A_topology_position_burst", "both", "final_4a_unconstrained_both_burst_run2_r2", flagged=True)
    # a clean hold and a folder the audit never saw
    make_hold(root, "S1_normal_operation_normal", "tf_only", "final_s1_tf_only_run1", flagged=False)
    make_hold(root, "S2_sustained_overload_normal", "tf_only", "final_s2_tf_only_run3", flagged=True)
    return root, configs


def test_legacy_flag_counts_every_variant(tree):
    root, _ = tree
    rows = pfd.legacy_flagged(root)
    flagged = {name for name, _variant, f in rows if f}
    assert flagged == {"final_s2_tf_only_run2", "final_4a_constrained_both_burst_run3",
                       "final_4a_unconstrained_both_burst_run2_r2", "final_s2_tf_only_run3"}


def test_next_slot_reads_the_yaml(tree):
    _, configs = tree
    assert pfd.next_slot(configs, "2/s2_tf_only.yaml") == 4


def test_the_eleven_rows_are_the_evidence_reports_eleven():
    names = [h.name for h in pfd.AFFECTED]
    assert len(names) == 11 and len(set(names)) == 11
    assert names[:6] == [
        "final_s2_both_burst_run1", "study6_s2_normal_rgtf1_rep1", "study6_s2_normal_rgtf1_rep2",
        "study6_s2_normal_rgtf0_rep1", "study6_s2_normal_rgtf0_rep2", "final_s2_tf_only_run2",
    ]
    assert names[6:9] == [
        "final_4a_constrained_rg_only_burst_run2",
        "final_4a_constrained_rg_only_normal_run2_r2",
        "final_4a_constrained_tf_only_run2",
    ]
    assert names[9:] == ["final_s2_tf_only_run3", "final_s2_both_burst_run3"]


def test_render_has_all_sections_and_blank_decisions(tree):
    root, configs = tree
    audit = "`final_s2_tf_only_run2` and `final_4a_constrained_both_burst_run3` are in the audit."
    text = pfd.render(root, configs, audit)
    for heading in ("## A. Materially affected", "## B. Flagged, not recommended", "## C. Confounded",
                    "## D. Not in the 2026-10-15 audit"):
        assert heading in text
    row = next(l for l in text.splitlines() if l.startswith("| `final_s2_tf_only_run2`"))
    assert row.endswith("|  |")            # blank Decision cell
    assert "| 4 |" in row                   # next free slot from the YAML
    assert "| yes |" in row                 # in the locked final_ set
    c_row = next(l for l in text.splitlines() if l.startswith("| `final_4a_constrained_both_burst_run3`"))
    assert "| 5 |" in c_row and c_row.endswith("|  |")


def test_unconstrained_flagged_holds_are_not_recommended(tree):
    root, configs = tree
    text = pfd.render(root, configs, "")
    b = text.split("## B.")[1].split("## C.")[0]
    assert "final_4a_unconstrained_both_burst_run2_r2" in b
    assert "healthy" in b


def test_holds_missing_from_the_audit_are_listed(tree):
    root, configs = tree
    audit = "`final_s2_tf_only_run2` `final_4a_constrained_both_burst_run3` `final_4a_unconstrained_both_burst_run2_r2` `final_s1_tf_only_run1`"
    text = pfd.render(root, configs, audit)
    d = text.split("## D.")[1]
    assert "`final_s2_tf_only_run3`" in d
    assert "`final_s2_tf_only_run2`" not in d
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest experiments/test_proxy_fd_decisions.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'proxy_fd_decisions'`.

- [ ] **Step 3: Implement the generator**

Create `experiments/proxy_fd_decisions.py`. The `AFFECTED` rows copy the evidence report's "Materially affected" table and its per-hold table (onset, before → after, effect); `path` is relative to `final results/`.

```python
"""Generate Guides and Info/2026-10-16-proxy-fd-rerun-decisions.md.

    python experiments/proxy_fd_decisions.py [--root DIR] [--out PATH] [--check]

Source of the effect sizes: Guides and Info/2026-10-15-proxy-fd-evidence-flagged-holds.md.
Source of the next free slot: the `run_number` already written in the YAML that owns the cell
(STATUS.md "Next free slots" mirrors those numbers). Nothing is re-run; the Decision column
is left blank for the user.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_score  # noqa: E402
import throttle_flags  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CONFIGS = REPO / "experiments" / "configs" / "final_configs"
OUT_PATH = REPO / "Guides and Info" / "2026-10-16-proxy-fd-rerun-decisions.md"
EVIDENCE = "2026-10-15-proxy-fd-evidence-flagged-holds.md"
TOPFULL_ON_VARIANTS = ("both", "tf_only")


@dataclass(frozen=True)
class Hold:
    name: str
    path: str      # under final results/
    yaml: str      # under final_configs/
    onset: str
    goodput: str
    p95: str
    rejection: str
    effect: str


AFFECTED = [
    Hold("final_s2_both_burst_run1", "S2_sustained_overload_burst/both/final_s2_both_burst_run1",
         "2/s2_both_burst.yaml", "120 s", "350 → 374", "422 → 621", "0.16 → 0.31",
         "shortfall 65 req/s; the next minute drops 53 req/s and adds 232 ms of P95 beyond cleans"),
    Hold("study6_s2_normal_rgtf1_rep1", "S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep1",
         "2/s2_both_normal.yaml", "103 s", "346 → 400", "352 → 549", "0.13 → 0.26",
         "shortfall 51 req/s; the next minute drops 103 req/s and adds 307 ms of P95"),
    Hold("study6_s2_normal_rgtf1_rep2", "S2_sustained_overload_normal/both/study6_s2_normal_rgtf1_rep2",
         "2/s2_both_normal.yaml", "65 s", "314 → 385", "226 → 459", "0.05 → 0.30",
         "shortfall 94 req/s; minute rejection +0.25 against +0.09"),
    Hold("study6_s2_normal_rgtf0_rep1", "S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep1",
         "2/s2_rg_only_normal.yaml", "50 s", "242 → 321", "272 → 456", "0.03 → 0.41",
         "shortfall 142 req/s; rejection in the next minute +0.49 against +0.09. Edge rpr stays 0.007"),
    Hold("study6_s2_normal_rgtf0_rep2", "S2_sustained_overload_normal/rg_only/study6_s2_normal_rgtf0_rep2",
         "2/s2_rg_only_normal.yaml", "69 s", "305 → 367", "360 → 461", "0.06 → 0.34",
         "shortfall 96 req/s; minute rejection +0.38 against +0.08"),
    Hold("final_s2_tf_only_run2", "S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2",
         "2/s2_tf_only.yaml", "333 s", "402 → 317", "564 → 1318", "0.17 → 0.31",
         "shortfall 120 req/s; the next minute is −114 req/s and +697 ms against controls that are flat"),
    Hold("final_4a_constrained_rg_only_burst_run2",
         "S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2",
         "4/4a_constrained/4a_constrained_rg_only_burst.yaml", "37 s", "175 → 29", "610 → 316", "0.15 → 0.94",
         "shortfall 49 req/s on top of the constrained collapse; minute rejection +0.77 against +0.42"),
    Hold("final_4a_constrained_rg_only_normal_run2_r2",
         "S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2_r2",
         "4/4a_constrained/4a_constrained_rg_only_normal.yaml", "36 s", "156 → 22", "570 → 322", "0.20 → 0.95",
         "shortfall 39 req/s; minute rejection +0.66 against +0.43"),
    Hold("final_4a_constrained_tf_only_run2",
         "S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2",
         "4/4a_constrained/4a_constrained_tf_only.yaml", "47 s", "182 → 24", "592 → 597", "0.33 → 0.96",
         "shortfall 45 req/s; the next minute drops another 149 req/s versus cleans and edge rpr rises to 1.32"),
    Hold("final_s2_tf_only_run3", "S2_sustained_overload_normal/tf_only/final_s2_tf_only_run3",
         "2/s2_tf_only.yaml", "187 s", "176 → 88", "858 → 1330", "0.53 → 0.73",
         "direct proxy log (429 accept4 lines from 189 s); shortfall 140 req/s; pre-onset goodput already far below clean S2 (that hold was pinned)"),
    Hold("final_s2_both_burst_run3", "S2_sustained_overload_burst/both/final_s2_both_burst_run3",
         "2/s2_both_burst.yaml", "50 s", "238 → 310", "252 → 426", "0.07 → 0.44",
         "direct proxy log (568 accept4 lines from 50 s); shortfall 146 req/s (level still rises: 50 s is inside the ramp); minute rejection +0.37 against +0.09"),
]
AFFECTED_NAMES = {h.name for h in AFFECTED}

# Flagged, and the evidence report does not recommend a re-run. (name, reason)
NOT_RECOMMENDED = [
    ("final_s2_both_burst_run2", "mild: full-window goodput shortfall 30 req/s; goodput 243 → 450"),
    ("final_s2_rg_only_burst_run2", "brief: 16 timeouts and a 45 s gap at 567 s; goodput 400 → 412"),
    ("study7_s2_normal_rgtf1_rep1", "brief: 40 timeouts, 105 s gap at 511 s; real local dip, hold average 475 → 450"),
    ("final_s3_rg_only_normal_run1", "brief and unlike accept4: no fetch warning, 55 s gap, clock fit correlation 0.11"),
    ("s2_burst20_rgtf0", "healthy through 555 s stale: goodput 299 → 530, rejection 0.03 → 0.05"),
]


def yaml_for(variant: str, name: str) -> str | None:
    """YAML (under final_configs/) that owns a final_4a_constrained_* cell."""
    if "4a_constrained" not in name:
        return None
    mode = "burst" if "burst" in name else "normal"
    stem = {
        ("rg_only", "burst"): "4a_constrained_rg_only_burst",
        ("rg_only", "normal"): "4a_constrained_rg_only_normal",
        ("tf_only", "normal"): "4a_constrained_tf_only",
        ("tf_only", "burst"): "4a_constrained_tf_only",
        ("both", "burst"): "4a_constrained_both_burst",
        ("both", "normal"): "4a_constrained_both_normal",
    }[(variant, mode)]
    return f"4/4a_constrained/{stem}.yaml"


def legacy_flagged(root: Path) -> list[tuple[str, str, bool]]:
    """(name, variant, flagged) for every hold, by the collector rule at EVERY variant."""
    out = []
    for run_dir in sorted(p for p in Path(root).glob("*/*/*") if p.is_dir()):
        rows = analysis_score._rows(run_dir / "topfull_throttle.csv")
        q = analysis_score.throttle_quality(
            rows, run_dir / "topfull_throttle_collector.log", topfull_on=True)
        out.append((run_dir.name, run_dir.parent.name, bool(q["flagged"] and q["has_csv"])))
    return out


def next_slot(configs_root: Path, yaml_rel: str) -> int:
    data = yaml.safe_load((Path(configs_root) / yaml_rel).read_text(encoding="utf-8"))
    return int(data["run_number"])


def _variant_of(root: Path, name: str) -> str:
    return next(p.parent.name for p in Path(root).glob(f"*/*/{name}"))


def _yn(flag: bool) -> str:
    return "yes" if flag else "no"


def render(root: Path, configs_root: Path, audit_text: str) -> str:
    root, configs_root = Path(root), Path(configs_root)
    legacy = legacy_flagged(root)
    flagged = [(n, v) for n, v, f in legacy if f]
    on = [n for n, v in flagged if v in TOPFULL_ON_VARIANTS]
    scanned = {n for n, _v, _f in legacy}
    missing = [n for n in sorted(scanned) if not throttle_flags.name_pattern(n).search(audit_text)]
    missing_flagged = [n for n in missing if any(n == fn for fn, _ in flagged)]
    out = [
        "# Proxy descriptor re-run decisions",
        "",
        f"Generated by `python experiments/proxy_fd_decisions.py`. Effect sizes are copied from [{EVIDENCE}]({EVIDENCE}) "
        "(read its corrections box first). **Nothing here has been re-run.** A re-run happens only after the "
        "descriptor and RL-timeout fixes have passed the verification hold in "
        "[the 2026-10-16 plan](../docs/superpowers/plans/2026-10-16-proxy-fd-limit-and-rl-stall-flag.md) Task 7, and only "
        "for rows the user marks in the Decision column. The next free slot is the `run_number` already written in the "
        "YAML that owns the cell (STATUS.md \"Next free slots\" lists the same numbers); a re-run bumps `run_number` and "
        "`log_folder` in that YAML only.",
        "",
        f"Counts: `final results/` holds {len(legacy)} run folders; flagged by the collector rule at every variant: "
        f"{len(flagged)} ({len(on)} TopFull on, {len(flagged) - len(on)} off). `rg_only` holds are in scope here: "
        "every Locust request goes through the proxy, so a proxy that ran out of descriptors damages them too.",
        "",
        "## A. Materially affected (11)",
        "",
        "| Hold | Variant | TopFull | In the locked `final_` set | Onset | Goodput req/s | P95 ms | Rejection | Versus clean controls | YAML | Next free run_number | Decision |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for h in AFFECTED:
        variant = h.path.split("/")[1]
        out.append(
            f"| `{h.name}` | {variant} | {'on' if variant in TOPFULL_ON_VARIANTS else 'off'} | "
            f"{_yn(h.name.startswith('final_'))} | {h.onset} | {h.goodput} | {h.p95} | {h.rejection} | "
            f"{h.effect} | `{h.yaml}` | {next_slot(configs_root, h.yaml) if (configs_root / h.yaml).exists() else 'n/a'} |  |"
        )
    out += [
        "",
        "`study6_*` holds are not in the locked `final_` set; a re-run of their cell would be a `final_` hold in the S2 YAML, not a replacement of the study folder.",
        "",
        "## B. Flagged, not recommended for re-run",
        "",
        "| Hold | Why |",
        "| --- | --- |",
    ]
    present = {n for n, _ in flagged}
    for name, why in NOT_RECOMMENDED:
        if name in present:
            out.append(f"| `{name}` | {why} |")
    unconstrained = sorted(n for n, _v in flagged if "4a_unconstrained" in n)
    for name in unconstrained:
        out.append(f"| `{name}` | healthy through the stall: goodput stays near 720 req/s and rejection near 0 |")
    out += [
        "",
        "## C. Confounded S4A-constrained flagged holds",
        "",
        "Any stall damage sits on the clean S4A-constrained collapse floor (goodput about 40 req/s, rejection about 0.93), "
        "so it cannot be separated from the catalog bottleneck. Confounded does not mean unaffected. "
        "After the fixes a re-run would measure the collapse without a stall; whether that is worth a slot is the user's call.",
        "",
        "| Hold | Variant | TopFull | In the locked `final_` set | YAML | Next free run_number | Decision |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for name, variant in sorted(flagged):
        if name in AFFECTED_NAMES:
            continue
        rel = yaml_for(variant, name)
        if rel is None:
            continue
        slot = next_slot(configs_root, rel) if (configs_root / rel).exists() else "n/a"
        out.append(
            f"| `{name}` | {variant} | {'on' if variant in TOPFULL_ON_VARIANTS else 'off'} | "
            f"{_yn(name.startswith('final_'))} | `{rel}` | {slot} |  |"
        )
    out += [
        "",
        "## D. Not in the 2026-10-15 audit",
        "",
        f"The audit file lists 144 holds; `final results/` held {len(legacy)} when this was generated. "
        "Folders whose name does not appear in the audit:",
        "",
    ]
    out += [f"- `{n}`" + (" (flagged)" if n in missing_flagged else "") for n in missing] or ["- none"]
    out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--root", type=Path, default=throttle_flags.DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--check", action="store_true", help="print counts only, write nothing")
    args = parser.parse_args(argv)
    legacy = legacy_flagged(args.root)
    flagged = [r for r in legacy if r[2]]
    print(f"runs={len(legacy)} flagged_any_variant={len(flagged)}")
    if args.check:
        return 0
    audit = throttle_flags.AUDIT_PATH.read_text(encoding="utf-8")
    text = render(args.root, DEFAULT_CONFIGS, audit)
    if args.out.exists():
        print(f"[ERROR] {args.out} exists; delete it by hand first (this tool never overwrites).", file=sys.stderr)
        return 1
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest experiments/test_proxy_fd_decisions.py -v`
Expected: all pass. (`test_the_eleven_rows_are_the_evidence_reports_eleven` pins the order: 6 S2, 3 S4A, 2 re-runs.)

- [ ] **Step 5: Count the live tree**

Run: `python experiments/proxy_fd_decisions.py --check`
Expected: `runs=146 flagged_any_variant=52`. If the count differs, do not generate the document: print which holds changed with `python -c "import sys; sys.path.insert(0,'experiments'); import proxy_fd_decisions as p; print([r for r in p.legacy_flagged(p.throttle_flags.DEFAULT_ROOT) if r[2]])"` and compare against the audit; a new hold under `final results/` since 2026-10-16 is the usual reason.

- [ ] **Step 6: Generate and review the document**

Run: `python experiments/proxy_fd_decisions.py`
Expected: `runs=146 flagged_any_variant=52` then `wrote ...2026-10-16-proxy-fd-rerun-decisions.md`.

Review checklist (read the file):
- Section A has 11 rows, every `Decision` cell empty, every `Next free run_number` a number (S2 `s2_tf_only` and `s2_both_burst` rows say 4; `s2_both_normal` and `s2_rg_only_normal` say 3; `4a_constrained_rg_only_burst` says 7; the other S4A-constrained rows say 5).
- Section A's `In the locked final_ set` is `no` exactly for the four `study6_*` rows.
- Section C has 33 rows less the S4A-constrained rows that Section A already lists... count them: `rg -c "^\| \`final_4a_constrained" "Guides and Info/2026-10-16-proxy-fd-rerun-decisions.md"` — expected 36 (3 in Section A plus 33 in Section C). If it is not 36, stop and compare against the evidence report's By-scenario table.
- Section D names `final_s2_tf_only_run3` and `final_s2_both_burst_run3`, each marked `(flagged)`, and nothing else.

- [ ] **Step 7: Commit (only if the user asked)**

```powershell
git add experiments/proxy_fd_decisions.py experiments/test_proxy_fd_decisions.py "Guides and Info/2026-10-16-proxy-fd-rerun-decisions.md"
git commit -m "docs: decision list for the holds damaged by the proxy descriptor stall"
```

---

### Task 6: Start the VMs, confirm the cluster, then deploy the fixes on master

This task starts the three VMs. Do not wait for the user to start them. Nothing here runs a hold. After the health check it reads and changes only master's live TopFull copy. If a start, SSH, or cluster check fails, stop and report it. Do not patch master and do not start Task 7.

**Files:** none in the repo (VM state and `~/.ssh/config` `HostName` lines only). Record outcomes in Task 8.

- [ ] **Step 1: Start the three VMs and confirm they are usable**

Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md) "Reconnect after VMs were stopped". Do not start anything in `networks-workshop`.

```powershell
gcloud config set project project-76deda76-55f1-42d2-abb
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: `topfull-master`, `topfull-worker-1`, and `topfull-load` are `RUNNING`, each with a non-empty NAT IP. If one stays `TERMINATED` or has an empty IP, wait and list again. If it is still down after a few minutes, stop and report. Do not continue with a partial set.

Public IPs change on start, and worker and load have swapped addresses before. Read the three current `HostName` values from `~/.ssh/config`. For each old `HostName` and each new NAT IP:

```powershell
ssh-keygen -R <ip>
```

Rewrite only the three `Host topfull-master`, `Host topfull-worker-1`, and `Host topfull-load` `HostName` lines to the new NAT IPs. Leave `User idozacharia`, `IdentityFile`, and every other host block as they are.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "hostname; whoami"
```

Expected: each alias answers, and `whoami` is `idozacharia` on all three. A timeout means a stale `HostName` or a VM that is not up yet: re-list and fix the `HostName`, then retry. `Permission denied` means the key is missing for `idozacharia`: re-run CONNECT-VMS.md Step 4 (key install) and retry. Do not switch `User` to `idoza`.

Then confirm the cluster, not just SSH. The API server can still be down right after a start, and a missing kubeconfig looks the same (`connection to localhost:8080 refused`).

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

Expected: both nodes `Ready`, the Online Boutique pods `Running` (2/2), and the VirtualServices listed. If `kubectl` says `connection to localhost:8080 refused`, check `~/.kube/config` for `idozacharia` (AGENTS.md §7) and wait a few minutes for the static pods, then run the same command again. If nodes are not `Ready` or pods are not `Running` after that wait, stop and report. The cluster is good to go only when this command succeeds.

- [ ] **Step 2: Read the facts this plan assumed**

Run: `ssh topfull-master "go version; ulimit -Sn; ulimit -Hn; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py"`
Expected: a Go version (if it is older than 1.19, that confirms the explanation in "Corrections" item 3; if 1.19 or newer, note it in Task 8 and keep going: the `ulimit` fix is still correct), `1024`, `1048576`, and both files listed.

Run: `ssh topfull-master "grep -c 'current_rps' /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py"`
Expected: `deploy_rl.py:2` and `overload_detection.py:` four or more. A different count means the live files differ from upstream; `patch_rl_timeout.py` will refuse with `anchor not found`, which is the intended safe failure.

- [ ] **Step 3: Dry-run the patch on master**

Run:
```powershell
scp experiments/patch_rl_timeout.py topfull-master:/tmp/rg_deploy_patch_rl_timeout.py
ssh topfull-master "python3 /tmp/rg_deploy_patch_rl_timeout.py --dry-run"
```
Expected: `overload_detection.py: would patch` and `deploy_rl.py: would patch`. If `[ERROR] ... anchor not found exactly once`, stop: the live file differs from upstream. Do not hand-edit without the user; report which anchor failed.

- [ ] **Step 4: Apply the patch**

Run: `ssh topfull-master "python3 /tmp/rg_deploy_patch_rl_timeout.py"`
Expected: `overload_detection.py: patched (backup overload_detection.py.orig-<stamp>)` and the same for `deploy_rl.py`.

Run: `ssh topfull-master "python3 -m py_compile /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py && echo compiled; grep -c 'RL_TIMEOUT_PATCH v1' /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py"`
Expected: `compiled`, then `...overload_detection.py:1` and `...deploy_rl.py:1`. Re-run Step 4's patch command: expected `already patched` twice.

- [ ] **Step 5: Check the cluster shape before the hold (AGENTS.md §4 caveat)**

The 2026-10-15 holds ran pinned (frontend HPA 4/4, catalog 1/1, sidecar `proxyCPU=90m`) and the restore to the unpinned shape was never recorded. The locked S2 set runs **unpinned**.

Run: `ssh topfull-master "kubectl get nodes; kubectl get hpa -n default; kubectl get deploy frontend -n default -o jsonpath='{.spec.template.metadata.annotations}'"`
Expected for the unpinned shape: nodes `Ready`; frontend HPA min 1 max 4; productcatalogservice HPA min 1 max 2; frontend annotations `sidecar.istio.io/proxyCPU: 100m` and **no** `proxyCPULimit`. If the live shape is the pinned one (HPA 4/4 and 1/1, `proxyCPU` `90m`), restore it: patch the HPAs (`kubectl patch hpa <name> -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":4}}'` for frontend and `...1,"maxReplicas":2` for the catalog; take the exact HPA names from the `kubectl get hpa` output, they were not read when this plan was written) and the frontend Deployment's `spec.template.metadata.annotations` (patch the pod template, not the Deployment object) to `proxyCPU=100m`. Re-run the `kubectl get` and confirm. Record what was found and what was changed for Task 8.

---

### Task 7: One verification hold — **NEEDS VMs UP**

Purpose: show on a real hold that the descriptor limit holds, the proxy never refuses connections, the RL loop never goes silent, and the throttle collector stays fresh. This is a real S2 `tf_only` hold, the load that stalled twice. It writes a new folder and overwrites nothing.

**Files:**
- Modify: `experiments/configs/final_configs/2/s2_tf_only.yaml` (`run_number`, `log_folder` only — only if STATUS.md "Next free slots" still says 4; otherwise use the number it says)
- Result folder (pulled): `experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run4/`

- [ ] **Step 1: Preconditions**

All of these must be true; if one is not, stop and report:
- Tasks 1–5 pass their tests: `python -m pytest experiments/test_run_scenario.py experiments/test_run_scenario_proxy_guard.py experiments/test_proxy_fd_collector.py experiments/test_patch_rl_timeout.py experiments/test_topfull_health.py experiments/test_analysis_score.py -q` all pass.
- Task 6 passed: the patch is present on master and the cluster is in the unpinned shape.
- Read [STATUS.md](../../../STATUS.md) "Next free slots". The `s2_tf_only.yaml` line says 4 when this plan was written. Use the number it says, not a number from this plan. The cell `final_s2_tf_only_run3` exists on disk and must not be overwritten.

- [ ] **Step 2: Clear leftover writers (AGENTS.md §6, as updated in Task 2)**

Wait until 120 s have passed since the last hold exited (the last hold was 2026-10-15; this is satisfied unless another hold ran today). Then run the §6 sequence exactly:

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_proxy_fd.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/proxy_fd_params.json"
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; pkill -f '[p]roxy_fd_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
ssh topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py|[p]roxy_fd_collector.py' || echo master-clear"
ssh topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log"
ssh topfull-master "sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```
Expected: `locust-clear`, `master-clear`, and an empty directory listing. Any other output: a writer is alive; do not start the run.

- [ ] **Step 3: Bump the slot and run**

In `experiments/configs/final_configs/2/s2_tf_only.yaml` set `run_number` to the free number (4) and `log_folder` to `final_s2_tf_only_run4` (keep the file's existing prefix and suffix style; open the file and match the pattern of the current `log_folder` value, changing only the run number). Never touch the historical `scenario_*.yaml` for this hold.

Run: `python experiments/run_scenario.py experiments/configs/final_configs/2/s2_tf_only.yaml`
Expected during startup: `Proxy open-files soft limit <N> [OK]` with N at or above 4096 (the hard limit, 1048576), then `RL timeout patch present on master [OK]`, `Started: proxy descriptor collector`, then `Master processes running [OK]`, and the 10-minute run. An abort with `proxy soft open-files limit is 1024` or `lack 'RL_TIMEOUT_PATCH v1'` means Task 1 or Task 6 did not take effect: fix that, do not bypass the check.

- [ ] **Step 4: Pull the folder**

Run: `python experiments/pull_results.py experiments/configs/final_configs/2/s2_tf_only.yaml`
Expected: the folder appears at `experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run4/` and contains `proxy_fds.csv`, `proxy_fd_collector.log`, `topfull_proxy.log`, `topfull_rl.log`, `topfull_throttle.csv`.

- [ ] **Step 5: Check each expected result**

```powershell
$d = "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run4"
(Select-String -Path "$d/topfull_proxy.log" -Pattern "too many open files" -SimpleMatch).Count
Select-String -Path "$d/topfull_proxy.log" -Pattern "nofile soft=" | Select-Object -First 1
python -c "import pandas as pd; d=pd.read_csv(r'$d/proxy_fds.csv'); print('rows',len(d),'peak_fds',d.open_fds.max(),'min_soft',d.soft_limit.min())"
(Select-String -Path "$d/topfull_rl.log" -Pattern "RL_RPS_TIMEOUT" -SimpleMatch).Count
(Select-String -Path "$d/topfull_rl.log" -Pattern "RL_LOOP_START" -SimpleMatch).Count
python experiments/topfull_health.py "$d"
python experiments/analysis_score.py "$d"
```
Expected, all of them:
- `too many open files` count: `0`.
- first proxy log line carries `nofile soft=1048576 hard=1048576` (or the hard limit the master reported in Task 6 Step 2).
- `proxy_fds.csv`: at least 500 rows, `min_soft` above 1024, `peak_fds` well below `min_soft`. (Peak above 1024 is the new normal; it is what would have crashed the old proxy. Note the peak in Task 8.)
- `RL_RPS_TIMEOUT` count `0`.
- `RL_LOOP_START` count of roughly 250–300 (one per 2 s over a 10-minute hold).
- `topfull_health.py` prints `health: ok` and an `rl:` line with `rl_silent_over_30s=no` and a `longest_silence_s` of a few seconds.
- the scorer's `Throttle data quality` row is `ok` (no `FLAGGED`) and its `Proxy and RL health` row is `ok`.

**If any expectation fails**, do not re-run anything from the decision list. Record the failure (which check, the numbers) for Task 8 and tell the user. A `PROXY FD` with a high soft limit would mean a leak or a different limit, which needs a new diagnosis, not a retry.

- [ ] **Step 6: Cool-off and restore**

Wait 120 s before any further hold. If Task 6 Step 5 changed the cluster shape, nothing further is needed; if the hold was run pinned for any reason, restore the unpinned shape and record it.

- [ ] **Step 7: Commit the YAML bump (only if the user asked)**

The hold's results folder is tracked like the other `final results/` folders; ask the user whether to commit it.

```powershell
git add experiments/configs/final_configs/2/s2_tf_only.yaml "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run4"
git commit -m "run: S2 tf_only verification hold after the proxy descriptor and RL timeout fixes"
```

---

### Task 8: Close-out, STATUS/AGENTS update, and open questions for the user

**Files:**
- Modify: `AGENTS.md` (§4 Latest three lines, "Still open", §7 known-fixes sentence)
- Modify: `STATUS.md` (one Done bullet; Next free slots if a YAML moved)
- Test: the full affected test set

**Interfaces:**
- Consumes: results of Tasks 1–7.
- Produces: the repo state recorded, and the open questions stated.

- [ ] **Step 1: Full test run and untouched-data check**

Run: `python -m pytest experiments/test_run_scenario.py experiments/test_run_scenario_proxy_guard.py experiments/test_proxy_fd_collector.py experiments/test_patch_rl_timeout.py experiments/test_topfull_health.py experiments/test_analysis_score.py experiments/test_throttle_flags.py experiments/test_throttle_stale.py experiments/test_retire_stay_valid.py experiments/test_proxy_fd_decisions.py -q`
Expected: all pass.

Run: `python experiments/throttle_flags.py audit`
Expected first line unchanged: `runs=146 flagged=27 topfull_on_flagged=27 topfull_off_flagged=0` (or `runs=147 ...` if Task 7 ran and its folder is clean and TopFull-on; then `flagged=27`).

Run: `git status --short "experiments/results"`
Expected: no output, or only the Task 7 folder. No other run folder is modified.

- [ ] **Step 2: Plan the STATUS.md step (write it by hand, once)**

Append **one** bullet under Done (above `## Next free slots`) in STATUS.md style: date `2026-10-16`; what was done (descriptor limit raised and verified in the runner; `proxy_fds.csv` collector; RL timeout patch applied to master and recorded as a deviation; `RL STALL` / `PROXY FD` flags; `PROXY STALL SUSPECTED` for holds with no proxy log (live count 52: 25 TopFull-off, 27 TopFull-on; `throttle_flags.py suspected`), which supersedes the "TopFull-off is N/A" reading of the remediation plan's Decided item 1 for labels only; "stay valid" sentences retired; decision document generated); the result of the Task 7 verification hold (peak descriptors, `too many open files` count, RL log longest silence, throttle `ok`) **only if it ran and passed**, otherwise the line `Verification hold not run (VMs down)` or the failing check; what is left (re-runs not decided, mentor sign-off open); links to this plan, [TOPFULL-UPSTREAM-DEVIATIONS.md](../../../Guides%20and%20Info/TOPFULL-UPSTREAM-DEVIATIONS.md), and [2026-10-16-proxy-fd-rerun-decisions.md](../../../Guides%20and%20Info/2026-10-16-proxy-fd-rerun-decisions.md). State failures and unverified items as such. If Task 7 ran, say whether `final_s2_tf_only_run4` is treated as a locked-set hold or as verification only (the user's call; default to verification only until told otherwise) and update "Next free slots" for `s2_tf_only.yaml` to the next number. Do not append anything about the edits to STATUS.md and AGENTS.md themselves.

- [ ] **Step 3: Plan the AGENTS.md step (replace, do not append)**

§4 "Latest": replace the three lines (do not append) with: (1) the fixes and the flags, one sentence each with links to this plan and the decision document; (2) the next free slot for `s2_tf_only` and `s2_both_burst` (4 unless Task 7 used it) and that no hold on the decision list has been re-run; (3) the cluster shape found and restored in Task 6 Step 5, or `Cluster not confirmed restored` if Task 6 could not start the VMs or the health check failed. "Still open": add mentor sign-off on the TopFull patch, and the re-run decision on the 11 holds; remove nothing that is still open. §7 "Known fixes already applied on master": add one sentence that master's `overload_detection.py` and `deploy_rl.py` carry the `RL_TIMEOUT_PATCH v1` patch (originals kept as `*.orig-<timestamp>`), the runner aborts a TopFull-on hold without it, and the proxy now starts with its soft open-files limit raised to the hard limit. Fix §3 and §2 if any row from Tasks 2–3 is still missing. Keep each entry short, dated, and factual.

- [ ] **Step 4: Final diff review**

Run: `git diff --stat`
Expected: the files named in File Structure and nothing else.

- [ ] **Step 5: Open questions for the user (state these in the final message, do not decide them)**

1. **Mentor sign-off on a TopFull code change.** The RL timeout patch changes only the failure path of `current_rps()` (wait 2 s and retry on the next tick instead of waiting without limit). It is disclosed in [TOPFULL-UPSTREAM-DEVIATIONS.md](../../../Guides%20and%20Info/TOPFULL-UPSTREAM-DEVIATIONS.md). Do the mentors accept it for the paper? If not, holds run without it, and the `RL STALL` flag is the only protection.
2. **Separate listener for the proxy's admin endpoints** (`/stats`, `/thresholds`) so a full accept queue on `:8090` cannot starve them. **Out of scope for this plan and recorded here.** It would be a change to `proxy_online_boutique.go`, which is a bigger deviation than the timeout and needs its own plan.
3. **Cluster restore state.** AGENTS.md §4 says the 2026-10-15 holds ran pinned (frontend HPA 4/4, catalog 1/1, `proxyCPU=90m`) and the restore to HPA 1–4 / 1–2 / `100m` was never recorded. Task 6 Step 5 reads and restores it. Confirm the live shape before any further hold.
4. **Re-run decisions.** Which rows of [2026-10-16-proxy-fd-rerun-decisions.md](../../../Guides%20and%20Info/2026-10-16-proxy-fd-rerun-decisions.md) get a re-run, and whether a passing `final_s2_tf_only_run4` verification hold counts as a locked-set hold.
5. **Whether `study6_*` holds (not `final_`) get re-run at all**, or the locked S2 cells (`both_normal`, `rg_only_normal`) get fresh `final_` holds instead.

- [ ] **Step 6: Commit (only if the user asked)**

```powershell
git add AGENTS.md STATUS.md
git commit -m "docs: record the proxy descriptor fix and the RL stall flag"
```

---

## Self-Review (run against the request)

1. **Spec coverage.**
   - Brief item 1 (raise descriptor limit, guard when the hard limit is low, test the generated script, `/proc/<pid>/limits` check on the proxy binary child of `go run`, abort before Locust, injectable-ssh tests, inheritance mechanism): Task 1 and "Corrections" item 3. The low-hard-limit guard is the `WARN hard nofile limit` line plus the 4096 abort in the verifier; unlimited is capped at 1048576.
   - Item 2 (sampling collector, `proxy_fds.csv` with UTC timestamp, pid, fd count, soft limit, ≤5 s; runner start/stop/pull; AGENTS §6 pgrep and kill list; METRICS-GATHERED table; tests): Task 2 (1 s interval; pull is covered because `collect_results` copies `src/logs/.` and `pull_results.py` runs `scp -r`).
   - Item 3 (timeout in `current_rps()` and any other proxy HTTP call, catch and log, heartbeat and start/end/timeout/cap-apply lines in a stable format, how TopFull is deployed, patch script and VM-required steps, deviation record, open decision, "robustness not behavior" statement): Task 3 (the only other `requests.get` is dead code, stated in Background), Task 6 for VM steps, `TOPFULL-UPSTREAM-DEVIATIONS.md`, Task 8 question 1.
   - Item 4 (separate `RL STALL` flag with a justified N, independent of the throttle flag, `proxy_fds.csv` / `too many open files` triggers, old holds `not assessable`, AGENTS §6 text, METRICS-GATHERED, ANALYSIS-TEMPLATE item 17, correct "remain valid", STATUS Done/Latest planned): Task 4 and Task 8 Steps 2–3. `PROXY FD` is a second name for the descriptor triggers because they apply to `rg_only`, which an RL-only flag cannot cover; stated in "Corrections" item 2.
   - Item 5 (decision list for 11 holds, per-hold effect, variant, locked `final_` membership, next slot, blank Decision, confounded section, healthy-through-stall section, the 2 holds missing from the audit with 146 vs 144 and 52, no re-runs, a verification-hold task with the stated expectations): Tasks 5 and 7.
   - Item 6 (open questions, mentor sign-off, admin-endpoint listener out of scope but recorded, cluster-restore check before the verification hold): Task 8 Step 5, Task 6 Step 5.
   - Global Constraints section: present and contains all seven requested items.
2. **Placeholder scan.** No "TBD" or "similar to Task N". Three places tell the executor to read a live value instead of using a number from this plan, with a reason: the next `run_number` (STATUS.md changes), the HPA names (not read when written), and Go's version (not read). The code blocks are complete as written; a pass over them after drafting removed leftover scaffolding.
3. **Type and name consistency.** `proxy_nofile_bash`, `PROXY_NOFILE_MIN`, `NOFILE_UNLIMITED`, `read_proxy_soft_limit`, `verify_proxy_nofile`, `PROXY_LIMITS_SCRIPT` (Task 1) are used with those names in Tasks 2, 3 and 7. `proxy_fd_collector.py`, `proxy_fds.csv`, `CSV_COLUMNS = timestamp,pid,open_fds,soft_limit`, tmux session `proxyfd`, `/tmp/rg_proxy_fd.sh`, `/tmp/proxy_fd_params.json` agree across Task 2, AGENTS.md edits, the Task 7 cleanup commands, and `topfull_health.FD_FILE`. The `RL_*` line formats in Task 3 match what `topfull_health.assess` parses (`RL_RPS_TIMEOUT`, `RL_RPS_END ... elapsed_s=`) in Task 4. `RL_PATCH_MARKER` equals `patch_rl_timeout.MARKER` and a test pins it. `Health.status` strings match what `analysis_score.render` and the AGENTS/ANALYSIS-TEMPLATE text say.
4. **Assumptions I could not verify from the repo** (also stated in the final reply): master's Go version (the explanation that `go run` hands the child the shell's limit is correct either way; Go 1.19+ would only change why 1024 survived); that the compiled binary's path contains `/exe/proxy_online_boutique` (Go's `go run` naming; `overload_detection.py` itself greps `/exe/proxy` and `go-build`, which agrees, but the exact name was not observed); that the live `overload_detection.py` / `deploy_rl.py` on master still contain the upstream anchor text (the patch refuses safely if not); that `final_s2_tf_only_run3` shows both flags with the digits in the evidence report; HPA names on the cluster; that the remediation plan finishes with `throttle_flags.py` and `analysis_score.py` as it describes (checked on disk at 00:45, Task 9 not yet applied); and that the count of 36 `final_4a_constrained_*` rows in the decision document (3 in Section A plus 33 confounded) holds on the live tree.
