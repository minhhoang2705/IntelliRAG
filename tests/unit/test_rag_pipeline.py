"""Unit tests for RAG Pipeline Service.

This module tests the RAGPipelineService which orchestrates
the retrieval-augmented generation flow.


Date: 2025-10-17
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_rag_pipeline_initialization():
    """Test RAG pipeline initializes with required services."""
    from app.services.rag_pipeline import RAGPipelineService
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    from app.services.llm_client import LLMClientService

    embedding_svc = EmbeddingService()
    vectordb_svc = VectorDBService(url="http://localhost:6333")
    llm_client = LLMClientService()

    pipeline = RAGPipelineService(
        embedding_service=embedding_svc,
        vectordb_service=vectordb_svc,
        llm_client=llm_client
    )

    assert pipeline.embedding_service is not None
    assert pipeline.vectordb_service is not None
    assert pipeline.llm_client is not None


@pytest.mark.asyncio
async def test_rag_pipeline_query_with_rag(mocker):
    """Test RAG pipeline executes full query flow."""
    from app.services.rag_pipeline import RAGPipelineService
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    from app.services.llm_client import LLMClientService

    # Create services
    embedding_svc = EmbeddingService()
    vectordb_svc = VectorDBService(url="http://localhost:6333")
    llm_client = LLMClientService()

    pipeline = RAGPipelineService(
        embedding_service=embedding_svc,
        vectordb_service=vectordb_svc,
        llm_client=llm_client
    )

    # Mock embedding service
    mock_embedding = [0.1] * 1024
    mocker.patch.object(embedding_svc, 'embed_single_async',
                        return_value=mock_embedding)

    # Mock vector DB search results
    mock_result1 = MagicMock()
    mock_result1.payload = {"text": "Python is a programming language"}
    mock_result1.score = 0.95
    mock_result1.id = 1

    mock_result2 = MagicMock()
    mock_result2.payload = {"text": "Python was created by Guido van Rossum"}
    mock_result2.score = 0.87
    mock_result2.id = 2

    mock_search = AsyncMock(return_value=[mock_result1, mock_result2])
    mocker.patch.object(vectordb_svc, 'search_vectors', mock_search)

    # Mock LLM generation
    mock_generate = AsyncMock(
        return_value="Python is a high-level programming language created by Guido van Rossum.")
    mocker.patch.object(llm_client, 'generate', mock_generate)

    # Execute query
    result = await pipeline.query_with_rag(
        query="What is Python?",
        collection_name="test_docs",
        top_k=2,
        temperature=0.7
    )

    # Verify result structure
    assert "answer" in result
    assert "sources" in result
    assert result["answer"] == "Python is a high-level programming language created by Guido van Rossum."
    assert len(result["sources"]) == 2
    assert result["sources"][0]["score"] == 0.95
