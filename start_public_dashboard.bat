@echo off
chcp 65001 > nul
echo ========================================================
echo   AutoResearchClaw - Khởi Động Public Server (Cloudflare)
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Đang khởi động Backend Server (Port 8090)...
start /b "" ".venv\Scripts\python.exe" "scripts\dashboard_server.py"

timeout /t 2 > nul

echo [2/2] Đang kích hoạt Cloudflare Tunnel ra Internet...
echo.
echo ========================================================
echo   LINK CÔNG KHAI CỦA BẠN SẼ HIỆN RA Ở BÊN DƯỚI:
echo   (Tìm dòng có dạng https://xxxx.trycloudflare.com)
echo   Chia sẻ link này để người khác xem data và bấm chạy Phase 1!
echo ========================================================
echo.

"bin\cloudflared.exe" tunnel --url http://localhost:8090

pause
