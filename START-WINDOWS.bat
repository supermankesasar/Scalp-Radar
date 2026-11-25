@echo off
setlocal
cd /d "%~dp0"
rem One launcher for daytime and overnight: scanner, research and market archive.
set "SCANNER_OVERNIGHT=1"
set "SCANNER_BACKGROUND=1"
if not defined SCANNER_LIVE_FILTER set "SCANNER_LIVE_FILTER=R08_MULTI_CORE"
set "HOST=127.0.0.1"
set "PORT=8765"
set "SCANNER_OPEN_BROWSER=1"
if not defined SCANNER_DB set "SCANNER_DB=%~dp0data\signals.sqlite3"
rem Avoid starting a second collector against the same database if port is occupied.
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo Port 8765 is already in use or the port check failed.
  echo Close the existing Scalp Radar terminal before starting again.
  pause
  exit /b 1
)
echo Scalp Radar - ALL crypto USDT Perpetuals
echo Database: %SCANNER_DB%
echo Live filter: %SCANNER_LIVE_FILTER%
echo Browser: http://127.0.0.1:8765
echo Collection: http://127.0.0.1:8765/api/overnight
echo Research: http://127.0.0.1:8765/api/research
echo Keep this terminal and PC running. Browser may be closed.
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -u app.py
) else (
  python -u app.py
)
set "RESULT=%errorlevel%"
echo Server stopped. Review the messages above.
pause
exit /b %RESULT%
