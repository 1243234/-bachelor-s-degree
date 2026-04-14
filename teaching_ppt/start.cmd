@echo off
setlocal
cd /d "%~dp0"
title Teaching PPT - start

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 (
  echo.
  echo Start script failed; see output above.
  pause
  exit /b 1
)
echo.
pause
