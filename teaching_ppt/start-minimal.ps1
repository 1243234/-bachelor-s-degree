#Requires -Version 5.1
# Start uvicorn only; open http://127.0.0.1:8000/minimal
# Use ASCII-only text so Windows PowerShell 5.1 never breaks on encoding.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

function Resolve-SystemPython {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd -and (Test-Path -LiteralPath $cmd.Source)) {
        return $cmd.Source
    }
    $cmd = Get-Command py.exe -ErrorAction SilentlyContinue
    if (-not $cmd) { return $null }
    try {
        $exe = (
            & py.exe -3 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1
        ).ToString().Trim()
        if ($exe -and (Test-Path -LiteralPath $exe)) { return $exe }
    } catch { }
    return $null
}

function Open-DefaultBrowser {
    param([string]$Url)
    cmd.exe /c start "" $Url
}

$venvPy = Join-Path $Root '.venv\Scripts\python.exe'
$venvPip = Join-Path $Root '.venv\Scripts\pip.exe'
$reqFile = Join-Path $Root 'requirements.txt'
$minimalUrl = 'http://127.0.0.1:8000/minimal'
$healthUrl = 'http://127.0.0.1:8000/health'

if (-not (Test-Path -LiteralPath $venvPy)) {
    Write-Host "[start-minimal] No .venv yet; creating venv and installing deps..."
    $sysPy = Resolve-SystemPython
    if (-not $sysPy) {
        Write-Host "[start-minimal] ERROR: python.exe or py.exe not found."
        Write-Host "Install Python 3.11+ and check 'Add Python to PATH', or install Python Launcher."
        exit 1
    }
    Write-Host "[start-minimal] Using interpreter: $sysPy"
    try {
        & $sysPy -m venv .venv
    } catch {
        Write-Host "[start-minimal] venv creation failed. If 'access denied': move project out of protected/sync folder, or run as Administrator."
        throw
    }
    if (-not (Test-Path -LiteralPath $venvPip)) {
        Write-Host "[start-minimal] pip.exe missing under .venv\Scripts."
        exit 1
    }
    & $venvPip install -r $reqFile
}

try {
    $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) {
        Write-Host "[start-minimal] Server already up; opening browser."
        Open-DefaultBrowser -Url $minimalUrl
        exit 0
    }
} catch { }

$uvicornBat = Join-Path $Root 'run-uvicorn-visible.bat'
if (-not (Test-Path -LiteralPath $uvicornBat)) {
    Write-Host "[start-minimal] ERROR: run-uvicorn-visible.bat missing in project root."
    exit 1
}
Write-Host "[start-minimal] Starting Uvicorn in a new window (see TeachingPPT-Uvicorn)..."
try {
    $proc = Start-Process -FilePath $uvicornBat -WorkingDirectory $Root -WindowStyle Normal -PassThru
} catch {
    Write-Host "[start-minimal] Start-Process failed: $($_.Exception.Message)"
    exit 1
}

$ok = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 1
        if ($r.StatusCode -eq 200) {
            $ok = $true
            break
        }
    } catch { }
    Start-Sleep -Milliseconds 500
}

if (-not $ok) {
    Write-Host "[start-minimal] Timeout waiting for /health. Check: port 8000 in use, or pip install -r requirements.txt"
    Write-Host "[start-minimal] If python started, see Task Manager (PID may be $($proc.Id))."
    exit 1
}

Write-Host "[start-minimal] Opening: $minimalUrl"
Open-DefaultBrowser -Url $minimalUrl
Write-Host "[start-minimal] Done. Uvicorn runs in background; stop the python.exe process to quit."
