@echo off
cd /d "%~dp0"
call EXPORT-LITE.bat --daily --complete %*
exit /b %errorlevel%
