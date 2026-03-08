# Setup Script: Add Scalp-Engine to Trade-Alerts for Unified Blueprint
# This script copies Scalp-Engine files into Trade-Alerts repository

Write-Host "=== Unified Blueprint Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if Scalp-Engine directory exists
$scalpEnginePath = "..\Scalp-Engine"
if (-not (Test-Path $scalpEnginePath)) {
    Write-Host "❌ Error: Scalp-Engine directory not found at: $scalpEnginePath" -ForegroundColor Red
    Write-Host "   Please make sure Scalp-Engine is in the parent directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Found Scalp-Engine directory" -ForegroundColor Green

# Check if Scalp-Engine already exists in Trade-Alerts
$targetPath = "Scalp-Engine"
if (Test-Path $targetPath) {
    Write-Host ""
    Write-Host "⚠️  Scalp-Engine directory already exists in Trade-Alerts" -ForegroundColor Yellow
    $response = Read-Host "   Do you want to remove it and copy fresh? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        Remove-Item -Path $targetPath -Recurse -Force
        Write-Host "✅ Removed existing Scalp-Engine directory" -ForegroundColor Green
    } else {
        Write-Host "❌ Cancelled - keeping existing directory" -ForegroundColor Red
        exit 0
    }
}

Write-Host ""
Write-Host "📦 Copying Scalp-Engine files..." -ForegroundColor Cyan

# Copy Scalp-Engine directory
try {
    # Use robocopy for better control
    robocopy $scalpEnginePath $targetPath /E /XD .git __pycache__ node_modules /XF .env *.db *.sqlite market_state.json /NFL /NDL /NJH /NJS
    Write-Host ""
    Write-Host "✅ Scalp-Engine files copied successfully" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "❌ Error copying files: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Review the copied files:" -ForegroundColor White
Write-Host "      - Scalp-Engine/ directory should now exist" -ForegroundColor Gray
Write-Host "   2. Commit the changes:" -ForegroundColor White
Write-Host "      git add Scalp-Engine render.yaml" -ForegroundColor Gray
Write-Host "      git commit -m 'Add Scalp-Engine for unified Blueprint deployment'" -ForegroundColor Gray
Write-Host "      git push" -ForegroundColor Gray
Write-Host "   3. Deploy on Render:" -ForegroundColor White
Write-Host "      - Go to Render Dashboard -> trade-alerts Blueprint" -ForegroundColor Gray
Write-Host "      - Click 'Manual sync' or 'Apply'" -ForegroundColor Gray
Write-Host "      - Render will add scalp-engine and scalp-engine-ui services" -ForegroundColor Gray
Write-Host "   4. Set environment variables for new services:" -ForegroundColor White
Write-Host "      - OANDA_ACCESS_TOKEN" -ForegroundColor Gray
Write-Host "      - OANDA_ACCOUNT_ID" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
