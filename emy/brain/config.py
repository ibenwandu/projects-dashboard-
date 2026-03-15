"""Configuration for Emy Brain service.

All configuration is managed via environment variables with sensible defaults.
For deployment, copy .env.example to .env and update values for your environment.
"""

import os
import logging
from pathlib import Path

# ============================================================================
# Service Configuration
# ============================================================================

BRAIN_HOST = os.getenv("BRAIN_HOST", "0.0.0.0")
BRAIN_PORT = int(os.getenv("BRAIN_PORT", "8001"))
ENV = os.getenv("ENV", "development")

# ============================================================================
# Database Configuration
# ============================================================================

BRAIN_DB_PATH = os.getenv("BRAIN_DB_PATH", "emy_brain.db")
DB_PATH = Path(BRAIN_DB_PATH)

# ============================================================================
# Job Queue Configuration
# ============================================================================

QUEUE_BATCH_SIZE = int(os.getenv("QUEUE_BATCH_SIZE", "10"))
QUEUE_POLL_INTERVAL = int(os.getenv("QUEUE_POLL_INTERVAL", "5"))

# ============================================================================
# WebSocket Configuration
# ============================================================================

WS_HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))

# ============================================================================
# Rate Limiting Configuration
# ============================================================================

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)
LOG_FILE = os.getenv("LOG_FILE")

# ============================================================================
# Monitoring Configuration
# ============================================================================

SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", ENV)
SENTRY_ENABLED = bool(SENTRY_DSN)

# ============================================================================
# Security Configuration
# ============================================================================

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ============================================================================
# Agent Configuration
# ============================================================================

AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))

# ============================================================================
# LangGraph Configuration
# ============================================================================

LANGGRAPH_DEBUG = os.getenv("LANGGRAPH_DEBUG", "false").lower() == "true"

# ============================================================================
# Deployment Flags
# ============================================================================

IS_PRODUCTION = ENV.lower() == "production"
IS_DEVELOPMENT = ENV.lower() == "development"
DEBUG = IS_DEVELOPMENT

# ============================================================================
# Derived Configuration
# ============================================================================

# API base URL (for external references)
API_BASE_URL = f"http://{BRAIN_HOST}:{BRAIN_PORT}"
if IS_PRODUCTION:
    # In production, use the external hostname if available
    API_BASE_URL = os.getenv("API_BASE_URL", API_BASE_URL)

# WebSocket URL (for client connections)
WS_URL = f"ws://{BRAIN_HOST}:{BRAIN_PORT}/ws/jobs"
if IS_PRODUCTION:
    # In production, client uses HTTPS/WSS
    WS_URL = os.getenv(
        "WS_URL",
        f"wss://{os.getenv('RENDER_EXTERNAL_HOSTNAME', BRAIN_HOST)}/ws/jobs"
    )
