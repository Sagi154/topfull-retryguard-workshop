# S3 TopFull-Only Cap Floor Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one Scenario 3 TopFull-only hold and show two things: the hold finishes with no new failure from the cap-floor patch, and a written `postcheckout` cap can sit strictly below 10 req/s. A written 0 counts, and a value in (0, 10) also counts. The controller is not required to choose 0.

**Architecture:** The floor is already implemented on the working tree (`experiments/topfull_cap_floor.py`, `ensure_cap_floor` in `experiments/run_scenario.py`). This plan does not change that code. It dry-runs the three rewrites against the live files on `topfull-master`, launches the existing S3 `tf_only` YAML, and reads `topfull_throttle.csv` plus the proxy and RL logs. `analysis_score.py` still drops a fresh threshold of 0, so a 0 that does appear is read from the CSV and the proxy log. Missing 0 is not a failure.

**Tech Stack:** The existing runner (`experiments/run_scenario.py`), OpenSSH host aliases, Python 3, pytest. No new dependency. No edit under `TopFull/`.

## Global Constraints

- The hold is `experiments/configs/final_configs/3/s3_tf_only.yaml`. When this plan was written that file had `run_number: 5` and `log_folder: final_s3_tf_only_run5`, and [STATUS.md](../../../STATUS.md) "Next free slots" listed every `final_configs/3/` YAML at 5. Use the number STATUS says at execution time. Do not edit any other YAML.
- Pulled folder: `experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/<log_folder>/`. RetryGuard is off, so the mode directory is `normal` even though the YAML still contains the three burst keys.
- This folder is verification only. It is not a column in [2026-10-15-s3-mode-matrix-abc.md](../../../Guides%20and%20Info/2026-10-15-s3-mode-matrix-abc.md). The locked S3 pair stays `final_s3_*_run3` and `final_s3_*_run4`.
- Do not change `experiments/topfull_cap_floor.py`, `experiments/run_scenario.py`, `experiments/analysis_score.py`, `experiments/graphs_tool.py`, `experiments/multi_graphs_tool.py`, or `experiments/run_timeline.py`. A fresh threshold of 0 stays an empty read in the scorer and on the graphs.
- Do not edit anything under `TopFull/`. The runner rewrites the live files on master.
- SSH aliases only: `topfull-master`, `topfull-worker-1`, `topfull-load`. Do not start the VMs in `networks-workshop`. Do not stop the three copy VMs unless the user asks.
- Cool-off before the hold is 120 s from the last `run_scenario.py` exit. `final_s2_tf_only_run4` finished before this plan was written, so that gap has elapsed unless a hold exits in this session.
- The floor check passes when both the CSV and the proxy log show a `postcheckout` cap strictly below 10. `0` is one such value. A hold that never writes 0 still passes the floor check when some written cap is in (0, 10). A CSV `0.0` with `threshold_fresh` 1 and no matching proxy apply is not, by itself, that cap: the collector also writes 0 for a missing key.
- The regression check passes when the hold exits, the three live files contain `TOPFULL_CAP_FLOOR`, both Python files still contain `RL_TIMEOUT_PATCH v1`, the RL log has no `zero threshold` line, a fresh 0 is not followed within 5 s by all five APIs at 10000, `too many open files` is 0, `health:` is `ok`, and throttle data quality is `ok`. Both checks are required.
- If `ensure_cap_floor` aborts (`expected 1 site, found`), do not hand-edit the live files and do not start Locust.
- Commit only when the user has asked for a commit in this session.

---

## File structure

- `experiments/configs/final_configs/3/s3_tf_only.yaml` — after a pulled hold, `run_number` and `log_folder` only.
- `experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run5/` — created by the runner and `pull_results.py`. Not written by hand.
- `STATUS.md` — one Done bullet, and the S3 next-free line split so only `s3_tf_only.yaml` moves.
- `AGENTS.md` — replace the three Latest lines in §4.

No new module. The dry-run and the verdict are inline Python in Tasks 2 and 4.

## Task 1: Confirm the tree, the slot, and the cluster

