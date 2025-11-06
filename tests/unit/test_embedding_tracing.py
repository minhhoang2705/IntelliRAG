"""Unit tests for OpenTelemetry tracing in EmbeddingService.

This module tests that tracing spans are created for embedding operations.

Date: 2025-11-06
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestEmbeddingTracing:
    """Test suite for tracing in EmbeddingService."""

    @pytest.mark.asyncio
    async def test_embed_batch_async_creates_span(self):
        """Test that embed_batch_async method creates a tracing span."""
        # RED: Will fail because span not created
        from app.services.embedding import EmbeddingService

        # Create service in remote mode (simpler for testing)
        service = EmbeddingService(use_remote=True, remote_url="http://localhost:8001")

        # Mock the _embed_remote method
        service._embed_remote = MagicMock(return_value=[[0.1, 0.2], [0.3, 0.4]])

        # Mock tracer to capture span creation
        with patch('app.services.embedding.trace.get_tracer') as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)
            mock_get_tracer.return_value = mock_tracer

            # Call embed_batch_async
            texts = ["Hello world", "Test text"]
            result = await service.embed_batch_async(texts)

            # Verify span was created with correct name
            mock_get_tracer.assert_called_once()
            mock_tracer.start_as_current_span.assert_called_once()
            call_args = mock_tracer.start_as_current_span.call_args
            assert call_args[0][0] == "embedding.batch"

            # Verify span attributes were set
            mock_span.set_attribute.assert_any_call("embedding.batch_size", 2)
            mock_span.set_attribute.assert_any_call("embedding.mode", "remote")
