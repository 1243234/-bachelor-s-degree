@echo off
setlocal
cd /d "%~dp0teaching_ppt"
title TeachingPPT Uvicorn (close this window to stop server)
echo Working directory: %CD%
echo.

if not exist "app\main.py" (
  echo ERROR: teaching_ppt\app\main.py not found.
  echo Expected the app with /minimal under "%~dp0teaching_ppt".
  pause
  exit /b 1
)

if not exist "%~dp0.venv\Scripts\python.exe" (
  echo ERROR: .venv\Scripts\python.exe not found at repo root.
  echo Run start-minimal.cmd from "%~dp0" first.
  pause
  exit /b 1
)

"%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo Uvicorn stopped. Exit code: %ERRORLEVEL%
pause
