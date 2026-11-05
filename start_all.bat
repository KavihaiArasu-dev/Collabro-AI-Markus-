@echo off
echo ===================================================
echo   Starting Markus AI Ecosystem
echo   1. Markus AIServer (agy)   (port 3001)
echo   2. Markus Next.js Backend  (port 8010)
echo   3. Markus AI Frontend      (port 5173)
echo ===================================================

start "Markus AIServer" cmd /k "cd /d %~dp0AIServer && node server.js"
ping -n 3 127.0.0.1 >nul

start "Markus Next.js Backend" cmd /k "cd /d %~dp0markus-next && npm run dev"
ping -n 3 127.0.0.1 >nul

start "Markus Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo All services launched!
