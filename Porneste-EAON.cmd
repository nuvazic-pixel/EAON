@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Ruleaza mai intai Instaleaza-EAON.cmd. Mediul local lipseste.
  if not "%EAON_NO_PAUSE%"=="1" pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -I "%~dp0scripts\launch_local.py" %*
set "EAON_EXIT=%ERRORLEVEL%"
if not "%EAON_NO_PAUSE%"=="1" pause
exit /b %EAON_EXIT%
