#!/usr/bin/env bash
# Manual FT-DMI-EMA scan – confirm FT list and API path
# Run from repo root or Scalp-Engine. Uses .env in Scalp-Engine if present.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python run_ft_dmi_ema_scan.py
exit $?
