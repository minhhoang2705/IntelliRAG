"""Unit tests for FastAPI query endpoint."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_query_endpoint_returns_classification():
    """Test query endpoint includes classification in response."""
    from app.services.query_router.classifier import QueryType, QueryClassification
    from fastapi.testclient import TestClient
    
    # Mock the orchestrator.query to return classification
    mock_result = {
        "answer": "Python is a programming language",
        "sources": [],
        "classification": QueryClassification(
            query_type=QueryType.DIRECT,
            confidence=0.95,
            reasoning="General knowledge question"
        )
    }
    
    with patch('app.main.orchestrator') as mock_orchestrator:
        mock_orchestrator.query = AsyncMock(return_value=mock_result)
        
        from app.main import app
        client = TestClient(app)
        
        # Make query request
        response = client.post("/api/v1/query", json={
            "query": "What is Python?"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify classification is included
        assert "classification" in data
        assert data["classification"] is not None
        assert data["classification"]["query_type"] == "direct"
        assert data["classification"]["confidence"] == 0.95


@pytest.mark.asyncio
async def test_query_endpoint_calls_orchestrator_without_use_rag():
    """Test that query endpoint doesn't pass use_rag to orchestrator."""
    from unittest.mock import AsyncMock, patch
    from fastapi.testclient import TestClient
    from app.services.query_router.classifier import QueryType, QueryClassification
    
    mock_result = {
        "answer": "Test answer",
        "sources": [],
        "classification": QueryClassification(
            query_type=QueryType.DIRECT,
            confidence=0.9,
            reasoning="Test"
        )
    }
    
    with patch('app.main.orchestrator') as mock_orchestrator:
        mock_orchestrator.query = AsyncMock(return_value=mock_result)
        
        from app.main import app
        client = TestClient(app)
        
        # Make request
        response = client.post("/api/v1/query", json={
            "query": "Test query",
            "use_rag": True  # This should be ignored
        })
        
        assert response.status_code == 200
        
        # Verify orchestrator.query was called WITHOUT use_rag parameter
        mock_orchestrator.query.assert_called_once()
        call_kwargs = mock_orchestrator.query.call_args.kwargs
        assert "use_rag" not in call_kwargs
        assert call_kwargs["query"] == "Test query"
        assert call_kwargs["collection_name"] == "default"
