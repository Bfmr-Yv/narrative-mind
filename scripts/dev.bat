@echo off
cd /d "%~dp0.."

echo Starting Narrative Mind v0.0.1-beta...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1"
pause
