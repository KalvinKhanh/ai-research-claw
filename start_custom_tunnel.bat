@echo off
chcp 65001 > nul
echo ========================================================
echo   AutoResearchClaw - Tên Miền Tùy Biến (LocalTunnel)
echo   Subdomain: hyperdatalaautoresearchclaw
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/3] Đang khởi động Backend Server (Port 8090)...
start /b "" ".venv\Scripts\python.exe" "scripts\dashboard_server.py"
timeout /t 2 > nul

echo [2/3] Lấy IP công khai làm mật khẩu truy cập lần đầu...
powershell -Command "try { $ip = Invoke-RestMethod -Uri https://loca.lt/mytunnelpassword; Write-Host '👉 Mật khẩu Tunnel (IP của bạn): ' $ip -ForegroundColor Green } catch {}"

echo.
echo [3/3] Đang kích hoạt tên miền: https://hyperdatalaautoresearchclaw.loca.lt
echo.
echo ========================================================
echo   LINK CÔNG KHAI CỦA BẠN:
echo   https://hyperdatalaautoresearchclaw.loca.lt
echo ========================================================
echo.

call npx -y localtunnel --port 8090 --subdomain hyperdatalaautoresearchclaw
pause
