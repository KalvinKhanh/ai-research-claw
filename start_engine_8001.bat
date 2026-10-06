@echo off
chcp 65001 > nul
title AutoResearchClaw Engine - Port 8001
cd /d "%~dp0"

echo ========================================================
echo   AutoResearchClaw - Engine Server (Port 8001)
echo ========================================================
echo.
echo Đang chạy Engine trên port 8001...
echo Swagger: http://localhost:8001/docs
echo.

set PORT=8001
".venv\Scripts\python.exe" "scripts\phase1_fastapi_server.py"

pause
