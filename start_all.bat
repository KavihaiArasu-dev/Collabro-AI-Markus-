@echo off
echo ===================================================
echo   Starting Markus AI Ecosystem
echo   1. OmniRoute AI Gateway (port 20128)
echo   2. Markus AI Backend    (port 8000)
echo   3. Markus AI Frontend   (port 5173)
echo ===================================================

start "OmniRoute Gateway" cmd /k "omniroute serve --no-open"
timeout /t 3 /nobreak >nul

start "Markus Backend" cmd /k "cd /d %~dp0markus && .\venv\Scripts\python.exe main.py"
timeout /t 2 /nobreak >nul

start "Markus Frontend" cmd /k "cd /d %~dp0markus\apps\frontend && npm run dev"

echo All services launched!