**Files:**
- Read: `experiments/run_scenario.py` (the `ensure_cap_floor` function)
- Read: `experiments/configs/final_configs/3/s3_tf_only.yaml`
- Read: `STATUS.md` "Next free slots"
- Test: `experiments/test_topfull_cap_floor.py`, `experiments/test_run_scenario.py`

**Interfaces:**
- Consumes: the cap-floor patcher already on this working tree.
- Produces: a go / no-go. Later tasks run only when every check in this task passed. The slot number they use is the `run_number` this task read from STATUS, called `SLOT` below. When this plan was written, `SLOT` was 5 and `log_folder` was `final_s3_tf_only_run5`.

- [ ] **Step 1: Confirm the runner that will launch the hold contains the floor**

```powershell
python -c "import pathlib; t=pathlib.Path('experiments/run_scenario.py').read_text(encoding='utf-8'); assert 'def ensure_cap_floor' in t; print('ensure_cap_floor present')"
```

Expected: `ensure_cap_floor present`

If this raises `AssertionError`, stop. Do not check out another branch and do not merge. The hold would install nothing and would still floor every API at 10.

- [ ] **Step 2: Run the floor tests**

Run: `python -m pytest experiments/test_topfull_cap_floor.py experiments/test_run_scenario.py -q`

Expected: both files pass (the last line is an all-passed count). A failure here means the tree that would patch master is not the tree the tests describe. Stop. Do not start the hold.

- [ ] **Step 3: Read the free slot**

Open `experiments/configs/final_configs/3/s3_tf_only.yaml` and the "Next free slots" list in `STATUS.md`.

Expected when this plan was written: the YAML has `run_number: 5` and `log_folder: final_s3_tf_only_run5`, and the `final_configs/3/` line says 5. `topfull_rl.enabled` is `true`. `retryguard.enabled` is `false`. `duration_seconds` is `600`. `checkoutservice` `cpu_limit_millicores` is `200`. User counts are `175 / 30 / 70 / 90 / 5`.

Use the number STATUS prints, not a remembered 5, if STATUS has moved. Do not bump the YAML in this step. The file is already sitting on the free slot. Do not edit the other four S3 YAMLs. Do not edit `experiments/configs/scenario_3_baseline.yaml`.

Confirm the destination folder does not already exist:

```powershell
Test-Path "experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run5"
```

Expected: `False`. If STATUS named a different slot, test that slot's `log_folder` instead. `True` means the slot was used: stop and report it.

- [ ] **Step 4: Confirm SSH and the unpinned cluster**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default; kubectl get hpa -n default; kubectl get deploy frontend -n default -o jsonpath='{.spec.template.metadata.annotations}'; echo"
```

Expected: the command returns. Nodes `Ready`. Frontend HPA min 1 max 4. `productcatalogservice` HPA min 1 max 2. Frontend annotations include `sidecar.istio.io/proxyCPU: 100m` and do not include `proxyCPULimit`. Pods for Online Boutique are up. A timeout means the VM is stopped or the HostName is stale: follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md). Start only `topfull-master`, `topfull-worker-1`, and `topfull-load` in `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. Do not start the `networks-workshop` VMs.

If the live shape is pinned (frontend HPA min 4 max 4, catalog min 1 max 1, `proxyCPU` `90m`), restore the unpinned shape before the hold. Take the HPA names from the `kubectl get hpa` output (they were `frontend-hpa` and `productcatalogservice-hpa` on 2026-10-16):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl patch hpa frontend-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":1,\"maxReplicas\":4}}'; kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":1,\"maxReplicas\":2}}'"
```

Patch `sidecar.istio.io/proxyCPU` to `100m` on the frontend Deployment's pod template (`spec.template.metadata.annotations`), and remove `sidecar.istio.io/proxyCPULimit` if it is set. A Deployment-object annotate does not roll the pods. Re-run the `kubectl get` in this step and confirm the unpinned shape before Task 2.

## Task 2: Dry-run the cap-floor patch against the live sources

**Files:**
- Read-only on master: `/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py`
- Read-only on master: `/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py`
- Read-only on master: `/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go`
- Uses: `experiments/topfull_cap_floor.py` (`patch_overload_detection`, `patch_deploy_rl`, `patch_proxy_burst`)

**Interfaces:**
- Consumes: Task 1 go.
- Produces: `preflight_ok` printed locally. Master is unchanged. Task 3 may start the hold only after that line.

- [ ] **Step 1: Rewrite the three live texts in memory**

This does not upload anything. `patch_*` returns the original string when `TOPFULL_CAP_FLOOR` is already present, and raises `RuntimeError` when the old site is missing or duplicated.

```powershell
python -c @"
import subprocess, sys
sys.path.insert(0, 'experiments')
import topfull_cap_floor as floor

