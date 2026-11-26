@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 migrate_database.py %*
) else (
  python migrate_database.py %*
)
pause
