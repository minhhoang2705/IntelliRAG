"""Structured logging configuration for IntelliRAG."""

import logging
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict
from contextlib import contextmanager


class StructuredJSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Console handler with JSON formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance with structured logging support.

    Args:
        name: Name for the logger (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


@contextmanager
def log_operation(operation_name: str, logger: logging.Logger, **context):
    """Context manager for logging operations with timing.

    Args:
        operation_name: Name of the operation being logged
        logger: Logger instance to use
        **context: Additional context to include in the log

    Yields:
        None

    Example:
        with log_operation("process_file", logger, file_path="/path/to/file"):
            # ... processing code ...
            pass
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        logger.info(
            f"{operation_name} completed",
            extra={'extra_data': {**context,
                                  'duration_seconds': round(duration, 3)}}
        )
