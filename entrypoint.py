#!/usr/bin/env python3
"""
Emy API entrypoint script.

Runs uvicorn server with proper module path setup.
"""

import sys
import os

# Add /app to Python path FIRST, before any imports
sys.path.insert(0, '/app')

# Debug: Show what's in /app before importing
print(f"DEBUG: /app contents: {os.listdir('/app') if os.path.exists('/app') else 'N/A'}")
if os.path.exists('/app/emy'):
    print(f"DEBUG: /app/emy contents: {os.listdir('/app/emy')}")

# Now import uvicorn
import uvicorn

if __name__ == "__main__":
    # Import the app after path is set
    try:
        from emy.gateway.api import app
        print("DEBUG: Successfully imported emy.gateway.api")
    except ImportError as e:
        print(f"ERROR: Could not import emy.gateway.api: {e}")
        print(f"DEBUG: sys.path = {sys.path}")
        raise

    # Run uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=os.getenv("EMY_LOG_LEVEL", "info").lower(),
    )
