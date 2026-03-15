import pytest
import json
import logging
from io import StringIO
from emy.brain.logging_config import JSONFormatter, setup_logging


def test_json_formatter_output():
    """Test JSONFormatter produces valid JSON output."""
    # Create logger with JSON formatter
    logger = logging.getLogger('test_logger')
    logger.handlers = []  # Clear any existing handlers

    # Setup string stream handler
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Log a message
    logger.info("Test message")

    # Get output and parse as JSON
    output = stream.getvalue().strip()
    log_data = json.loads(output)

    # Verify JSON structure
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Test message"
    assert "timestamp" in log_data
    assert "logger" in log_data


def test_json_formatter_with_exception():
    """Test JSONFormatter includes exception info."""
    logger = logging.getLogger('test_exception')
    logger.handlers = []

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)

    # Log with exception
    try:
        raise ValueError("Test error")
    except ValueError:
        logger.exception("An error occurred")

    output = stream.getvalue().strip()
    log_data = json.loads(output)

    assert log_data["level"] == "ERROR"
    assert log_data["message"] == "An error occurred"
    assert "exception" in log_data
    assert "ValueError" in log_data["exception"]


def test_setup_logging_creates_logger():
    """Test setup_logging() function creates properly configured logger."""
    logger = setup_logging(log_level=logging.DEBUG)

    assert logger is not None
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) > 0

    # Verify handler has JSONFormatter
    handler = logger.handlers[0]
    assert isinstance(handler.formatter, JSONFormatter)
