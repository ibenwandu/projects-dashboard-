#!/usr/bin/env python3
"""
Emy API entrypoint script.

Runs uvicorn server with proper module path setup.
"""

import sys
import os
from pathlib import Path

# Dockerfile copies emy/ contents to /app/emy/
# So Python path should include /app to find the emy package
app_dir = Path("/app").resolve()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# For local development, also support running from within emy/ directory
local_dir = Path(".").resolve()
if str(local_dir) not in sys.path:
    sys.path.insert(0, str(local_dir))

# Load environment variables from .env file (local only)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except Exception:
    pass  # .env loading is optional

# Now run uvicorn
import uvicorn

if __name__ == "__main__":
    # Import after path is set up
    from emy.gateway.api import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=os.getenv("EMY_LOG_LEVEL", "info").lower(),
    )
