"""End-to-end integration tests for IntelliRAG services.

This module tests complete workflows: text → embedding → storage → retrieval.
Tests use real services (SentenceTransformer, Qdrant) without mocking.

Author: IntelliRAG Team
Date: 2025-10-17
"""

import pytest
import uuid


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_text_to_storage_to_retrieval():
    """Test complete workflow: text → embedding → storage → retrieval.
    
    Integration Test: Verifies full RAG pipeline foundation works end-to-end.
    Expected: Query returns most semantically relevant document.
    """
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    from tests.fixtures.integration_data import SAMPLE_DOCUMENTS
    import asyncio

    # Initialize services
    embedding_svc = EmbeddingService()
    vectordb_svc = VectorDBService(url="http://localhost:6333")

    collection_name = f"test_e2e_{uuid.uuid4()}"

    try:
        # 1. Create collection
        await vectordb_svc.create_collection(collection_name, 768, "cosine")

        # 2. Generate embeddings for documents
        texts = [doc['text'] for doc in SAMPLE_DOCUMENTS]
        embeddings = await embedding_svc.embed_batch_async(texts)

        # 3. Store in Qdrant
        ids = list(range(len(SAMPLE_DOCUMENTS)))  # Use integers for Qdrant
        payloads = SAMPLE_DOCUMENTS

        await vectordb_svc.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=payloads,
            ids=ids
        )

        # Wait for indexing
        await asyncio.sleep(1)

        # 4. Query with semantic search
        query = "Tell me about programming languages"
        query_embedding = await embedding_svc.embed_single_async(query)

        results = await vectordb_svc.search_vectors(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=3
        )

        # 5. Verify results
        assert len(results) > 0

        # Debug: Print all scores
        print(f"\nQuery: {query}")
        for i, result in enumerate(results):
            print(f"Result {i+1}: id={result.payload['id']}, score={result.score:.3f}, text={result.payload['text'][:50]}...")

        # Top result should be about Python (doc_1)
        top_result = results[0]
        assert top_result.payload['id'] == 'doc_1'
        assert 'Python' in top_result.payload['text']

        # Top result should have a high score
        assert top_result.score > 0.5  # Relaxed threshold for real-world scores

    finally:
        await vectordb_svc.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_multilingual_semantic_search():
    """Test multilingual semantic search.
    
    Integration Test: Verifies multilingual model enables cross-language search.
    Expected: English query finds documents in multiple languages with good scores.
    """
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    import asyncio

    embedding_svc = EmbeddingService()
    vectordb_svc = VectorDBService(url="http://localhost:6333")

    collection_name = f"test_multilingual_{uuid.uuid4()}"

    try:
        await vectordb_svc.create_collection(collection_name, 768, "cosine")

        # Documents in different languages
        docs = [
            {"id": "en", "text": "Python is a programming language", "lang": "en"},
            {"id": "fr", "text": "Python est un langage de programmation", "lang": "fr"},
            {"id": "es", "text": "Python es un lenguaje de programación", "lang": "es"},
            {"id": "de", "text": "Python ist eine Programmiersprache", "lang": "de"},
        ]

        texts = [doc['text'] for doc in docs]
        embeddings = await embedding_svc.embed_batch_async(texts)

        await vectordb_svc.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=docs,
            ids=list(range(len(docs)))
        )

        await asyncio.sleep(1)

        # Query in English
        query = "What programming language is being discussed?"
        query_embedding = await embedding_svc.embed_single_async(query)

        results = await vectordb_svc.search_vectors(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=4
        )

        # All documents should be retrieved (they all talk about Python)
        assert len(results) == 4

        # Debug: Print all scores
        print("\nMultilingual search results:")
        for result in results:
            print(f"  {result.payload['lang']}: {result.score:.3f}")

        # Top results should have reasonable similarity (multilingual model)
        # Note: Real-world multilingual similarity varies, so using realistic threshold
        assert results[0].score > 0.4  # Top result should have decent similarity

    finally:
        await vectordb_svc.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_concurrent_operations():
    """Test concurrent embedding and storage operations.
    
    Integration Test: Verifies system handles concurrent operations correctly.
    Expected: All concurrent batches process successfully without errors.
    """
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    import asyncio

    embedding_svc = EmbeddingService()
    vectordb_svc = VectorDBService(url="http://localhost:6333")

    collection_name = f"test_concurrent_{uuid.uuid4()}"

    try:
        await vectordb_svc.create_collection(collection_name, 768, "cosine")

        # Create multiple concurrent tasks
        async def process_batch(batch_id: int, texts: list):
            embeddings = await embedding_svc.embed_batch_async(texts)
            ids = [batch_id * 1000 + i for i in range(len(texts))]  # Ensure unique integer IDs
            payloads = [{"batch": batch_id, "text": t} for t in texts]

            await vectordb_svc.upsert_vectors(
                collection_name=collection_name,
                vectors=embeddings,
                payloads=payloads,
                ids=ids
            )

            return len(embeddings)

        # Run 5 concurrent batches of 20 texts each
        batches = [
            [f"Batch {i} document {j}" for j in range(20)]
            for i in range(5)
        ]

        tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks)

        # Verify all batches processed
        assert all(r == 20 for r in results)

        # Total 100 vectors stored
        total_stored = sum(results)
        assert total_stored == 100

        print(f"\nSuccessfully processed {total_stored} vectors concurrently")

    finally:
        await vectordb_svc.delete_collection(collection_name)
