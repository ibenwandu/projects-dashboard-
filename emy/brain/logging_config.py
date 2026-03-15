"""Structured logging configuration for EMyBrain."""

import logging
import json
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging and monitoring."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    logger_name: str = 'EMyBrain'
) -> logging.Logger:
    """
    Setup structured logging for EMyBrain.

    Args:
        log_level: Logging level (default: INFO)
        log_file: Optional file path for file logging
        logger_name: Root logger name (default: EMyBrain)

    Returns:
        Configured logger instance
    """
    root_logger = logging.getLogger(logger_name)
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers = []

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    return root_logger
