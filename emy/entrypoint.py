#!/usr/bin/env python3
"""
Emy API entrypoint script.

Runs uvicorn server with proper module path setup.
"""

import sys
import os
from pathlib import Path

# Ensure /app is in the Python path
app_dir = Path("/app").resolve()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# Now run uvicorn
import uvicorn

if __name__ == "__main__":
    # Build context is emy/ directory, COPY . ./emy/ creates /app/emy/
    # So modules are at /app/emy/MODULE_NAME
    from emy.gateway.api import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=os.getenv("EMY_LOG_LEVEL", "info").lower(),
    )