SRC = '/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src'
FILES = [
    ('overload_detection.py', floor.patch_overload_detection, True),
    ('deploy_rl.py', floor.patch_deploy_rl, True),
    ('proxy/proxy_online_boutique.go', floor.patch_proxy_burst, False),
]
for rel, patcher, needs_rl in FILES:
    remote = SRC + '/' + rel
    proc = subprocess.run(
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'topfull-master', 'cat ' + remote],
        capture_output=True, text=True, encoding='utf-8',
    )
    if proc.returncode != 0:
        raise SystemExit('ssh failed for ' + rel + ': ' + proc.stderr)
    original = proc.stdout.replace('\r\n', '\n').replace('\r', '\n')
    patched = patcher(original)
    state = 'already' if patched == original else 'will_patch'
    rl = 'RL_TIMEOUT_PATCH v1' in patched
    if needs_rl and not rl:
        raise SystemExit(rel + ': RL_TIMEOUT_PATCH v1 missing after the cap-floor rewrite')
    if \"if api['threshold'] <= 10:\" in patched:
        raise SystemExit(rel + ': old floor of 10 still present after the rewrite')
    if 'print(\"zero threshold\")' in patched:
        raise SystemExit(rel + ': zero-threshold reset still present after the rewrite')
    print(rel, state, 'rl_marker=' + str(rl))
print('preflight_ok')
"@
```

Expected, three file lines then `preflight_ok`. Each file line is `already` or `will_patch`. The two Python files print `rl_marker=True`. The Go file prints `rl_marker=False`.

`RuntimeError: ... expected 1 site, found` means the live file no longer matches the patcher (the RL timeout patch and the cap-floor patch disagree, or the file was edited by hand). Stop. Do not start Task 3. Do not edit the live file to make the site match.

- [ ] **Step 2: Confirm master was not written**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "grep -c TOPFULL_CAP_FLOOR /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go || true"
```

Expected: the same marker counts as before Step 1. Step 1 does not upload, so a file that printed `will_patch` still has count `0`, and a file that printed `already` still has a count greater than `0`. A count that changed means something else wrote the file. Stop.

## Task 3: Run the S3 TopFull-only hold

**Files:**
- Modify on master, via the runner only: the three paths in Task 2
- Create: `experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run5/` (or the `log_folder` Task 1 read)

**Interfaces:**
- Consumes: `preflight_ok` from Task 2, and `SLOT` / `log_folder` from Task 1.
- Produces: a pulled run directory containing `topfull_throttle.csv`, `topfull_proxy.log`, and `topfull_rl.log`.

- [ ] **Step 1: Clear leftover writers**

If `run_scenario.py` exited in this session less than 120 s ago, wait out the remainder. Then:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_proxy_fd.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/proxy_fd_params.json"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; pkill -f '[p]roxy_fd_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py|[p]roxy_fd_collector.py' || echo master-clear"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

Expected: `locust-clear`, `master-clear`, and an empty directory listing. Any other process line means a writer is alive. Do not start the run.

- [ ] **Step 2: Launch the hold**

Do not change `run_number` or `log_folder` first. They already name the free slot from Task 1.

Run: `python experiments/run_scenario.py experiments/configs/final_configs/3/s3_tf_only.yaml`

Expected during startup, for each of the three live paths, one of these lines (the timestamp prefix varies):

```text
cap floor already in /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py
```

```text
Patched /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py for cap floor 0
```

