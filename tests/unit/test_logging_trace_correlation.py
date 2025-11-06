"""Unit tests for trace correlation in structured logging.

This module tests that logs include OpenTelemetry trace context
for correlation with distributed traces.

Date: 2025-11-06
"""

import pytest
import json
import logging
from unittest.mock import patch, MagicMock
from io import StringIO


class TestLoggingTraceCorrelation:
    """Test suite for trace correlation in logs."""

    def test_json_formatter_includes_trace_context(self):
        """Test that StructuredJSONFormatter includes trace_id and span_id."""
        # RED: Will fail because trace context not in logs
        from app.core.logging import StructuredJSONFormatter
        from opentelemetry import trace

        # Create formatter and logger
        formatter = StructuredJSONFormatter()
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        try:
            # Mock a tracer with active span
            mock_span_context = MagicMock()
            mock_span_context.trace_id = 12345678901234567890123456789012
            mock_span_context.span_id = 1234567890123456
            mock_span_context.is_valid = True

            mock_span = MagicMock()
            mock_span.get_span_context.return_value = mock_span_context

            with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
                # Log a message
                logger.info("Test message with trace context")

                # Parse logged JSON
                log_output = stream.getvalue()
                log_data = json.loads(log_output.strip())

                # Verify trace context fields are present
                assert 'trace_id' in log_data, "Log should include trace_id"
                assert 'span_id' in log_data, "Log should include span_id"

                # Verify trace IDs are formatted correctly (hex strings)
                assert isinstance(log_data['trace_id'], str), "trace_id should be string"
                assert isinstance(log_data['span_id'], str), "span_id should be string"
                assert len(log_data['trace_id']) == 32, "trace_id should be 32-char hex"
                assert len(log_data['span_id']) == 16, "span_id should be 16-char hex"

        finally:
            logger.removeHandler(handler)
