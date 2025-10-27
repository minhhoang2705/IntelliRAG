"""Unit tests for VectorDBService.

This module contains comprehensive tests for the VectorDBService class,
which manages vector storage and retrieval in Qdrant.

Test Coverage:
- Service instantiation and configuration
- Collection lifecycle management
- Vector upsert operations (single and batch)
- Vector similarity search with filters

Methodology: Test-Driven Development (TDD)
Target Coverage: >85%


Date: 2025-10-16
"""

import pytest


class TestVectorDBServiceInstantiation:
    """Test suite for VectorDBService instantiation and initialization."""

    def test_vectordb_service_can_be_instantiated(self):
        """Test VectorDBService can be created with URL parameter.

        RED Phase: This test will fail because VectorDBService doesn't exist yet.
        Expected failure: ImportError or ModuleNotFoundError
        """
        from app.services.vectordb import VectorDBService
        service = VectorDBService(url="http://localhost:6333")
        assert service is not None

    def test_vectordb_service_requires_url(self):
        """Test VectorDBService requires URL parameter.

        RED Phase: Should fail with TypeError when URL is not provided.
        """
        from app.services.vectordb import VectorDBService
        with pytest.raises(TypeError):
            service = VectorDBService()

    def test_vectordb_service_initializes_client(self):
        """Test VectorDBService creates AsyncQdrantClient on initialization.

        RED Phase: Will fail because client initialization not implemented.
        """
        from app.services.vectordb import VectorDBService
        service = VectorDBService(url="http://localhost:6333")
        assert service.client is not None
        assert hasattr(service, 'url')
        assert service.url == "http://localhost:6333"

    def test_vectordb_service_accepts_api_key(self):
        """Test VectorDBService accepts optional API key for authentication.

        RED Phase: Will fail because api_key handling not implemented.
        """
        from app.services.vectordb import VectorDBService
        service = VectorDBService(
            url="http://localhost:6333", api_key="secret")
        assert service.api_key == "secret"


