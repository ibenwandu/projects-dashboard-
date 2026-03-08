"""
Run analysis immediately (legacy name).
Uses full workflow including RL enhancement and market state export (Step 9).
Prefer run_immediate_analysis.py or run_full_analysis.py for clarity.
"""

import sys

# Delegate to full workflow so market state is always exported (Step 9)
from run_immediate_analysis import run_immediate_analysis

if __name__ == "__main__":
    success = run_immediate_analysis()
    sys.exit(0 if success else 1)
