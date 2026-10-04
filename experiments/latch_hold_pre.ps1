param(
    [Parameter(Mandatory)][string]$Treatment,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

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
if ($rc -ne 0) { Write-Error "prep failed rc=$rc"; exit 1 }

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
