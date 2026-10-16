@echo off
chcp 65001 > nul
title PaperWriter - Port 8002
cd /d "%~dp0"

echo ========================================================
echo   PaperWriter Service (Port 8002)
echo ========================================================
echo Swagger: http://localhost:8002/docs
echo.

".venv\Scripts\python.exe" -m uvicorn paperwriter.app:app --host 0.0.0.0 --port 8002

pause