class TestVectorDBServiceCollectionManagement:
    """Test suite for VectorDBService collection management operations."""

    @pytest.mark.asyncio
    async def test_vectordb_service_create_collection(self, mocker):
        """Test creating a new collection with 1024-d vectors.

        RED Phase: Will fail because create_collection method doesn't exist.
        """
        from app.services.vectordb import VectorDBService
        service = VectorDBService(url="http://localhost:6333")

        # Mock the client's create_collection to avoid actual Qdrant connection
        mocker.patch.object(
            service.client, 'create_collection', return_value=None)

        success = await service.create_collection(
            collection_name="test_collection",
            vector_size=1024,
            distance="cosine"
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_vectordb_service_create_collection_calls_qdrant_client(self, mocker):
        """Test that create_collection properly calls Qdrant client.

        RED Phase: Will fail because stub doesn't call client.create_collection.
        """
        from app.services.vectordb import VectorDBService
        from qdrant_client.models import Distance, VectorParams

        service = VectorDBService(url="http://localhost:6333")

        # Mock the client's create_collection method
        mock_create = mocker.patch.object(
            service.client, 'create_collection', return_value=None)

        await service.create_collection(
            collection_name="test_collection",
            vector_size=1024,
            distance="cosine"
        )

        # Verify the client method was called with correct parameters
        mock_create.assert_called_once_with(
            collection_name="test_collection",
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )

    @pytest.mark.asyncio
    async def test_vectordb_service_create_collection_invalid_distance(self):
        """Test that create_collection raises ValueError for invalid distance metric.

        RED Phase: Will fail because validation not implemented yet.
        """
        from app.services.vectordb import VectorDBService

        service = VectorDBService(url="http://localhost:6333")

        with pytest.raises(ValueError, match="Unsupported distance metric"):
            await service.create_collection(
                collection_name="test_collection",
                vector_size=1024,
                distance="invalid_metric"
            )

    @pytest.mark.asyncio
    async def test_vectordb_service_collection_exists(self, mocker):
        """Test checking if a collection exists.

        RED Phase: Will fail because collection_exists method doesn't exist.
        """
        from app.services.vectordb import VectorDBService

        service = VectorDBService(url="http://localhost:6333")

        # Mock the client's collection_exists method
        mocker.patch.object(
            service.client, 'collection_exists', return_value=True)

        exists = await service.collection_exists("test_collection")

        assert exists is True

    @pytest.mark.asyncio
    async def test_vectordb_service_delete_collection(self, mocker):
        """Test deleting a collection.

        RED Phase: Will fail because delete_collection method doesn't exist.
        """
        from app.services.vectordb import VectorDBService

        service = VectorDBService(url="http://localhost:6333")

        # Mock the client's delete_collection method
        mocker.patch.object(
            service.client, 'delete_collection', return_value=True)

        success = await service.delete_collection("test_collection")

        assert success is True

    @pytest.mark.asyncio
    async def test_vectordb_service_get_collection_info(self, mocker):
        """Test getting collection information.

        RED Phase: Will fail because get_collection_info method doesn't exist.
        """
        from app.services.vectordb import VectorDBService

        service = VectorDBService(url="http://localhost:6333")

        # Mock collection info response
        mock_info = {
            "status": "green",
            "vectors_count": 100,
            "points_count": 100
        }
        mocker.patch.object(service.client, 'get_collection',
                            return_value=mock_info)

        info = await service.get_collection_info("test_collection")

        assert info is not None
        assert info == mock_info


class TestVectorDBServiceVectorOperations:
    """Test suite for VectorDBService vector upsert operations."""

    @pytest.mark.asyncio
    async def test_vectordb_service_upsert_single_vector(self, mocker):
        """Test upserting a single vector with metadata.

        RED Phase: Will fail because upsert_vectors method doesn't exist.
        """
        from app.services.vectordb import VectorDBService

        service = VectorDBService(url="http://localhost:6333")

        # Mock the client's upsert method
        mocker.patch.object(service.client, 'upsert', return_value=None)

        # Upsert a single 1024-d vector
        vector = [0.1] * 1024
        metadata = {"text": "test document", "source": "test.pdf"}

        success = await service.upsert_vectors(
            collection_name="test_collection",
            vectors=[vector],
            payloads=[metadata],
            ids=["doc_1"]
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_vectordb_service_upsert_calls_qdrant_client(self, mocker):
        """Test that upsert_vectors properly calls Qdrant client.

        RED Phase: Will fail because stub doesn't call client.upsert.
        """
        from app.services.vectordb import VectorDBService

        service = VectorDBService(url="http://localhost:6333")

        # Mock the client's upsert method
        mock_upsert = mocker.patch.object(
            service.client, 'upsert', return_value=None)

        # Upsert a single vector
        vector = [0.1] * 1024
        metadata = {"text": "test document"}

        await service.upsert_vectors(
            collection_name="test_collection",
            vectors=[vector],
            payloads=[metadata],
            ids=["doc_1"]
        )

        # Verify the client method was called
        mock_upsert.assert_called_once()


class TestVectorDBServiceSearchOperations:
    """Test suite for VectorDBService vector search operations."""

    @pytest.mark.asyncio
    async def test_vectordb_service_search_vectors(self, mocker):
        """Test searching for similar vectors.

        RED Phase: Will fail because search_vectors method doesn't exist.
        """
        from app.services.vectordb import VectorDBService

        service = VectorDBService(url="http://localhost:6333")

        # Mock search results
        mock_results = [
            {"id": "doc_1", "score": 0.95, "payload": {"text": "result 1"}},
            {"id": "doc_2", "score": 0.85, "payload": {"text": "result 2"}}
        ]
        mocker.patch.object(service.client, 'search',
                            return_value=mock_results)

        # Search with a query vector
        query_vector = [0.1] * 1024
        results = await service.search_vectors(
            collection_name="test_collection",
            query_vector=query_vector,
            limit=5
        )

        assert len(results) == 2
        assert results[0]["score"] == 0.95
