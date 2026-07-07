# Narrative Mind v4.0 - Dev Launch Script
# Usage: .\scripts\dev.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Write-Host '========================================' -ForegroundColor Cyan
Write-Host ' Narrative Mind v4.0 - Dev Launch' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''

# --- 0. Cleanup leftover ports from previous runs ---
Write-Host '[0/3] Cleaning up leftover ports...' -ForegroundColor DarkGray
foreach ($port in @(9091, 1420)) {
    $pids = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($pid in $pids) {
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  Killed PID $pid on port $port" -ForegroundColor DarkGray
        } catch { }
    }
}
# Also clean up any leftover PowerShell background jobs from previous sessions
Get-Job -Name 'nm-sidecar','nm-vite' -ErrorAction SilentlyContinue | Remove-Job -Force -ErrorAction SilentlyContinue
Write-Host ''

# --- 1. Python Sidecar ---
Write-Host '[1/3] Starting Python Sidecar (localhost:9091)...' -ForegroundColor Yellow

$pythonExe = "$root\src-python\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host 'ERROR: venv not found.' -ForegroundColor Red
    Write-Host 'Run: cd src-python ; python -m venv .venv ; .venv\Scripts\pip install -r requirements.txt' -ForegroundColor Red
    exit 1
}

$sidecarJob = Start-Job -Name 'nm-sidecar' -ScriptBlock {
    param($py, $dir, $logFile)
    Set-Location $dir
    & $py main.py > $logFile 2>&1
} -ArgumentList $pythonExe, "$root\src-python", "$root\sidecar.log"

Write-Host '  Waiting for sidecar...' -NoNewline
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:9091/v1/llm/health' -TimeoutSec 1 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch { }
    Write-Host '.' -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host ''

if ($ready) {
    Write-Host '  Sidecar is ready!' -ForegroundColor Green
} else {
    Write-Host '  WARNING: Sidecar not ready. Analysis may not work.' -ForegroundColor DarkYellow
}

# --- 2. Frontend (Vite dev server) ---
Write-Host '[2/3] Starting Vite dev server (localhost:1420)...' -ForegroundColor Yellow

$viteDir = "$root\src-frontend"
if (-not (Test-Path "$viteDir\node_modules")) {
    Write-Host '  Installing frontend deps...' -ForegroundColor Yellow
    Set-Location $viteDir
    npm install
}

$viteJob = Start-Job -Name 'nm-vite' -ScriptBlock {
    param($dir)
    Set-Location $dir
    npx vite --port 1420 --strictPort 2>&1 | Out-Null
} -ArgumentList $viteDir

Write-Host '  Waiting for Vite...' -NoNewline
$viteReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri 'http://localhost:1420' -TimeoutSec 1 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($resp.StatusCode -eq 200) {
            $viteReady = $true
            break
        }
    } catch { }
    Write-Host '.' -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host ''

if ($viteReady) {
    Write-Host '  Vite is ready!' -ForegroundColor Green
} else {
    Write-Host '  ERROR: Vite failed to start.' -ForegroundColor Red
    Stop-Job -Name 'nm-sidecar' -ErrorAction SilentlyContinue
    exit 1
}

# --- 3. Tauri Dev ---
Write-Host '[3/3] Launching Tauri desktop app...' -ForegroundColor Yellow
Write-Host '  App window will open. Close this terminal to stop all services.' -ForegroundColor DarkGray
Write-Host ''

Set-Location "$root"
$tauriExe = "$viteDir\node_modules\.bin\tauri.cmd"
if (-not (Test-Path $tauriExe)) {
    Write-Host 'ERROR: tauri CLI not found. Run: cd src-frontend ; npm install' -ForegroundColor Red
    Stop-Job -Name 'nm-sidecar','nm-vite' -ErrorAction SilentlyContinue
    exit 1
}

try {
    & $tauriExe dev
} finally {
    Write-Host ''
    Write-Host 'Cleaning up background services...' -ForegroundColor Yellow
    Stop-Job -Name 'nm-sidecar','nm-vite' -ErrorAction SilentlyContinue
    Remove-Job -Name 'nm-sidecar','nm-vite' -Force -ErrorAction SilentlyContinue
    Write-Host 'Stopped. Bye!' -ForegroundColor Cyan
}
