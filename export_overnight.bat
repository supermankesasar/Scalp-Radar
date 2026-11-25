@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 export_overnight.py
) else (
  python export_overnight.py
)
pause
