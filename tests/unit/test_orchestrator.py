"""Unit tests for Orchestrator Service.

This module tests the OrchestratorService which coordinates
all RAG services and provides a unified interface.

Author: IntelliRAG Team
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
    """Test orchestrator executes query via RAG pipeline."""
    from app.services.orchestrator import OrchestratorService

    orchestrator = OrchestratorService()

    # Mock the RAG pipeline query method
    mock_result = {
        "answer": "Python is a programming language",
        "sources": [{"text": "Python is...", "score": 0.95, "id": "1"}]
    }
    mock_query = AsyncMock(return_value=mock_result)
    mocker.patch.object(orchestrator.rag_pipeline, 'query_with_rag', mock_query)

    result = await orchestrator.query(
        query="What is Python?",
        collection_name="test_docs",
        use_rag=True
    )

    assert result["answer"] == "Python is a programming language"
    assert len(result["sources"]) == 1
    mock_query.assert_called_once()
