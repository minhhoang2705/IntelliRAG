"""Integration tests for FastAPI endpoints with real services.

This module tests the FastAPI application with real Qdrant, vLLM,
and SentenceTransformers without mocking.

Author: IntelliRAG Team
Date: 2025-10-18
"""

import pytest
from fastapi.testclient import TestClient
import uuid


@pytest.mark.integration
def test_health_endpoint():
    """Test health check endpoint.

    Integration Test: Verifies health endpoint returns 200
    Prerequisites: None
    Expected: Returns healthy status
    """
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "IntelliRAG"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_startup_initialization(check_vllm):
    """Test FastAPI app initializes services on startup.

    Integration Test: Verifies orchestrator initializes
    Prerequisites: Qdrant and vLLM running
    Expected: Services initialize without errors
    """
    from app import main  # Import module, not variables
    from fastapi.testclient import TestClient

    # Trigger startup event via lifespan context
    with TestClient(main.app):
        # Orchestrator should be initialized (access via module namespace)
        assert main.orchestrator is not None
        assert main.orchestrator.embedding_service is not None
        assert main.orchestrator.vectordb_service is not None
        assert main.orchestrator.llm_client is not None
        assert main.orchestrator.rag_pipeline is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_without_rag(check_vllm):
    """Test query endpoint with direct LLM mode (no RAG).

    Integration Test: Verifies direct LLM queries work
    Prerequisites: vLLM running
    Expected: Returns answer without sources
    """
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    request_data = {
        "query": "What is 2+2? Answer in one word.",
        "use_rag": False,
        "temperature": 0.0,
        "max_tokens": 10
    }

    response = client.post("/api/v1/query", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "sources" in data
    assert "used_rag" in data
    assert "query" in data

    assert data["used_rag"] is False
    assert len(data["sources"]) == 0
    assert len(data["answer"]) > 0
    assert data["query"] == request_data["query"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_with_rag(check_vllm):
    """Test query endpoint with RAG retrieval.

    Integration Test: Verifies RAG queries work via API
    Prerequisites: Qdrant and vLLM running
    Expected: Returns answer with sources
    """
    from app.main import app
    from app.services.vectordb import VectorDBService
    from app.services.embedding import EmbeddingService
    from tests.fixtures.integration_data import SAMPLE_DOCUMENTS
    from fastapi.testclient import TestClient

    # Setup: Populate collection with test data
    collection_name = "default"  # FastAPI uses "default" collection
    vectordb_svc = VectorDBService(url="http://localhost:6333")
    embedding_svc = EmbeddingService(device="cpu")

    try:
        # Create and populate collection
        try:
            await vectordb_svc.delete_collection(collection_name)
        except:
            pass

        await vectordb_svc.create_collection(collection_name, 768, "cosine")
        texts = [doc['text'] for doc in SAMPLE_DOCUMENTS]
        embeddings = await embedding_svc.embed_batch_async(texts)
        ids = list(range(len(SAMPLE_DOCUMENTS)))
        await vectordb_svc.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=SAMPLE_DOCUMENTS,
            ids=ids
        )

        # Execute RAG query via API
        client = TestClient(app)

        request_data = {
            "query": "What is machine learning?",
            "use_rag": True,
            "top_k": 3,
            "temperature": 0.7
        }

        response = client.post("/api/v1/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "used_rag" in data
        assert "query" in data

        assert data["used_rag"] is True
        assert len(data["sources"]) > 0
        assert len(data["sources"]) <= 3
        assert len(data["answer"]) > 0

        # Verify sources structure
        for source in data["sources"]:
            assert "text" in source
            assert "score" in source
            assert "id" in source

    finally:
        # Cleanup
        try:
            await vectordb_svc.delete_collection(collection_name)
        except:
            pass


@pytest.mark.integration
def test_query_endpoint_validation():
    """Test query endpoint validates requests.

    Integration Test: Verifies request validation works
    Prerequisites: None
    Expected: Returns 422 for invalid requests
    """
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Test empty query
    response = client.post("/api/v1/query", json={"query": ""})
    assert response.status_code == 422

    # Test missing query field
    response = client.post("/api/v1/query", json={"use_rag": True})
    assert response.status_code == 422

    # Test invalid temperature
    response = client.post("/api/v1/query", json={
        "query": "test",
        "temperature": 3.0  # Above max 2.0
    })
    assert response.status_code == 422

    # Test invalid top_k
    response = client.post("/api/v1/query", json={
        "query": "test",
        "top_k": -1
    })
    assert response.status_code == 422
