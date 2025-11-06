"""Unit tests for OpenTelemetry tracing in LLMClientService.

This module tests that tracing spans are created for LLM generation operations.

Date: 2025-11-06
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestLLMClientTracing:
    """Test suite for tracing in LLMClientService."""

    @pytest.mark.asyncio
    async def test_generate_creates_span(self):
        """Test that generate method creates a tracing span."""
        # RED: Will fail because span not created
        from app.services.llm_client import LLMClientService

        # Create service with mocked client
        service = LLMClientService(base_url="http://localhost:8000/v1", model="test-model")

        # Mock the OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Mock tracer to capture span creation
        with patch('app.services.llm_client.trace.get_tracer') as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)
            mock_get_tracer.return_value = mock_tracer

            # Call generate
            result = await service.generate(
                prompt="Test prompt",
                temperature=0.7,
                max_tokens=100
            )

            # Verify span was created with correct name
            mock_get_tracer.assert_called_once()
            mock_tracer.start_as_current_span.assert_called_once()
            call_args = mock_tracer.start_as_current_span.call_args
            assert call_args[0][0] == "llm.generate"

            # Verify span attributes were set
            mock_span.set_attribute.assert_any_call("llm.model", "test-model")
            mock_span.set_attribute.assert_any_call("llm.temperature", 0.7)
            mock_span.set_attribute.assert_any_call("llm.max_tokens", 100)
