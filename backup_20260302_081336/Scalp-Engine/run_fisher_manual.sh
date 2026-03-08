#!/usr/bin/env bash
# Manual Fisher Transform scan – FT opportunities (FISHER_PAIRS)
# Run from repo root or Scalp-Engine. Uses .env in Scalp-Engine if present.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python run_fisher_scan.py
exit $?
