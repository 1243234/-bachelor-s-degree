"""One-off: write start.ps1 with UTF-8 BOM for Windows PowerShell 5.1."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = r"""# UTF-8 BOM note: keep this file encoded as UTF-8 with BOM for best compatibility.
#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Join-Path $Root 'teaching_ppt'

$venvPy = Join-Path $Root '.venv\Scripts\python.exe'
$venvPip = Join-Path $Root '.venv\Scripts\pip.exe'
$reqFile = Join-Path $Root 'requirements.txt'
if (-not (Test-Path -LiteralPath $venvPy)) {
    Write-Host '[start] venv not found; creating and installing dependencies...'
    & python -m venv .venv
    if (-not (Test-Path -LiteralPath $venvPip)) {
        throw 'Failed to create venv; please ensure Python is installed and "python" is available.'
    }
    & $venvPip install -r $reqFile
}

if (-not (Test-Path -LiteralPath (Join-Path $AppRoot 'app\main.py'))) {
    throw "Application not found: $AppRoot\app\main.py"
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root 'logs') | Out-Null
$webOut = Join-Path $Root 'logs\web.log'
$webErr = Join-Path $Root 'logs\web.err.log'

Write-Host '[start] Starting Web (8000) from teaching_ppt...'
$webP = Start-Process -FilePath $venvPy -WorkingDirectory $AppRoot -ArgumentList @(
    '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'
) -WindowStyle Hidden -RedirectStandardOutput $webOut -RedirectStandardError $webErr -PassThru

Write-Host ''
Write-Host '[start] Done. Open http://localhost:8000/minimal'
Write-Host ("[start] Web PID={0}" -f $webP.Id)
Write-Host '[start] To stop: terminate that PID.'
"""

if __name__ == "__main__":
    out = ROOT / "start.ps1"
    out.write_text(CONTENT, encoding="utf-8-sig", newline="\r\n")
    print("Wrote", out, "with UTF-8 BOM")
