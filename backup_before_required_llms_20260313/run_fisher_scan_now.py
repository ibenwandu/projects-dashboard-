#!/usr/bin/env python3
"""
Run Fisher Transform immediate scan from repo root.
Calls Scalp-Engine/run_fisher_scan.py (reversal strategy, publishes to market-state-api or disk).

Usage (from Trade-Alerts repo root):
  python run_fisher_scan_now.py

  On Render Web Shell (shell starts at repo root):
  python run_fisher_scan_now.py
"""
import os
import sys
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_SCALP_ENGINE = _REPO_ROOT / "Scalp-Engine"
_RUN_FISHER = _SCALP_ENGINE / "run_fisher_scan.py"


def main():
    if not _RUN_FISHER.exists():
        print("Scalp-Engine/run_fisher_scan.py not found. Run from Trade-Alerts repo root.", file=sys.stderr)
        sys.exit(1)
    result = subprocess.run(
        [sys.executable, "run_fisher_scan.py"],
        cwd=str(_SCALP_ENGINE),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
