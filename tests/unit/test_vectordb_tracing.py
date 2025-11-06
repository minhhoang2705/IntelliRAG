"""Unit tests for OpenTelemetry tracing in VectorDBService.

This module tests that tracing spans are created for vector search operations.

Date: 2025-11-06
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestVectorDBTracing:
    """Test suite for tracing in VectorDBService."""

    @pytest.mark.asyncio
    async def test_search_vectors_creates_span(self):
        """Test that search_vectors method creates a tracing span."""
        # RED: Will fail because span not created
        from app.services.vectordb import VectorDBService

        # Mock Qdrant client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.points = [MagicMock(), MagicMock(), MagicMock()]  # 3 results
        mock_client.query_points.return_value = mock_response

        # Create service with mocked client
        service = VectorDBService(url="http://localhost:6333")
        service.client = mock_client

        # Mock tracer to capture span creation
        with patch('app.services.vectordb.trace.get_tracer') as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)
            mock_get_tracer.return_value = mock_tracer

            # Call search_vectors
            query_vector = [0.1, 0.2, 0.3]
            result = await service.search_vectors(
                collection_name="test_collection",
                query_vector=query_vector,
                limit=5
            )

            # Verify span was created with correct name
            mock_get_tracer.assert_called_once()
            mock_tracer.start_as_current_span.assert_called_once()
            call_args = mock_tracer.start_as_current_span.call_args
            assert call_args[0][0] == "vectordb.search"

            # Verify span attributes were set
            mock_span.set_attribute.assert_any_call("db.collection", "test_collection")
            mock_span.set_attribute.assert_any_call("db.limit", 5)
            mock_span.set_attribute.assert_any_call("db.results_count", 3)
