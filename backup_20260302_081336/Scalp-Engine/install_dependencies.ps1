# Install all dependencies for Scalp-Engine
# Run this if you get "ModuleNotFoundError" errors

Write-Host "Installing Scalp-Engine dependencies..." -ForegroundColor Green
Write-Host ""

# Change to Scalp-Engine directory
Set-Location $PSScriptRoot

# Check which Python is being used
Write-Host "Python version:" -ForegroundColor Yellow
python --version
Write-Host "Python path:" -ForegroundColor Yellow
python -c "import sys; print(sys.executable)"
Write-Host ""

# Install from requirements.txt
Write-Host "Installing packages from requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Yellow
python -c "import oandapyV20; print('[OK] oandapyV20')"
python -c "import pandas; print('[OK] pandas')"
python -c "import numpy; print('[OK] numpy')"
python -c "import yaml; print('[OK] pyyaml')"
python -c "import dotenv; print('[OK] python-dotenv')"

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "You can now run: python scalp_engine.py" -ForegroundColor Green

