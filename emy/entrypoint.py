#!/usr/bin/env python3
"""
Emy API entrypoint script.

Runs uvicorn server with proper module path setup.
"""

import sys
import os
from pathlib import Path

# DIAGNOSTIC OUTPUT
print("\n" + "="*60)
print("ENTRYPOINT DIAGNOSTICS")
print("="*60)
print(f"Current directory: {os.getcwd()}")
print(f"\n/app exists: {Path('/app').exists()}")
print(f"/app/emy exists: {Path('/app/emy').exists()}")
if Path('/app').exists():
    print(f"\n/app contents: {list(Path('/app').iterdir())[:10]}")  # First 10 items
if Path('/app/emy').exists():
    print(f"/app/emy contents: {list(Path('/app/emy').iterdir())[:10]}")
print(f"\nPython sys.path:")
for p in sys.path:
    print(f"  {p}")
print("="*60 + "\n")

# Ensure /app is in the Python path
app_dir = Path("/app").resolve()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# Now run uvicorn
import uvicorn

if __name__ == "__main__":
    # Build context is repository root, so full emy/ tree is copied to /app/
    # Modules are at /app/emy/MODULE_NAME
    from emy.gateway.api import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=os.getenv("EMY_LOG_LEVEL", "info").lower(),
    )
