# PowerShell script to run Scalp-Engine with proper output handling
# This ensures you can see what's happening and stop it easily

Write-Host "Starting Scalp-Engine..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Change to Scalp-Engine directory
Set-Location $PSScriptRoot

# Run the script (this will show output in real-time)
python scalp_engine.py

