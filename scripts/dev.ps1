# Narrative Mind v4.0 - Dev Launch Script
# Usage: .\scripts\dev.ps1
#
# LLM 配置优先级:
#   1. 当前 session 的环境变量 (LLM_API_KEY / LLM_BASE_URL / LLM_MODEL)
#   2. config/llm.json（gitignored，放这里一劳永逸）
#   3. 都不设 → 仍然启动，但分析功能不可用

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Write-Host '========================================' -ForegroundColor Cyan
Write-Host ' Narrative Mind v4.0 - Dev Launch' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''

# --- 0. Load LLM config ---
Write-Host '[0/3] Loading LLM config...' -ForegroundColor DarkGray

$llmConfigFile = Join-Path $root 'config\llm.json'

if (Test-Path $llmConfigFile) {
    $llmConfig = $null
    try { $llmConfig = Get-Content $llmConfigFile -Raw | ConvertFrom-Json } catch {}

    if ($llmConfig) {
        if (-not $env:LLM_API_KEY) {
            $key = $llmConfig.api_key
            if ($key -and $key -ne 'your-api-key-here') {
                $env:LLM_API_KEY = $key
                Write-Host "  LLM_API_KEY loaded from config/llm.json" -ForegroundColor DarkGray
            }
        }
        if (-not $env:LLM_BASE_URL) {
            $url = $llmConfig.base_url
            if ($url) { $env:LLM_BASE_URL = $url; Write-Host "  LLM_BASE_URL = $url" -ForegroundColor DarkGray }
        }
        if (-not $env:LLM_MODEL) {
            $model = $llmConfig.model
            if ($model) { $env:LLM_MODEL = $model; Write-Host "  LLM_MODEL   = $model" -ForegroundColor DarkGray }
        }
        if (-not $env:LLM_PROVIDER) {
            $provider = $llmConfig.provider
            if ($provider) { $env:LLM_PROVIDER = $provider }
        }
    } else {
        Write-Host "  WARNING: Failed to parse config/llm.json" -ForegroundColor Yellow
    }
} else {
    Write-Host "  config/llm.json not found — copy config/llm.example.json and fill in your key" -ForegroundColor Yellow
}

if ($env:LLM_API_KEY) {
    $len = $env:LLM_API_KEY.Length
    $show = if ($len -gt 8) { $env:LLM_API_KEY.Substring(0, 8) } else { $env:LLM_API_KEY.Substring(0, [Math]::Max(1, $len - 4)) }
    Write-Host "  LLM ready (key: ${show}...)" -ForegroundColor Green
} else {
    Write-Host "  LLM not configured — analysis will fail" -ForegroundColor Yellow
}
Write-Host ''

# --- 1. Cleanup leftover ports from previous runs ---
Write-Host '[1/3] Cleaning up leftover ports...' -ForegroundColor DarkGray
foreach ($port in @(1420)) {
    $pids = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($pid in $pids) {
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  Killed PID $pid on port $port" -ForegroundColor DarkGray
        } catch { }
    }
}
# Clean up leftover Vite job from previous sessions
Get-Job -Name 'nm-vite' -ErrorAction SilentlyContinue | Remove-Job -Force -ErrorAction SilentlyContinue
Write-Host ''

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
    Stop-Job -Name 'nm-vite' -ErrorAction SilentlyContinue
    exit 1
}

try {
    & $tauriExe dev
} finally {
    Write-Host ''
    Write-Host 'Cleaning up background services...' -ForegroundColor Yellow
    Stop-Job -Name 'nm-vite' -ErrorAction SilentlyContinue
    Remove-Job -Name 'nm-vite' -Force -ErrorAction SilentlyContinue
    Write-Host 'Stopped. Bye!' -ForegroundColor Cyan
}
