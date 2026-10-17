@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\first_run.ps1" %*
if errorlevel 1 (
  echo Installation or startup failed. Please read the error above and run start.bat again.
  pause
  exit /b 1
)
