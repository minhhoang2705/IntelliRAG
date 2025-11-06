"""Unit tests for OpenTelemetry tracing in RAGPipelineService.

This module tests that tracing spans are created for RAG query operations.

Date: 2025-11-06
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestRAGPipelineTracing:
    """Test suite for tracing in RAGPipelineService."""

    @pytest.mark.asyncio
    async def test_query_with_rag_creates_span(self):
        """Test that query_with_rag method creates a tracing span."""
        # RED: Will fail because span not created
        from app.services.rag_pipeline import RAGPipelineService

        # Mock services
        mock_embedding = AsyncMock()
        mock_embedding.embed_single_async.return_value = [0.1, 0.2, 0.3]

        mock_vectordb = AsyncMock()
        mock_result = MagicMock()
        mock_result.payload = {"text": "Test document"}
        mock_result.score = 0.95
        mock_result.id = "doc-1"
        mock_vectordb.search_vectors.return_value = [mock_result]

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Test answer"

        # Create service
        service = RAGPipelineService(
            embedding_service=mock_embedding,
            vectordb_service=mock_vectordb,
            llm_client=mock_llm
        )

        # Mock tracer to capture span creation
        with patch('app.services.rag_pipeline.trace.get_tracer') as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)
            mock_get_tracer.return_value = mock_tracer

            # Call query_with_rag
            result = await service.query_with_rag(
                query="Test query",
                collection_name="test_collection",
                top_k=5
            )

            # Verify span was created with correct name
            mock_get_tracer.assert_called_once()
            mock_tracer.start_as_current_span.assert_called_once()
            call_args = mock_tracer.start_as_current_span.call_args
            assert call_args[0][0] == "rag.query"

            # Verify span attributes were set
            mock_span.set_attribute.assert_any_call("rag.collection", "test_collection")
            mock_span.set_attribute.assert_any_call("rag.top_k", 5)
            mock_span.set_attribute.assert_any_call("rag.sources_count", 1)