The same two shapes for `deploy_rl.py` and `proxy/proxy_online_boutique.go`. Then `Proxy open-files soft limit <N> [OK]` with N at or above 4096, `RL timeout patch present on master [OK]`, and the 600 s hold.

An abort whose message contains `expected 1 site, found` or `lack 'RL_TIMEOUT_PATCH v1'` means the live tree is not the tree Task 2 accepted. Stop. Do not bypass the check. Do not bump the YAML: the slot was not consumed if no results folder was pulled.

The run is 10 minutes plus startup. Wait until `run_scenario.py` exits.

- [ ] **Step 3: Pull the folder**

Run: `python experiments/pull_results.py experiments/configs/final_configs/3/s3_tf_only.yaml`

Expected directory: `experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run5/` (substitute the `log_folder` from Task 1 if STATUS had moved). It contains `topfull_throttle.csv`, `topfull_proxy.log`, `topfull_rl.log`, `proxy_fds.csv`, and `run_manifest.json`.

- [ ] **Step 4: Confirm the three live files now carry the floor and still carry the RL marker**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "echo OD; grep -c TOPFULL_CAP_FLOOR /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py; grep -c RL_TIMEOUT_PATCH /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py; echo RL; grep -c TOPFULL_CAP_FLOOR /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py; grep -c RL_TIMEOUT_PATCH /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/deploy_rl.py; echo GO; grep -c TOPFULL_CAP_FLOOR /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/proxy_online_boutique.go; echo OLD; grep -c \"threshold'] <= 10\" /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py || true"
```

Expected: each `TOPFULL_CAP_FLOOR` count is greater than 0, each `RL_TIMEOUT_PATCH` count is greater than 0, and the old-floor count is `0`. A `0` on `TOPFULL_CAP_FLOOR` means the hold did not install the floor. Do not call it verified. Continue to Task 4 so the logs are still scored, and record the install as failed.

## Task 4: Read the cap-floor verdict

**Files:**
- Read: the pulled folder from Task 3
- Test: the inline script in Step 1, then `experiments/topfull_health.py` and `experiments/analysis_score.py` as read-only scorers

**Interfaces:**
- Consumes: the pulled folder. The prior S3 TopFull-only holds `final_s3_tf_only_run3` and `final_s3_tf_only_run4` kept `postcheckout` at exactly 10 for most of the loaded window ([2026-10-15-s3-mode-matrix-abc.md](../../../Guides%20and%20Info/2026-10-15-s3-mode-matrix-abc.md) live-caps sections). A written rate strictly below 10 is the new observation. Whether that rate is 0 is recorded and is not required.
- Produces: one printed `verdict=` line, one printed `saw_zero=` line, plus the health lines. Task 5 copies those lines into STATUS.

`live_caps` in `experiments/analysis_score.py` skips `threshold <= 0`. A scorer table that omits postcheckout's 0 is the expected display. It is not a failed hold.

- [ ] **Step 1: Run the verdict script**

Set `RUN` to the pulled folder. The script treats 10000 as no cap. A floor pass is any fresh `postcheckout` cap strictly below 10 on both the CSV and the proxy log. `saw_zero` records whether that cap was 0. `zero threshold` in the RL log is the old `stop(reset=True)` print. A later tick within 5 s where all five APIs are fresh at 10000 is that reset.

```powershell
python -c @"
import csv, re
from datetime import datetime
from pathlib import Path

RUN = Path(r'experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run5')
APIS = ('getproduct', 'postcheckout', 'getcart', 'postcart', 'emptycart')
PASSTHROUGH = 10000.0

def parse_ts(text):
    return datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ')

rows = list(csv.DictReader((RUN / 'topfull_throttle.csv').open(encoding='utf-8')))
fresh_by_tick = {}
stats = {api: {'fresh': 0, 'capped': 0, 'below_10': 0, 'zeros': 0, 'min_capped': None} for api in APIS}
for row in rows:
    api = row['api']
    if api not in stats:
        continue
    if int(float(row['threshold_fresh'] or 0)) != 1:
        continue
    value = float(row['threshold'])
    stats[api]['fresh'] += 1
    fresh_by_tick.setdefault(row['timestamp'], {})[api] = value
    if value == PASSTHROUGH:
        continue
    stats[api]['capped'] += 1
    if stats[api]['min_capped'] is None or value < stats[api]['min_capped']:
        stats[api]['min_capped'] = value
    if value < 10.0:
        stats[api]['below_10'] += 1
    if value == 0.0:
        stats[api]['zeros'] += 1
