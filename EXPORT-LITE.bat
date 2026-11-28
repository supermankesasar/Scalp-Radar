@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 export_lite.py --open-folder %*
) else (
  python export_lite.py --open-folder %*
)
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" echo Export FAILED. Copy the error above.
pause
exit /b %RESULT%
