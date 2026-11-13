@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Lipseste Python Launcher. Instaleaza Python 3.12 de la https://www.python.org/downloads/windows/
  if not "%EAON_NO_PAUSE%"=="1" pause
  exit /b 1
)
py -3.12 -I -X utf8 "%~dp0scripts\setup_local.py" %*
set "EAON_EXIT=%ERRORLEVEL%"
if not "%EAON_NO_PAUSE%"=="1" pause
exit /b %EAON_EXIT%
