# PowerShell script to start OmniRoute, Markus Next.js Backend, and Markus Frontend

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Starting Markus AI Ecosystem" -ForegroundColor Cyan
Write-Host "  1. OmniRoute AI Gateway    (port 20128)" -ForegroundColor Green
Write-Host "  2. Markus Next.js Backend  (port 8010)" -ForegroundColor Green
Write-Host "  3. Markus AI Frontend      (port 5173)" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "omniroute serve --no-open"
Start-Sleep -Seconds 3

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\markus-next'; npm run dev"
Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\frontend'; npm run dev"

Write-Host "All services launched successfully!" -ForegroundColor Green
