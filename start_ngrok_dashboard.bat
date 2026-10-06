@echo off
chcp 65001 > nul
echo ========================================================
echo   AutoResearchClaw - Khởi Động Dashboard (Ngrok Tĩnh)
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Đang khởi động Backend Server (Port 8090)...
start /b "" ".venv\Scripts\python.exe" "scripts\dashboard_server.py"

timeout /t 2 > nul

echo [2/2] Đang kết nối ngrok tunnel cố định...
echo.
echo ========================================================
echo   LINK CÔNG KHAI CỐ ĐỊNH CỦA BẠN:
echo   https://vowed-doorway-speculate.ngrok-free.dev
echo ========================================================
echo.

bin\ngrok.exe http 8090 --url https://vowed-doorway-speculate.ngrok-free.dev
pause
