@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>&1
if errorlevel 1 (
  echo Install Git for Windows first: https://git-scm.com/download/win
  pause
  exit /b 1
)
where py >nul 2>&1
if errorlevel 1 (
  python -u auto_update.py
) else (
  py -3 -u auto_update.py
)
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" pause
exit /b %RESULT%
