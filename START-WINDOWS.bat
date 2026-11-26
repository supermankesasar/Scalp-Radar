@echo off
setlocal
cd /d "%~dp0"
rem One launcher for daytime and overnight: scanner, research and market archive.
set "SCANNER_OVERNIGHT=1"
set "SCANNER_BACKGROUND=1"
set "SCANNER_WEBSOCKET=1"
set "SCANNER_R10=1"
set "SCANNER_R11=1"
if not defined SCANNER_LIVE_FILTER set "SCANNER_LIVE_FILTER=R08_MULTI_CORE"
set "HOST=127.0.0.1"
set "PORT=8765"
set "SCANNER_OPEN_BROWSER=1"
rem if not defined SCANNER_DB, local_runner.py selects persistent database
rem Avoid starting a second collector against the same database if port is occupied.
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo Port 8765 is already in use or the port check failed.
  echo Close the existing Scalp Radar terminal before starting again.
  pause
  exit /b 1
)
echo Scalp Radar R11 preview - R08 dashboard and R10 retained
echo Database: persistent local path (or SCANNER_DB override)
echo Live filter: %SCANNER_LIVE_FILTER%
echo Browser: http://127.0.0.1:8765
echo Collection: http://127.0.0.1:8765/api/overnight
echo Research: http://127.0.0.1:8765/api/research
echo WebSocket: http://127.0.0.1:8765/api/websocket
echo Research 1M: http://127.0.0.1:8765/api/research/1m
echo R10: http://127.0.0.1:8765/api/research/r10
echo R11 preview: http://127.0.0.1:8765/api/radar/r11
echo REST budget: http://127.0.0.1:8765/api/rest-budget
echo Runtime: http://127.0.0.1:8765/api/runtime
echo Keep this terminal and PC running. Browser may be closed.
where py >nul 2>&1
if not errorlevel 1 (
  set "PY=py -3"
) else (
  set "PY=python"
)
%PY% -c "import websockets; assert websockets.__version__ == '15.0.1'" >nul 2>&1
if errorlevel 1 (
  echo Installing required WebSocket library...
  %PY% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo WebSocket dependency installation failed. Check internet or Python installation.
    pause
    exit /b 1
  )
)
%PY% -u local_runner.py
set "RESULT=%errorlevel%"
echo Server stopped. Review the messages above.
pause
exit /b %RESULT%