for api in APIS:
    s = stats[api]
    print(f\"{api} fresh={s['fresh']} capped={s['capped']} min_capped={s['min_capped']} below_10={s['below_10']} zeros={s['zeros']}\")

reset_hits = 0
for stamp in sorted(fresh_by_tick):
    values = fresh_by_tick[stamp]
    if not any(values.get(api) == 0.0 for api in APIS):
        continue
    t0 = parse_ts(stamp)
    for later in sorted(fresh_by_tick):
        if later <= stamp:
            continue
        if (parse_ts(later) - t0).total_seconds() > 5:
            break
        later_values = fresh_by_tick[later]
        if all(later_values.get(api) == PASSTHROUGH for api in APIS):
            reset_hits += 1
            print(f'reset_to_10000 {stamp} -> {later}')
            break
print(f'reset_to_10000_count={reset_hits}')

proxy = (RUN / 'topfull_proxy.log').read_text(encoding='utf-8', errors='replace')
apply_re = re.compile(r'Apply threshold to (\w+) : ([0-9eE.+\-]+)')
apply_min = {api: None for api in APIS}
apply_zero = {api: 0 for api in APIS}
apply_below = {api: 0 for api in APIS}
for api, raw in apply_re.findall(proxy):
    if api not in apply_min:
        continue
    value = float(raw)
    if value == PASSTHROUGH:
        continue
    if apply_min[api] is None or value < apply_min[api]:
        apply_min[api] = value
    if value < 10.0:
        apply_below[api] += 1
    if value == 0.0:
        apply_zero[api] += 1
for api in APIS:
    print(f'proxy_apply {api} min={apply_min[api]} below_10={apply_below[api]} zeros={apply_zero[api]}')

rl = (RUN / 'topfull_rl.log').read_text(encoding='utf-8', errors='replace')
zero_branch = rl.count('zero threshold')
print(f'rl_zero_threshold_prints={zero_branch}')

pc = stats['postcheckout']
csv_zero = pc['zeros'] >= 1
proxy_zero = apply_zero['postcheckout'] >= 1
csv_below = pc['below_10'] >= 1
proxy_below = apply_below['postcheckout'] >= 1
saw_zero = 'yes' if csv_zero and proxy_zero else 'no'
if zero_branch > 0 or reset_hits > 0:
    verdict = 'reset_still_present'
elif csv_below and proxy_below:
    verdict = 'pass'
elif pc['capped'] == 0 and apply_min['postcheckout'] is None:
    verdict = 'inconclusive'
elif not csv_below and not proxy_below and (pc['min_capped'] == 10.0 or apply_min['postcheckout'] == 10.0):
    verdict = 'floor_still_10'
else:
    verdict = 'inconclusive'
print('saw_zero=' + saw_zero)
print('verdict=' + verdict)
"@
```

Meaning of the last line:

| `verdict=` | What it says |
|---|---|
| `pass` | Both the CSV and the proxy show a `postcheckout` cap strictly below 10, and the old reset did not run. `saw_zero=yes` means that cap was 0. `saw_zero=no` means the lowest written cap was in (0, 10). Either one passes the floor check. |
| `floor_still_10` | The lowest non-10000 `postcheckout` cap is 10. The old floor is still what got written. |
| `reset_still_present` | The RL log printed `zero threshold`, or a fresh 0 was followed within 5 s by all five APIs at 10000. The deleted reset branch ran. This is a regression. |
| `inconclusive` | `postcheckout` was never capped, or the CSV and the proxy log disagree. The floor was not demonstrated. This is not a crash. |

Do not launch a second hold from this plan for any verdict.

- [ ] **Step 2: Health, separate from the floor verdict**

```powershell
$d = "experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run5"
(Select-String -Path "$d/topfull_proxy.log" -Pattern "too many open files" -SimpleMatch).Count
python experiments/topfull_health.py "$d"
python experiments/analysis_score.py "$d"
```

Expected for the numbers to be citable: `too many open files` count `0`, `topfull_health.py` prints `health: ok`, and the scorer's `Throttle data quality` row is `ok`.

If any of those fail, record `not_clean` beside the verdict. A `pass` with `not_clean` does not clear the regression check: the proxy or the throttle reads were not trustworthy. The scorer's live-caps section may omit a 0; that omission alone is not `not_clean`. The hold is verified only when the verdict is `pass`, `saw_zero` is either word, `health:` is `ok`, throttle data quality is `ok`, and `too many open files` is 0.

## Task 5: Restore the cluster, free the next slot, record the hold

**Files:**
- Modify: `experiments/configs/final_configs/3/s3_tf_only.yaml` (`run_number`, `log_folder` only, and only after a pulled folder)
- Modify: `STATUS.md` (one Done bullet; the S3 next-free line)
- Modify: `AGENTS.md` (§4 Latest, three lines)

**Interfaces:**
- Consumes: the `verdict=` line and the health lines from Task 4, and whether Task 3 pulled a folder.
- Produces: the repo records the hold as verification only, and `s3_tf_only.yaml` names the next unused slot.

- [ ] **Step 1: Confirm Paper-C1 checkout and the unpinned shape**

The runner calls `reconcile_paper_cpu_limits` when the hold exits. Checkout's paper limit is `800m` ([ADR 0009](../../../docs/adr/0009-paper-c1-default-cpu-table.md)). During the hold it is `200m`.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get deploy checkoutservice -n default -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}'; echo; kubectl get hpa -n default; kubectl get deploy frontend -n default -o jsonpath='{.spec.template.metadata.annotations}'; echo"
```

Expected: checkout limit `800m`, frontend HPA min 1 max 4, catalog HPA min 1 max 2, frontend `proxyCPU` `100m`, no `proxyCPULimit`.

If the checkout limit is still `200m`, put the paper limit back and wait for the rollout:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl patch deployment checkoutservice -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"800m\"},\"requests\":{\"cpu\":\"800m\"}}}]}}}}'; kubectl rollout status deployment/checkoutservice -n default --timeout=180s"
```

Re-read the limit. Expected: `800m`. If an HPA or the sidecar annotation is still the pinned shape, repeat the restore commands in Task 1 Step 4, then re-read.

Leave the three VMs RUNNING.

- [ ] **Step 2: Bump only this YAML when a folder was pulled**

Skip this step if Task 3 did not pull a folder.

In `experiments/configs/final_configs/3/s3_tf_only.yaml` set `run_number` to `SLOT + 1` and `log_folder` to `final_s3_tf_only_run<SLOT + 1>`. When this plan was written that is `run_number: 6` and `log_folder: final_s3_tf_only_run6`. Change no other key. Leave the other four files in `final_configs/3/` at 5.

- [ ] **Step 3: Append one STATUS bullet**

Append one bullet under Done, above `## Next free slots`. Date it with the day the hold ran. Include the `log_folder`, the `verdict=` word, the `saw_zero=` word, the printed `postcheckout` stats line, the printed `proxy_apply postcheckout` line, `rl_zero_threshold_prints`, `reset_to_10000_count`, the `health:` line, and whether throttle data quality was `ok`. State `not_clean` when Task 4 Step 2 failed. Say the folder is verification only and is not a column in the S3 mode-matrix guide. Link this plan and [TOPFULL-THROTTLE-METRICS.md](../../../Guides%20and%20Info/TOPFULL-THROTTLE-METRICS.md).

If the verdict is `pass`, health is `ok`, throttle is `ok`, and `too many open files` is 0, the bullet says the hold verified both checks: no regression, and a `postcheckout` cap was written strictly below 10. Quote `saw_zero`. Do not write that 0 was required. For `floor_still_10` or `reset_still_present`, the bullet says the verification failed and names the verdict. For `inconclusive` with health `ok`, the bullet says the hold did not regress and the floor was not demonstrated.

If Step 2 bumped the YAML, split the `final_configs/3/` next-free line into two: `s3_tf_only.yaml` at `SLOT + 1`, and `s3_{rg_only_burst,rg_only_normal,both_burst,both_normal}.yaml` still at 5 (or whatever those four files still say). Do not write a bullet about the STATUS edit itself.

- [ ] **Step 4: Replace the three Latest lines in AGENTS.md §4**

Replace the three lines. Do not append. The three lines are:

1. The hold: `log_folder`, verdict word, and `saw_zero`. When the verdict is `pass` and the health lines are `ok`, say a `postcheckout` cap was written strictly below 10 and the hold did not regress. When the verdict is anything else, quote the verdict word and say the verification did not pass. Link this plan.
2. The next free slot: `s3_tf_only.yaml` is `SLOT + 1` after a pulled hold, the other S3 YAMLs are unchanged, and this folder stays verification only until the user says otherwise. The locked S3 columns remain run 3 and run 4.
3. The cluster after Step 1: checkout limit, frontend HPA, catalog HPA, sidecar annotation, and that the three VMs were left RUNNING. If Step 1 had to patch checkout back to `800m`, say so.

"Still open": if the verdict is `pass` with health `ok`, throttle `ok`, and `too many open files` 0, remove the open item that says this verification hold has not been run. The branch `cap-floor-0` stays unmerged unless the user asks to merge; leave that unmerged state in the Latest line rather than as a new open question. If the verdict is not `pass`, or the health lines are not `ok`, replace that open item with: the S3 TopFull-only cap-floor verification did not pass (`verdict=` word, plus `not_clean` when Step 2 failed). Do not remove the proxy-fd re-run decision or the mentor sign-off item.

- [ ] **Step 5: Commit only if the user asked**

```powershell
git add experiments/configs/final_configs/3/s3_tf_only.yaml "experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run5" STATUS.md AGENTS.md
git commit -m "run: S3 tf_only hold to verify the admission-cap floor of 0"
```

Substitute the pulled folder name if `SLOT` was not 5. Do not `git add` a folder that was not pulled. Do not push. Do not merge `cap-floor-0`.

---

## Self-review

Spec coverage:

- One S3 TopFull-only hold, the scenario whose earlier `tf_only` runs pinned `postcheckout` at 10 — Task 3, using `s3_tf_only.yaml`.
- The runner's existing floor install is what the hold executes, after a dry-run that refuses a mismatched live file — Tasks 1 and 2.
- No regression: the hold finishes, the RL timeout marker survives the cap-floor rewrite, and the old reset to 10000 does not run — Tasks 2, 3, and 4 (`reset_still_present`, `not_clean`).
- The cap can be written strictly below 10, and 0 is enough but not required — Task 4 `pass` with `saw_zero` either `yes` or `no`. The scorer's omission of a 0 is called out so it is not treated as failure.
- A lowest cap of exactly 10 is `floor_still_10` — Task 4. A hold that never caps `postcheckout` is `inconclusive`, which is a missing demonstration, not a crash.
- The hold stays out of the locked S3 matrix, the YAML slot advances only after a pull, and STATUS / AGENTS record the verdict — Task 5.
- Checkout returns to paper `800m` and the cluster stays unpinned — Task 5 Step 1.

Placeholder scan: no TBD, no "handle edge cases", no "similar to Task N". `SLOT` is defined in Task 1 as the number STATUS prints, with the value at writing time (5) stated next to it.

Type consistency: `ensure_cap_floor`, `patch_overload_detection`, `patch_deploy_rl`, `patch_proxy_burst`, `TOPFULL_CAP_FLOOR`, and `RL_TIMEOUT_PATCH v1` match `experiments/topfull_cap_floor.py` and `experiments/run_scenario.py`. The verdict words `pass`, `floor_still_10`, `reset_still_present`, `inconclusive`, and `not_clean`, and the `saw_zero` words `yes` and `no`, are the same words in Task 4 and Task 5.
