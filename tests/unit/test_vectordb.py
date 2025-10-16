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

Author: IntelliRAG Team
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
        service = VectorDBService(url="http://localhost:6333", api_key="secret")
        assert service.api_key == "secret"


class TestVectorDBServiceCollectionManagement:
    """Test suite for VectorDBService collection management operations."""

    @pytest.mark.asyncio
    async def test_vectordb_service_create_collection(self, mocker):
        """Test creating a new collection with 768-d vectors.

        RED Phase: Will fail because create_collection method doesn't exist.
        """
        from app.services.vectordb import VectorDBService
        service = VectorDBService(url="http://localhost:6333")

        # Mock the client's create_collection to avoid actual Qdrant connection
        mocker.patch.object(service.client, 'create_collection', return_value=None)

        success = await service.create_collection(
            collection_name="test_collection",
            vector_size=768,
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
        mock_create = mocker.patch.object(service.client, 'create_collection', return_value=None)

        await service.create_collection(
            collection_name="test_collection",
            vector_size=768,
            distance="cosine"
        )

        # Verify the client method was called with correct parameters
        mock_create.assert_called_once_with(
            collection_name="test_collection",
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
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
                vector_size=768,
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
        mocker.patch.object(service.client, 'collection_exists', return_value=True)

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
        mocker.patch.object(service.client, 'delete_collection', return_value=True)

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
        mocker.patch.object(service.client, 'get_collection', return_value=mock_info)

        info = await service.get_collection_info("test_collection")

        assert info is not None
        assert info == mock_info
