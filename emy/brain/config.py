"""Emy Brain configuration."""
import os
from pathlib import Path

# Service settings
BRAIN_PORT = int(os.getenv("BRAIN_PORT", "8001"))
BRAIN_HOST = os.getenv("BRAIN_HOST", "0.0.0.0")
ENV = os.getenv("ENV", "development")

# Database
DB_PATH = Path(os.getenv("DB_PATH", "emy_brain.db"))

# Job queue
QUEUE_BATCH_SIZE = int(os.getenv("QUEUE_BATCH_SIZE", "10"))
QUEUE_POLL_INTERVAL = int(os.getenv("QUEUE_POLL_INTERVAL", "5"))

# Agent timeouts (seconds)
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))

# LangGraph
LANGGRAPH_DEBUG = os.getenv("LANGGRAPH_DEBUG", "false").lower() == "true"
