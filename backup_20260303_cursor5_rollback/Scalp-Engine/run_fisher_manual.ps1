# Manual Fisher Transform scan – FT opportunities (FISHER_PAIRS)
# Run from repo root or Scalp-Engine. Uses .env in Scalp-Engine if present.

$ScalpEngine = $PSScriptRoot
if (-not (Test-Path (Join-Path $ScalpEngine "run_fisher_scan.py"))) {
    $ScalpEngine = Join-Path $PSScriptRoot "Scalp-Engine"
}
Set-Location $ScalpEngine
python run_fisher_scan.py
exit $LASTEXITCODE
