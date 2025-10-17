"""Integration tests for VectorDBService with real Qdrant.

This module tests VectorDBService with actual Qdrant instance,
not mocked. Tests include connection, collection management, vector operations,
and similarity search.

Author: IntelliRAG Team
Date: 2025-10-17
"""

import pytest
import uuid


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_connects_to_real_qdrant():
    """Test connection to actual Qdrant instance.
    
    Integration Test: Verifies VectorDBService can connect to real Qdrant.
    Expected: Client initializes and can query Qdrant.
    """
    from app.services.vectordb import VectorDBService

    service = VectorDBService(url="http://localhost:6333")

    # Verify client is initialized
    assert service.client is not None

    # Test connection by checking health (via collection_exists)
    # This should not raise an exception
    exists = await service.collection_exists("nonexistent_collection")
    assert exists is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_create_collection_real():
    """Test creating actual collection in Qdrant.
    
    Integration Test: Verifies real collection creation in Qdrant.
    Expected: Collection is created successfully and exists.
    """
    from app.services.vectordb import VectorDBService

    service = VectorDBService(url="http://localhost:6333")

    collection_name = f"test_collection_{uuid.uuid4()}"

    try:
        # Create collection
        success = await service.create_collection(
            collection_name=collection_name,
            vector_size=768,
            distance="cosine"
        )

        assert success is True

        # Verify collection exists
        exists = await service.collection_exists(collection_name)
        assert exists is True

        # Get collection info
        info = await service.get_collection_info(collection_name)
        assert info is not None

    finally:
        # Cleanup
        await service.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_collection_lifecycle():
    """Test full collection lifecycle.
    
    Integration Test: Verifies create, query, delete operations work.
    Expected: Full lifecycle works without errors.
    """
    from app.services.vectordb import VectorDBService

    service = VectorDBService(url="http://localhost:6333")
    collection_name = f"test_lifecycle_{uuid.uuid4()}"

    # 1. Create
    await service.create_collection(collection_name, 768, "cosine")
    assert await service.collection_exists(collection_name) is True

    # 2. Get info
    info = await service.get_collection_info(collection_name)
    assert info is not None

    # 3. Delete
    success = await service.delete_collection(collection_name)
    assert success is True

    # 4. Verify deleted
    exists = await service.collection_exists(collection_name)
    assert exists is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_upsert_real_vectors():
    """Test upserting vectors to real Qdrant.
    
    Integration Test: Verifies vector upsert with real Qdrant.
    Expected: Vectors are stored successfully.
    """
    from app.services.vectordb import VectorDBService
    import numpy as np

    service = VectorDBService(url="http://localhost:6333")
    collection_name = f"test_upsert_{uuid.uuid4()}"

    try:
        # Create collection
        await service.create_collection(collection_name, 768, "cosine")

        # Generate test vectors
        vectors = [np.random.rand(768).tolist() for _ in range(10)]
        payloads = [{"text": f"Document {i}", "index": i} for i in range(10)]
        ids = [i for i in range(10)]  # Use integers for Qdrant compatibility

        # Upsert vectors
        success = await service.upsert_vectors(
            collection_name=collection_name,
            vectors=vectors,
            payloads=payloads,
            ids=ids
        )

        assert success is True

        # Verify vectors were stored
        info = await service.get_collection_info(collection_name)
        assert info is not None

    finally:
        await service.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_search_real():
    """Test similarity search with real Qdrant.
    
    Integration Test: Verifies similarity search returns relevant results.
    Expected: Exact match has highest score, results sorted by score.
    """
    from app.services.vectordb import VectorDBService
    import numpy as np
    import asyncio

    service = VectorDBService(url="http://localhost:6333")
    collection_name = f"test_search_{uuid.uuid4()}"

    try:
        # Create collection
        await service.create_collection(collection_name, 768, "cosine")

        # Create and upsert test vectors
        base_vector = np.random.rand(768)
        vectors = [
            base_vector.tolist(),  # Exact match
            (base_vector + np.random.rand(768) * 0.1).tolist(),  # Very similar
            np.random.rand(768).tolist(),  # Random (dissimilar)
        ]

        payloads = [
            {"text": "Exact match", "similarity": "exact", "id_name": "exact"},
            {"text": "Very similar", "similarity": "high", "id_name": "similar"},
            {"text": "Random", "similarity": "low", "id_name": "random"},
        ]

        ids = [0, 1, 2]  # Use integers for Qdrant compatibility

        await service.upsert_vectors(collection_name, vectors, payloads, ids)

        # Wait for indexing (Qdrant may need a moment)
        await asyncio.sleep(1)

        # Search with base vector
        results = await service.search_vectors(
            collection_name=collection_name,
            query_vector=base_vector.tolist(),
            limit=3
        )

        # Verify results
        assert len(results) == 3

        # First result should be exact match (id=0) with high score
        assert results[0].id == 0
        assert results[0].score > 0.99

        # Second should be similar (id=1) with good score
        assert results[1].id == 1
        assert results[1].score > 0.8

        # Results should be sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    finally:
        await service.delete_collection(collection_name)
