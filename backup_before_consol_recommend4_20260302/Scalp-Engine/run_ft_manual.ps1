# Manual FT-DMI-EMA scan – confirm FT list and API path
# Run from repo root or Scalp-Engine. Uses .env in Scalp-Engine if present.

$ScalpEngine = $PSScriptRoot
if (-not (Test-Path (Join-Path $ScalpEngine "run_ft_dmi_ema_scan.py"))) {
    $ScalpEngine = Join-Path $PSScriptRoot "Scalp-Engine"
}
Set-Location $ScalpEngine
python run_ft_dmi_ema_scan.py
exit $LASTEXITCODE
