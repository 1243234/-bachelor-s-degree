@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Teaching PPT - start minimal UI

echo ========================================
echo Teaching PPT - minimal launcher
echo Root: %CD%
echo ========================================
echo.

if not exist "requirements.txt" (
  echo ERROR: requirements.txt not found. Run this CMD from the project folder.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment .venv ...
  python -m venv .venv 2>nul
  if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
  )
  if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Cannot create venv. Install Python 3.11+ and add to PATH ^(or use py launcher^).
    pause
    exit /b 1
  )
  echo Installing dependencies ^(first time may take a few minutes^)...
  call ".venv\Scripts\pip.exe" install -r requirements.txt
  if errorlevel 1 (
    echo pip install failed.
    pause
    exit /b 1
  )
)

echo Starting Uvicorn in a NEW window ^(keep it open; errors will show there^)...
start "TeachingPPT-Uvicorn" "%~dp0run-uvicorn-visible.bat"

echo Waiting for http://127.0.0.1:8000/health ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ok=$false; for($i=0; $i -lt 90; $i++) { try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){ $ok=$true; break } } catch {}; Start-Sleep -Milliseconds 500 }; if(-not $ok){ exit 1 }"

if errorlevel 1 (
  echo.
  echo Timed out: server did not respond on port 8000.
  echo Check the "TeachingPPT-Uvicorn" window for Python errors ^(missing module, port in use, etc.^).
  echo.
  pause
  exit /b 1
)

echo Opening browser...
start "" "http://127.0.0.1:8000/minimal"
echo.
echo OK. Leave the Uvicorn window running. Close it to stop the server.
pause
