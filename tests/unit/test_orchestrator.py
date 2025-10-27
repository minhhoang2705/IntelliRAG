"""Unit tests for Orchestrator Service.

This module tests the OrchestratorService which coordinates
all RAG services and provides a unified interface.


Date: 2025-10-17
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test orchestrator initializes all required services."""
    from app.services.orchestrator import OrchestratorService

    orchestrator = OrchestratorService(
        vectordb_url="http://localhost:6333",
        llm_base_url="http://localhost:8000/v1",
        llm_model="Qwen/Qwen2.5-7B-Instruct"
    )

    assert orchestrator.embedding_service is not None
    assert orchestrator.vectordb_service is not None
    assert orchestrator.llm_client is not None
    assert orchestrator.rag_pipeline is not None


@pytest.mark.asyncio
async def test_orchestrator_query(mocker):
    """Test orchestrator executes query via QueryRouter."""
    from app.services.orchestrator import OrchestratorService
    from app.services.query_router.classifier import QueryType, QueryClassification

    orchestrator = OrchestratorService()

    # Mock the query router service
    mock_result = {
        "query": "What is Python?",
        "classification": QueryClassification(
            query_type=QueryType.DIRECT,
            confidence=0.95,
            reasoning="General knowledge"
        ),
        "response": "Python is a programming language",
        "context": None,
        "error": None
    }
    mock_route = AsyncMock(return_value=mock_result)
    mocker.patch.object(orchestrator.query_router_service,
                        'route_query', mock_route)

    result = await orchestrator.query(
        query="What is Python?",
        collection_name="test_docs"
    )

    assert result["answer"] == "Python is a programming language"
    assert "classification" in result
    mock_route.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_has_query_router():
    """Test orchestrator initializes QueryRouterService."""
    from app.services.orchestrator import OrchestratorService

    orchestrator = OrchestratorService()

    # Assert query router service exists
    assert orchestrator.query_router_service is not None


@pytest.mark.asyncio
async def test_orchestrator_query_router_is_correct_type():
    """Test orchestrator initializes correct QueryRouterService type."""
    from app.services.orchestrator import OrchestratorService
    from app.services.query_router_service import QueryRouterService

    orchestrator = OrchestratorService()

    # Assert it's the correct type
    assert isinstance(orchestrator.query_router_service, QueryRouterService)


@pytest.mark.asyncio
async def test_orchestrator_query_uses_router(mocker):
    """Test orchestrator query() uses QueryRouterService."""
    from app.services.orchestrator import OrchestratorService
    from app.services.query_router.classifier import QueryType, QueryClassification

    orchestrator = OrchestratorService()

    # Mock the query router service
    mock_result = {
        "query": "What is Python?",
        "classification": QueryClassification(
            query_type=QueryType.DIRECT,
            confidence=0.95,
            reasoning="General knowledge question"
        ),
        "response": "Python is a programming language",
        "context": None,
        "error": None
    }
    mock_route_query = AsyncMock(return_value=mock_result)
    mocker.patch.object(orchestrator.query_router_service,
                        'route_query', mock_route_query)

    # Execute query
    result = await orchestrator.query(
        query="What is Python?",
        collection_name="docs"
    )

    # Verify query router was called
    mock_route_query.assert_called_once_with(
        query="What is Python?",
        collection_name="docs"
    )

    # Verify result includes classification
    assert "classification" in result
    assert result["classification"].query_type == QueryType.DIRECT
