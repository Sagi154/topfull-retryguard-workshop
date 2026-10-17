# Run remaining analysis-runs replay holds (plan Task 3).
# Usage (from worktree root):
#   powershell -File experiments/run_replay_holds.ps1
# Optional: -FromIndex 3  (1-based row in $Holds; default 1 = first remaining)

param(
  [int]$FromIndex = 1
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $PSScriptRoot\..

$Holds = @(
  @{ C = "experiments/configs/analysis_runs_replay/s2/s2_tf_only_run3.yaml"; D = "experiments/results/final_runs_results/S2_sustained_overload_normal/tf_only/analysis_s2_tf_only_run3"; Name = "analysis_s2_tf_only_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s2/s2_rg_only_burst_run3.yaml"; D = "experiments/results/final_runs_results/S2_sustained_overload_burst/rg_only/analysis_s2_rg_only_burst_run3"; Name = "analysis_s2_rg_only_burst_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s2/s2_both_burst_run3.yaml"; D = "experiments/results/final_runs_results/S2_sustained_overload_burst/both/analysis_s2_both_burst_run3"; Name = "analysis_s2_both_burst_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s3/s3_rg_only_normal_run3.yaml"; D = "experiments/results/final_runs_results/S3_targeted_bottleneck_normal/rg_only/analysis_s3_rg_only_normal_run3"; Name = "analysis_s3_rg_only_normal_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s3/s3_both_normal_run3.yaml"; D = "experiments/results/final_runs_results/S3_targeted_bottleneck_normal/both/analysis_s3_both_normal_run3"; Name = "analysis_s3_both_normal_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s3/s3_tf_only_run3.yaml"; D = "experiments/results/final_runs_results/S3_targeted_bottleneck_normal/tf_only/analysis_s3_tf_only_run3"; Name = "analysis_s3_tf_only_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s3/s3_rg_only_burst_run3.yaml"; D = "experiments/results/final_runs_results/S3_targeted_bottleneck_burst/rg_only/analysis_s3_rg_only_burst_run3"; Name = "analysis_s3_rg_only_burst_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s3/s3_both_burst_run3.yaml"; D = "experiments/results/final_runs_results/S3_targeted_bottleneck_burst/both/analysis_s3_both_burst_run3"; Name = "analysis_s3_both_burst_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_rg_only_normal_run3.yaml"; D = "experiments/results/final_runs_results/S4A_topology_position_normal/rg_only/analysis_4a_unconstrained_rg_only_normal_run3"; Name = "analysis_4a_unconstrained_rg_only_normal_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_both_normal_run3.yaml"; D = "experiments/results/final_runs_results/S4A_topology_position_normal/both/analysis_4a_unconstrained_both_normal_run3"; Name = "analysis_4a_unconstrained_both_normal_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_tf_only_run3.yaml"; D = "experiments/results/final_runs_results/S4A_topology_position_normal/tf_only/analysis_4a_unconstrained_tf_only_run3"; Name = "analysis_4a_unconstrained_tf_only_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_rg_only_burst_run3.yaml"; D = "experiments/results/final_runs_results/S4A_topology_position_burst/rg_only/analysis_4a_unconstrained_rg_only_burst_run3"; Name = "analysis_4a_unconstrained_rg_only_burst_run3" },
  @{ C = "experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_both_burst_run3.yaml"; D = "experiments/results/final_runs_results/S4A_topology_position_burst/both/analysis_4a_unconstrained_both_burst_run3"; Name = "analysis_4a_unconstrained_both_burst_run3" }
)

function Assert-Pin {
  $out = @'
import json, subprocess
def get(args):
    return json.loads(subprocess.check_output(["kubectl", *args]))
fe = get(["get", "hpa", "frontend-hpa", "-n", "default", "-o", "json"])
ca = get(["get", "hpa", "productcatalogservice-hpa", "-n", "default", "-o", "json"])
fd = get(["get", "deploy", "frontend", "-n", "default", "-o", "json"])
cd = get(["get", "deploy", "productcatalogservice", "-n", "default", "-o", "json"])
ann = fd["spec"]["template"]["metadata"].get("annotations", {})
print("frontend_hpa", fe["spec"]["minReplicas"], fe["spec"]["maxReplicas"], fd["status"].get("readyReplicas"))
print("catalog_hpa", ca["spec"]["minReplicas"], ca["spec"]["maxReplicas"], cd["status"].get("readyReplicas"))
print("proxyCPU", ann.get("sidecar.istio.io/proxyCPU"))
print("proxyCPULimit", ann.get("sidecar.istio.io/proxyCPULimit"))
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master python3 -
  Write-Host $out
  if ($out -notmatch "frontend_hpa 4 4 4") { throw "pin fail: $out" }
  if ($out -notmatch "catalog_hpa 1 1 1") { throw "pin fail: $out" }
  if ($out -notmatch "proxyCPU 90m") { throw "pin fail: $out" }
  if ($out -notmatch "proxyCPULimit None") { throw "pin fail: $out" }
}

function Clear-Writers {
  ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true" | Out-Null
  ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; pkill -f '[p]roxy_fd_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true" | Out-Null
  $l = ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "ps -ef | grep -E 'locust' | grep -v grep || echo locust-clear"
  $m = ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ps -ef | grep -E 'metric_collector|deploy_rl|proxy_online|retryguard|envoy_retry|resource_usage|topfull_throttle|proxy_fd' | grep -v grep || echo master-clear"
  Write-Host "load: $l"
  Write-Host "master: $m"
  if ($l -notmatch "locust-clear") { throw "locust still alive: $l" }
  if ($m -notmatch "master-clear") { throw "master writers still alive: $m" }
  ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs" | Out-Null
  ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/rg_proxy_fd.sh /tmp/proxy_fd_params.json" | Out-Null
}

$logPath = "docs/superpowers/plans/2026-10-17-analysis-runs-replay-log.md"
$i = 0
foreach ($h in $Holds) {
  $i++
  if ($i -lt $FromIndex) { continue }
  Write-Host "===== HOLD $i/$($Holds.Count) $($h.Name) ====="
  Assert-Pin
  Clear-Writers
  Assert-Pin
  python experiments/run_scenario.py $h.C
  $exitAt = Get-Date
  if ($LASTEXITCODE -ne 0) {
    Add-Content -Path $logPath -Value "$($h.Name) | exit failed | throttle - | health - | replicas - | runner rc=$LASTEXITCODE" -Encoding utf8
    throw "run_scenario failed for $($h.Name) rc=$LASTEXITCODE"
  }
  python experiments/pull_results.py $h.C
  if ($LASTEXITCODE -ne 0) { throw "pull failed for $($h.Name)" }
  $rep = python -c "import csv,sys; from collections import defaultdict; d=defaultdict(set)
for row in csv.DictReader(open(sys.argv[1], newline='')):
    if row['service'] in ('frontend','productcatalogservice'):
        d[row['service']].add(int(float(row['replica_count'])))
print(dict(d))" "$($h.D)/resource_usage.csv"
  Write-Host "REPLICAS=$rep"
  if ($rep -ne "{'frontend': {4}, 'productcatalogservice': {1}}") {
    throw "replica pin failed for $($h.Name): $rep"
  }
  $finish = python experiments/replay_finish_hold.py $h.D
  Write-Host $finish
  $line = ($finish -split "`r?`n" | Where-Object { $_ -like 'analysis_*' } | Select-Object -First 1)
  $tag = (($finish -split "`r?`n" | Where-Object { $_ -like 'TAG=*' } | Select-Object -First 1) -replace '^TAG=', '')
  if (-not $line) { throw "no log line for $($h.Name)" }
  Add-Content -Path $logPath -Value $line -Encoding utf8
  git add -- $h.D $logPath
  git commit -m "data: $($h.Name) ($tag)"
  git push -u origin HEAD
  if ($LASTEXITCODE -ne 0) { throw "push failed after $($h.Name)" }
  $remain = [Math]::Max(0, 120 - ((Get-Date) - $exitAt).TotalSeconds)
  # cool-off from run_scenario exit; pull/score/commit already used some of it
  Write-Host "cool-off sleep $remain s"
  Start-Sleep -Seconds $remain
  Write-Host "DONE $($h.Name)"
}

Write-Host "ALL_REMAINING_HOLDS_DONE"
