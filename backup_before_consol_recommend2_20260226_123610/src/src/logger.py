"""Logging configuration

ERROR HANDLING POLICY
=====================
Use the following levels consistently across the codebase:

  logger.debug()    - Detailed diagnostic info useful only when investigating a bug.
                      Not shown in production by default.
  logger.info()     - Normal operational events (startup, scheduled runs, successful steps).
  logger.warning()  - Recoverable issues where a fallback was used, or something unexpected
                      happened but the system can continue (e.g. missing optional config,
                      using a default value, token rotation detected).
  logger.error()    - A specific operation failed and requires attention, but the process
                      can continue (e.g. failed to send email, parse error on one opportunity).
  logger.critical() - System-level failures that prevent normal operation.

RAISE exceptions for:
  - Invalid required configuration at startup
  - Programmer errors (wrong argument types, missing required params)

LOG (don't raise) for:
  - Network / external service failures (with fallback or retry logic)
  - Per-item processing failures in a loop (log and continue)
"""

import logging
import os
import threading
from datetime import datetime

_logger_lock = threading.Lock()


def setup_logger(name="trade_alerts", log_level=logging.INFO):
    """Setup and configure logger (thread-safe, idempotent)."""
    logger = logging.getLogger(name)

    # Guard: if already initialised, return immediately without touching handlers
    with _logger_lock:
        if logger.handlers:
            return logger

        logger.setLevel(log_level)

        # Create logs directory if it doesn't exist
        # On Render (production): Use persistent disk /var/data/logs (mounted at startup)
        # Locally: Use relative ./logs directory
        if os.getenv('ENV') == 'production' or os.getenv('RENDER'):
            # Force /var/data/logs on Render
            log_dir = '/var/data/logs'
        else:
            # Local development
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')

        os.makedirs(log_dir, exist_ok=True)

        # File handler
        log_file = os.path.join(log_dir, f'trade_alerts_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
