@echo off
chcp 65001 > nul
title AutoResearchClaw - FastAPI Swagger Server (Phase 1)
cd /d "%~dp0"

echo ========================================================
echo   AutoResearchClaw - Khởi Động FastAPI & Swagger UI
echo ========================================================
echo.
echo Đang chạy server trên port 8000...
echo.

".venv\Scripts\python.exe" "scripts\phase1_fastapi_server.py"

pause
