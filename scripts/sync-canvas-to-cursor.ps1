# Copies the workplan canvas (and editor types) to Cursor's managed canvases folder
# so the live Canvas preview works. Run from repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\sync-canvas-to-cursor.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$managed = Join-Path $env:USERPROFILE ".cursor\projects\c-Users-idoza-topfull-retryguard-workshop\canvases"

New-Item -ItemType Directory -Force -Path $managed | Out-Null

$files = @(
  "topfull-retryguard-workplan.canvas.tsx",
  "package.json",
  "package-lock.json",
  "tsconfig.json"
)

foreach ($name in $files) {
  $src = Join-Path $repoRoot "canvases\$name"
  if (Test-Path $src) {
    Copy-Item -Force $src (Join-Path $managed $name)
    Write-Host "Copied $name"
  }
}

Write-Host ""
Write-Host "Open this file in Cursor, then Ctrl+Shift+P -> Open Canvas:"
Write-Host (Join-Path $managed "topfull-retryguard-workplan.canvas.tsx")
