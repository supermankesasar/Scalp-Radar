@echo off
setlocal
cd /d "%~dp0"
set "SCANNER_OVERNIGHT=1"
set "SCANNER_BACKGROUND=1"
set "HOST=127.0.0.1"
set "PORT=8765"
if not defined SCANNER_DB set "SCANNER_DB=%~dp0data\signals.sqlite3"
echo Scalp Radar - ALL crypto USDT Perpetuals
echo Database: %SCANNER_DB%
echo Browser: http://127.0.0.1:8765
echo Collection: http://127.0.0.1:8765/api/overnight
echo Keep this window and PC running. Browser may be closed.
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -u app.py
) else (
  python -u app.py
)
echo Server stopped. Review the messages above.
pause
