# PowerShell script to safely create monorepo structure
# This script COPIES projects (doesn't move them) to preserve originals

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Monorepo Creation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get base directory
$baseDir = "C:\Users\user\projects\personal"
$monorepoName = "trading-systems-monorepo"
$monorepoPath = Join-Path $baseDir $monorepoName

# Check if monorepo already exists
if (Test-Path $monorepoPath) {
    Write-Host "Monorepo directory already exists, continuing..." -ForegroundColor Yellow
    Write-Host "  (Existing files will be preserved, new files will be added)" -ForegroundColor Gray
} else {
    # Create monorepo directory
    Write-Host "Creating monorepo directory..." -ForegroundColor Green
    New-Item -ItemType Directory -Path $monorepoPath -Force | Out-Null
}

# Check source directories exist
$firstMonitorSrc = Join-Path $baseDir "first-monitor"
$fxEngineSrc = Join-Path $baseDir "Fx-engine"

if (-not (Test-Path $firstMonitorSrc)) {
    Write-Host "ERROR: first-monitor not found at $firstMonitorSrc" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $fxEngineSrc)) {
    Write-Host "ERROR: Fx-engine not found at $fxEngineSrc" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Source directories found:" -ForegroundColor Green
Write-Host "  - first-monitor: $firstMonitorSrc" -ForegroundColor Gray
Write-Host "  - Fx-engine: $fxEngineSrc" -ForegroundColor Gray
Write-Host ""

# Copy first-monitor
Write-Host "Copying first-monitor..." -ForegroundColor Yellow
$firstMonitorDest = Join-Path $monorepoPath "first-monitor"
if (Test-Path $firstMonitorDest) {
    Write-Host "  first-monitor already exists in monorepo, skipping..." -ForegroundColor Gray
} else {
    Copy-Item -Path $firstMonitorSrc -Destination $firstMonitorDest -Recurse -Force
    Write-Host "  ✅ Copied first-monitor" -ForegroundColor Green
}

# Copy Fx-engine
Write-Host "Copying Fx-engine..." -ForegroundColor Yellow
$fxEngineDest = Join-Path $monorepoPath "Fx-engine"
if (Test-Path $fxEngineDest) {
    Write-Host "  Fx-engine already exists in monorepo, skipping..." -ForegroundColor Gray
} else {
    Copy-Item -Path $fxEngineSrc -Destination $fxEngineDest -Recurse -Force
    Write-Host "  ✅ Copied Fx-engine" -ForegroundColor Green
}

# Copy render.yaml
Write-Host ""
Write-Host "Setting up render.yaml..." -ForegroundColor Yellow
$renderYamlSrc = Join-Path $baseDir "trading-systems-monorepo-render.yaml"
$renderYamlDest = Join-Path $monorepoPath "render.yaml"
if (Test-Path $renderYamlSrc) {
    Copy-Item -Path $renderYamlSrc -Destination $renderYamlDest -Force
    Write-Host "  ✅ Created render.yaml" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  render.yaml template not found, you'll need to create it manually" -ForegroundColor Yellow
}

# Create .gitignore
Write-Host ""
Write-Host "Creating .gitignore..." -ForegroundColor Yellow
$gitignorePath = Join-Path $monorepoPath ".gitignore"
$gitignoreContent = @"
# Python
__pycache__/
*.py[cod]
*.so
.Python
env/
venv/
.venv

# Environment
.env
.env.local

# Databases
*.db
*.sqlite
*.sqlite3

# Data
data/
*.csv
*.json

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project-specific
first-monitor/data/
Fx-engine/data/
"@
Set-Content -Path $gitignorePath -Value $gitignoreContent
Write-Host "  ✅ Created .gitignore" -ForegroundColor Green

# Create README
Write-Host ""
Write-Host "Creating README.md..." -ForegroundColor Yellow
$readmePath = Join-Path $monorepoPath "README.md"
$readmeContent = @"
# Trading Systems Monorepo

This repository contains both first-monitor and Fx-engine projects in a monorepo structure for integrated deployment on Render.

## Structure

\`\`\`
trading-systems-monorepo/
├── first-monitor/      # First Principles Monitor
├── Fx-engine/          # FX Decision Engine
└── render.yaml         # Render deployment configuration
\`\`\`

## Local Development

Both projects work independently:

\`\`\`bash
# Test first-monitor
cd first-monitor
python test_integration.py

# Test Fx-engine
cd ../Fx-engine
python -c "from core.production_engine import ProductionEngine; print('OK')"
\`\`\`

## Integration

first-monitor automatically detects Fx-engine when both are in the same repository, enabling:
- Technical analysis integration
- ML tracker integration
- Full integrated mode

## Deployment

Deploy using Render Blueprints - the \`render.yaml\` file will create all services automatically.

See MONOREPO_MIGRATION_GUIDE.md for detailed setup instructions.
"@
Set-Content -Path $readmePath -Value $readmeContent
Write-Host "  ✅ Created README.md" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Monorepo Created Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Location: $monorepoPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Test integration: cd $monorepoPath\first-monitor && python test_integration.py" -ForegroundColor White
Write-Host "2. Initialize git: cd $monorepoPath && git init" -ForegroundColor White
Write-Host "3. Create GitHub repository and push" -ForegroundColor White
Write-Host "4. Deploy to Render using Blueprints" -ForegroundColor White
Write-Host ""
Write-Host "Original projects are unchanged and still working!" -ForegroundColor Green

