"""Unit tests for structured logging functionality."""

import json
import logging
from io import StringIO


def test_structured_json_formatter_formats_as_json():
    """Test that StructuredJSONFormatter outputs valid JSON."""
    from app.core.logging import StructuredJSONFormatter

    # Create a log record
    logger = logging.getLogger("test")
    formatter = StructuredJSONFormatter()

    # Create handler with string buffer
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Log a message
    logger.info("Test message")

    # Get output and parse as JSON
    output = stream.getvalue()
    log_data = json.loads(output.strip())

    # Verify JSON structure
    assert "timestamp" in log_data
    assert "level" in log_data
    assert "message" in log_data
    assert log_data["message"] == "Test message"
    assert log_data["level"] == "INFO"


def test_app_uses_structured_logging():
    """Test that the FastAPI app is configured with structured logging."""
    from app.main import logger
    from app.core.logging import StructuredJSONFormatter

    # Verify logger is configured
    assert logger is not None
    assert logger.name == "app.main"

    # Check that root logger has handlers with JSON formatter
    root_logger = logging.getLogger()
    has_json_formatter = any(
        isinstance(handler.formatter, StructuredJSONFormatter)
        for handler in root_logger.handlers
    )
    assert has_json_formatter, "Root logger should have StructuredJSONFormatter"
