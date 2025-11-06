"""Unit tests for OpenTelemetry tracing in OrchestratorService.

This module tests that tracing spans are created for orchestrator query operations.

Date: 2025-11-06
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestOrchestratorTracing:
    """Test suite for tracing in OrchestratorService."""

    @pytest.mark.asyncio
    async def test_query_creates_span(self):
        """Test that query method creates a tracing span."""
        # RED: Will fail because span not created
        from app.services.orchestrator import OrchestratorService

        # Create service with mocked dependencies
        service = OrchestratorService()

        # Mock the query_router_service to avoid real LLM calls
        service.query_router_service = AsyncMock()
        service.query_router_service.route_query.return_value = {
            "response": "Test answer",
            "context": [
                {"text": "Test document", "score": 0.95, "id": "doc-1"}
            ],
            "classification": {"query_type": "retrieval", "needs_rag": True}
        }

        # Mock tracer to capture span creation
        with patch('app.services.orchestrator.trace.get_tracer') as mock_get_tracer:
            mock_tracer = MagicMock()
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)
            mock_get_tracer.return_value = mock_tracer

            # Call query
            result = await service.query(
                query="Test query",
                collection_name="test_collection",
                top_k=5
            )

            # Verify span was created with correct name
            mock_get_tracer.assert_called_once()
            mock_tracer.start_as_current_span.assert_called_once()
            call_args = mock_tracer.start_as_current_span.call_args
            assert call_args[0][0] == "orchestrator.query"

            # Verify span attributes were set
            mock_span.set_attribute.assert_any_call("query.collection", "test_collection")
            mock_span.set_attribute.assert_any_call("query.top_k", 5)
