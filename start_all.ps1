# PowerShell script to start OmniRoute, Markus Backend, and Markus Frontend

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Starting Markus AI Ecosystem" -ForegroundColor Cyan
Write-Host "  1. OmniRoute AI Gateway (port 20128)" -ForegroundColor Green
Write-Host "  2. Markus AI Backend    (port 8000)" -ForegroundColor Green
Write-Host "  3. Markus AI Frontend   (port 5173)" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "omniroute serve --no-open"
Start-Sleep -Seconds 3

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\markus'; .\venv\Scripts\python.exe main.py"
Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\markus\apps\frontend'; npm run dev"

Write-Host "All services launched successfully!" -ForegroundColor Green
