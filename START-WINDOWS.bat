@echo off
cd /d "%~dp0"
set "RESEARCH_AUTO=1"
start "" "http://127.0.0.1:8765"
where py >nul 2>nul
if %errorlevel%==0 (py app.py) else (python app.py)
pause