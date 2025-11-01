"""Unit tests for QueryRouterService.

This service wraps the LangGraph query router and provides a high-level API
for routing queries through the classification and conditional RAG flow.
"""

import pytest
from unittest.mock import MagicMock
from app.services.query_router_service import QueryRouterService
from app.services.query_router.classifier import QueryClassifier
from app.services.vectordb import VectorDBService
from app.services.llm_client import LLMClientService


@pytest.mark.asyncio
@pytest.mark.unit
class TestQueryRouterServiceInit:
    """Test QueryRouterService initialization."""

    async def test_init_with_all_services(self):
        """Should initialize with classifier, vectordb, and llm services."""
        # Arrange
        mock_classifier = MagicMock(spec=QueryClassifier)
        mock_vectordb = MagicMock(spec=VectorDBService)
        mock_llm = MagicMock(spec=LLMClientService)

        # Act
        service = QueryRouterService(
            classifier=mock_classifier,
            vectordb=mock_vectordb,
            llm=mock_llm
        )

        # Assert
        assert service.classifier == mock_classifier
        assert service.vectordb == mock_vectordb
        assert service.llm == mock_llm
        assert service.graph is not None


@pytest.mark.asyncio
@pytest.mark.unit
class TestQueryRouterServiceRouteQuery:
    """Test QueryRouterService.route_query() method."""

    async def test_route_rag_query_success(self):
        """Should successfully route RAG query through retrieval."""
        # Arrange
        from unittest.mock import AsyncMock
        from app.services.query_router.classifier import QueryType, QueryClassification

        mock_classifier = AsyncMock()
        mock_vectordb = AsyncMock()
        mock_llm = AsyncMock()

        mock_classifier.classify = AsyncMock(return_value=QueryClassification(
            query_type=QueryType.RAG,
            confidence=0.92,
            reasoning="Query asks about specific document content requiring retrieval"
        ))

        service = QueryRouterService(
            classifier=mock_classifier,
            vectordb=mock_vectordb,
            llm=mock_llm
        )

        query = "What is the revenue in Q4 report?"
        collection_name = "financial_docs"

        # Act
        result = await service.route_query(query, collection_name)

        # Assert
        assert result["query"] == query
        assert result["classification"] is not None
        assert result["classification"].query_type == QueryType.RAG
        # Verify classifier was actually called
        mock_classifier.classify.assert_called_once_with(query)

    async def test_route_query_error_handling(self):
        """Should handle classification errors gracefully."""
        from unittest.mock import AsyncMock

        mock_classifier = AsyncMock()
        mock_vectordb = AsyncMock()
        mock_llm = AsyncMock()

        # Make classifier fail
        mock_classifier.classify = AsyncMock(side_effect=Exception("LLM unavailable"))

        service = QueryRouterService(
            classifier=mock_classifier,
            vectordb=mock_vectordb,
            llm=mock_llm
        )

        # Act
        result = await service.route_query("Test query", "docs")

        # Assert
        assert result["error"] is not None
        assert "Classification failed" in result["error"]
