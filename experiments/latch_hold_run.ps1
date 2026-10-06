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
