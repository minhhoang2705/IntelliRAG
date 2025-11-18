"""Integration tests for RAG Pipeline Service with real services.

This module tests the RAGPipelineService with real Qdrant, vLLM,
and SentenceTransformers without mocking.


Date: 2025-10-18
"""

import pytest
import uuid


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_pipeline_with_real_services(check_vllm):
    """Test complete RAG pipeline with real services.

    Integration Test: Full RAG flow (embed → retrieve → generate)
    Prerequisites: Qdrant and vLLM running
    Expected: Returns answer with relevant sources
    """
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    from app.services.llm_client import LLMClientService
    from app.services.rag_pipeline import RAGPipelineService
    from tests.fixtures.integration_data import SAMPLE_DOCUMENTS

    # Initialize services
    embedding_svc = EmbeddingService(device="cpu", use_remote=True)
    vectordb_svc = VectorDBService(url="http://localhost:6333")
    llm_client = LLMClientService(
        base_url="http://localhost:8000/v1",
        model="Qwen/Qwen3-0.6B"
    )

    rag_pipeline = RAGPipelineService(
        embedding_service=embedding_svc,
        vectordb_service=vectordb_svc,
        llm_client=llm_client
    )

    collection_name = f"test_rag_{uuid.uuid4()}"

    try:
        # 1. Create collection and populate with documents
        await vectordb_svc.create_collection(collection_name, 1024, "cosine")

        texts = [doc['text'] for doc in SAMPLE_DOCUMENTS]
        embeddings = await embedding_svc.embed_batch_async(texts)
        ids = list(range(len(SAMPLE_DOCUMENTS)))

        await vectordb_svc.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=SAMPLE_DOCUMENTS,
            ids=ids
        )

        # 2. Execute RAG query
        result = await rag_pipeline.query_with_rag(
            query="What is machine learning?",
            collection_name=collection_name,
            top_k=3,
            temperature=0.7
        )

        # 3. Verify results
        assert "answer" in result
        assert "sources" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) <= 3

        # Verify sources have required fields
        for source in result["sources"]:
            assert "text" in source
            assert "score" in source
            assert "id" in source
            assert 0.0 <= source["score"] <= 1.0

    finally:
        # Cleanup
        try:
            await vectordb_svc.delete_collection(collection_name)
        except:
            pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_pipeline_different_top_k_values(check_vllm):
    """Test RAG pipeline with different top_k values.

    Integration Test: Verifies retrieval with k=1, 3, 5
    Prerequisites: Qdrant and vLLM running
    Expected: Returns correct number of sources
    """
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    from app.services.llm_client import LLMClientService
    from app.services.rag_pipeline import RAGPipelineService
    from tests.fixtures.integration_data import SAMPLE_DOCUMENTS

    # Initialize services
    embedding_svc = EmbeddingService(device="cpu")
    vectordb_svc = VectorDBService(url="http://localhost:6333")
    llm_client = LLMClientService(
        base_url="http://localhost:8000/v1",
        model="Qwen/Qwen3-0.6B"
    )

    rag_pipeline = RAGPipelineService(
        embedding_service=embedding_svc,
        vectordb_service=vectordb_svc,
        llm_client=llm_client
    )

    collection_name = f"test_rag_topk_{uuid.uuid4()}"

    try:
        # Setup collection
        await vectordb_svc.create_collection(collection_name, 1024, "cosine")
        texts = [doc['text'] for doc in SAMPLE_DOCUMENTS]
        embeddings = await embedding_svc.embed_batch_async(texts)
        ids = list(range(len(SAMPLE_DOCUMENTS)))
        await vectordb_svc.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=SAMPLE_DOCUMENTS,
            ids=ids
        )

        # Test different top_k values
        for k in [1, 3, 5]:
            result = await rag_pipeline.query_with_rag(
                query="What is artificial intelligence?",
                collection_name=collection_name,
                top_k=k,
                temperature=0.7
            )

            assert len(result["sources"]) <= k
            assert len(result["answer"]) > 0

    finally:
        try:
            await vectordb_svc.delete_collection(collection_name)
        except:
            pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_pipeline_source_attribution(check_vllm):
    """Test RAG pipeline returns correct source attribution.

    Integration Test: Verifies sources are sorted by relevance score
    Prerequisites: Qdrant and vLLM running
    Expected: Sources sorted descending by score
    """
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    from app.services.llm_client import LLMClientService
    from app.services.rag_pipeline import RAGPipelineService
    from tests.fixtures.integration_data import SAMPLE_DOCUMENTS

    # Initialize services
    embedding_svc = EmbeddingService(device="cpu")
    vectordb_svc = VectorDBService(url="http://localhost:6333")
    llm_client = LLMClientService(
        base_url="http://localhost:8000/v1",
        model="Qwen/Qwen3-0.6B"
    )

    rag_pipeline = RAGPipelineService(
        embedding_service=embedding_svc,
        vectordb_service=vectordb_svc,
        llm_client=llm_client
    )

    collection_name = f"test_rag_sources_{uuid.uuid4()}"

    try:
        # Setup collection
        await vectordb_svc.create_collection(collection_name, 1024, "cosine")
        texts = [doc['text'] for doc in SAMPLE_DOCUMENTS]
        embeddings = await embedding_svc.embed_batch_async(texts)
        ids = list(range(len(SAMPLE_DOCUMENTS)))
        await vectordb_svc.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=SAMPLE_DOCUMENTS,
            ids=ids
        )

        # Execute query
        result = await rag_pipeline.query_with_rag(
            query="What is deep learning?",
            collection_name=collection_name,
            top_k=5,
            temperature=0.7
        )

        # Verify sources are sorted by score (descending)
        sources = result["sources"]
        if len(sources) > 1:
            scores = [s["score"] for s in sources]
            assert scores == sorted(
                scores, reverse=True), "Sources should be sorted by score descending"

        # Verify all scores are valid
        for source in sources:
            assert 0.0 <= source["score"] <= 1.0
            assert isinstance(source["text"], str)
            assert len(source["text"]) > 0

    finally:
        try:
            await vectordb_svc.delete_collection(collection_name)
        except:
            pass
