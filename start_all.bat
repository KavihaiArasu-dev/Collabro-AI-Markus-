@echo off
echo ===================================================
echo   Starting Markus AI Ecosystem
echo   1. OmniRoute AI Gateway    (port 20128)
echo   2. Markus Next.js Backend  (port 8010)
echo   3. Markus AI Frontend      (port 5173)
echo ===================================================

start "OmniRoute Gateway" cmd /k "omniroute serve --no-open"
timeout /t 3 /nobreak >nul

start "Markus Next.js Backend" cmd /k "cd /d %~dp0markus-next && npm run dev"
timeout /t 2 /nobreak >nul

start "Markus Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo All services launched!
