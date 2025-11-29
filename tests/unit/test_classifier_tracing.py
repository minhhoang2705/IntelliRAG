"""Unit tests for OpenTelemetry tracing in QueryClassifier.

This module tests that tracing spans are created for query classification.

Date: 2025-11-06
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestClassifierTracing:
    """Test suite for tracing in QueryClassifier."""

    @pytest.mark.asyncio
    async def test_classify_creates_span(self):
        """Test that classify method creates a tracing span."""
        # RED: Will fail because span not created
        from app.services.query_router.classifier import QueryClassifier

        # Mock the LLM client
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = '{"query_type": "rag", "confidence": 0.95, "reasoning": "test"}'

        # Create classifier with mocked LLM
        classifier = QueryClassifier(llm_client=mock_llm)

        # Mock tracer to capture span creation
        with patch('app.services.query_router.classifier.trace.get_tracer') as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)
            mock_get_tracer.return_value = mock_tracer

            # Call classify
            result = await classifier.classify("What is RAG?")

            # Verify span was created with correct name
            mock_get_tracer.assert_called_once()
            mock_tracer.start_as_current_span.assert_called_once()
            call_args = mock_tracer.start_as_current_span.call_args
            assert call_args[0][0] == "query.classify"
