# PowerShell script to run Scalp-Engine UI
# This starts the Streamlit dashboard

Write-Host "Starting Scalp-Engine UI..." -ForegroundColor Green
Write-Host "The dashboard will open in your browser automatically" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Change to Scalp-Engine directory
Set-Location $PSScriptRoot

# Check if streamlit is installed
$streamlitCheck = python -c "import streamlit" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Streamlit not found. Installing..." -ForegroundColor Yellow
    pip install streamlit
}

# Run Streamlit UI
streamlit run scalp_ui.py
