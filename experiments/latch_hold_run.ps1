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

if ((Test-Path $dest) -or (Test-Path $src)) { throw "$name already exists locally; refusing to overwrite" }

Step "t=0 snapshot" { New-Item -ItemType Directory -Force $S | Out-Null; Save-Snapshot "$S\t0.txt" }
Step "generate config" { python experiments/s2_latch_probe.py config $Treatment $Slot }
Step "clear stale remote scripts" {
    ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
}
Step "run hold (about 17 min)" { python experiments/run_scenario.py $cfg }
Step "pull" { python experiments/pull_results.py $cfg }
Step "move into new vms" { Move-Item $src "experiments\results\new vms\" }
Step "end snapshot" { Save-Snapshot "$S\end.txt" }
Step "copy snapshots into run folder" { Copy-Item $S "$dest\state" -Recurse }

if ($DryRun) { exit 0 }

python experiments/s2_latch_probe.py gate $Treatment $Slot
$gateRc = $LASTEXITCODE
python experiments/s2_latch_probe.py score $Slot
exit $gateRc
