@echo off
setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%"

where uv >nul 2>&1
if errorlevel 1 (
  echo Hardwise needs uv on PATH. Install it from https://docs.astral.sh/uv/
  pause
  exit /b 1
)

if defined HARDWISE_PORT (
  for /f "usebackq delims=" %%P in (`powershell.exe -NoProfile -Command "$p=0; if (-not [int]::TryParse($env:HARDWISE_PORT, [ref]$p) -or $p -lt 1 -or $p -gt 65535) { exit 2 }; try { $l=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$p); $l.Start(); $l.Stop(); $p } catch { exit 3 }"`) do set "PORT=%%P"
  if not defined PORT (
    echo HARDWISE_PORT=%HARDWISE_PORT% is invalid or already in use. Choose a free port from 1 to 65535.
    pause
    exit /b 1
  )
) else (
  for /f "usebackq delims=" %%P in (`powershell.exe -NoProfile -Command "foreach ($p in 8765..8785) { try { $l=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$p); $l.Start(); $l.Stop(); $p; break } catch {} }"`) do if not defined PORT set "PORT=%%P"
  if not defined PORT (
    echo Hardwise could not find a free port in 8765-8785. Set HARDWISE_PORT to another free port.
    pause
    exit /b 1
  )
  if not "!PORT!"=="8765" echo Port 8765 is already in use; using port !PORT! instead.
)

set "URL=http://127.0.0.1:%PORT%/"
set "NETLIST=tests/fixtures/allegro/mixed_controller_power_stage.net"
set "BOM=tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"
set "DOC_INDEX=data/document_indexes/mixed_controller_power_stage_docs.csv"

echo Preparing Hardwise dependencies...
uv sync
if errorlevel 1 (
  pause
  exit /b 1
)

echo The browser will open when Hardwise is ready at %URL%
start "" /b powershell.exe -NoProfile -Command "$url='%URL%'; foreach ($attempt in 1..120) { try { Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 1 | Out-Null; Start-Process $url; exit } catch {}; Start-Sleep -Milliseconds 250 }; Write-Error ('Hardwise did not become ready at ' + $url + ' within 30 seconds.')"

echo Starting Hardwise Workbench with the built-in demo project.
echo Close this window or press Ctrl+C to stop the server.
uv run hardwise serve-workbench "%NETLIST%" "%BOM%" --document-index "%DOC_INDEX%" --port %PORT%
if errorlevel 1 pause
