$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RootDir

$Url = "http://127.0.0.1:8765/"
$Netlist = "tests/fixtures/allegro/mixed_controller_power_stage.net"
$Bom = "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Hardwise needs uv on PATH. Install it from https://docs.astral.sh/uv/"
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Preparing Hardwise dependencies..."
uv sync

Write-Host "Opening $Url"
Start-Job -ScriptBlock {
    param($WorkbenchUrl)
    Start-Sleep -Seconds 2
    Start-Process $WorkbenchUrl
} -ArgumentList $Url | Out-Null

Write-Host "Starting Hardwise Workbench with the built-in demo project."
Write-Host "Close this window or press Ctrl+C to stop the server."
uv run hardwise serve-workbench $Netlist $Bom --port 8765
