@echo off
setlocal
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
if exist "%~dp0.venv\Scripts\python.exe" (
  set "OYE_PYTHON=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0toolkit\python.exe" (
  set "OYE_PYTHON=%~dp0toolkit\python.exe"
) else (
  echo Python environment is missing. See docs\RUNNING.md.
  pause
  exit /b 1
)
"%OYE_PYTHON%" "%~dp0server.py" %*
set "OYE_EXIT_CODE=%ERRORLEVEL%"
if not "%OYE_EXIT_CODE%"=="0" pause
exit /b %OYE_EXIT_CODE%
