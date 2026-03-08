#!/usr/bin/env python3
"""
Clear execution history so the engine can retry trades (reset run counts).
Run this on the engine host (e.g. Render shell) when you want to allow
previously max_runs-blocked opportunities to be traded again.

Usage (on server):
  python Scalp-Engine/scripts/clear_execution_history.py
  # or: python -c "open('/var/data/execution_history.json','w').write('{}')"
"""
import os

EXECUTION_HISTORY_FILE = "/var/data/execution_history.json"

def main():
    try:
        with open(EXECUTION_HISTORY_FILE, "w") as f:
            f.write("{}")
        print("Execution history cleared. Engine can retry trades.")
    except FileNotFoundError:
        print("No execution history file found (already empty or first run).")
    except PermissionError:
        print("Permission denied. Run on the engine host with write access to /var/data.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
