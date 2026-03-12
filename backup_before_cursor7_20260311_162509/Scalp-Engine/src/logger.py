"""Logging configuration for Scalp-Engine

Provides centralized file logging with rotation (10 MB, 3 backups).
Adapted from Trade-Alerts root logger pattern.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_log_dir() -> str:
    """
    Get the log directory path.

    Returns:
    - On Render: /var/data/logs/
    - On local dev: Scalp-Engine/logs/
    """
    # Check if we're on Render (ENV='production' or RENDER env var set)
    if os.getenv('ENV') == 'production' or os.getenv('RENDER'):
        # Force /var/data/logs on Render (mounted at startup)
        log_dir = '/var/data/logs'
    else:
        # Local development: use Scalp-Engine/logs/
        scalp_engine_dir = Path(__file__).parent.parent
        log_dir = str(scalp_engine_dir / 'logs')

    # Create directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def attach_file_handler(logger_names: list, log_filename: str):
    """
    Add a RotatingFileHandler to named loggers.

    Args:
        logger_names: List of logger names (e.g., ['TradeExecutor', 'PositionManager'])
        log_filename: Base filename without date/extension (e.g., 'scalp_engine')
                     Will be formatted as: {log_filename}_YYYYMMDD.log

    Idempotent - checks for existing FileHandlers before adding.
    """
    from datetime import datetime

    log_dir = get_log_dir()
    print(f"🔍 [LOGGER] attach_file_handler called - log_dir: {log_dir}, filename: {log_filename}, loggers: {logger_names}")

    # Format log filename with today's date
    today = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'{log_filename}_{today}.log')

    # Formatter (same as Trade-Alerts root)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)

        # Idempotent guard: skip if FileHandler already exists for this file
        has_file_handler = any(
            isinstance(h, RotatingFileHandler) and h.baseFilename.endswith(log_file)
            for h in logger.handlers
        )

        if has_file_handler:
            # Already attached, skip
            continue

        # Create and configure RotatingFileHandler (10 MB, 3 backups)
        # Note: RotatingFileHandler creates file on first write, not on instantiation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        logger.addHandler(file_handler)
        
        # Force immediate write to create the file
        try:
            logger.info(f"✅ Log file initialized: {log_file}")
            # Force flush to ensure file is written immediately
            file_handler.flush()
            # Verify file was created
            if os.path.exists(log_file):
                print(f"✅ [LOGGER] Log file created and verified: {log_file}")
            else:
                print(f"⚠️ [LOGGER] Log file handler attached but file not created yet: {log_file}")
        except Exception as e:
            print(f"⚠️ [LOGGER] Failed to initialize log file {log_file}: {e}")
        # Log to console (stdout) so it appears in Render logs
        print(f"✅ [LOGGER] File handler attached for {logger_name} -> {log_file}")
        logger.info(f"✅ File handler attached for {logger_name} -> {log_file}")
