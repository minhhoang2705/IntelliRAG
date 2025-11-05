"""Unit tests for VectorDB dimension detection and auto-migration.

Tests the automatic detection of embedding dimension changes and
collection migration/recreation logic.

Date: 2025-11-05
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.vectordb import VectorDBService
from qdrant_client.models import Distance, VectorParams, CollectionInfo, CollectionsResponse


class TestVectorDBDimensionDetection:
    """Test dimension detection and validation."""

    @pytest.fixture
    def vectordb_service(self):
        """Create VectorDBService instance with mocked client."""
        service = VectorDBService(url="http://localhost:6333")
        service.client = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_ensure_collection_creates_new_if_not_exists(self, vectordb_service):
        """Test that ensure_collection_with_dimension creates new collection if it doesn't exist."""
        # Arrange
        vectordb_service.client.collection_exists = AsyncMock(
            return_value=False)
        vectordb_service.client.create_collection = AsyncMock()

        # Act
        result = await vectordb_service.ensure_collection_with_dimension(
            collection_name="test_collection",
            vector_size=1024,
            distance="cosine"
        )

        # Assert
        assert result["action"] == "created"
        assert result["dimension"] == 1024
        vectordb_service.client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_collection_accepts_existing_with_same_dimension(self, vectordb_service):
        """Test that existing collection with same dimension is accepted."""
        # Arrange
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1024
        mock_collection_info.points_count = 100

        vectordb_service.client.collection_exists = AsyncMock(
            return_value=True)
        vectordb_service.client.get_collection = AsyncMock(
            return_value=mock_collection_info)

        # Act
        result = await vectordb_service.ensure_collection_with_dimension(
            collection_name="test_collection",
            vector_size=1024,
            distance="cosine"
        )

        # Assert
        assert result["action"] == "exists"
        assert result["dimension"] == 1024

    @pytest.mark.asyncio
    async def test_ensure_collection_raises_on_dimension_mismatch_by_default(self, vectordb_service):
        """Test that dimension mismatch raises ValueError by default."""
        # Arrange
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1024  # Existing dimension

        vectordb_service.client.collection_exists = AsyncMock(
            return_value=True)
        vectordb_service.client.get_collection = AsyncMock(
            return_value=mock_collection_info)

        # Act & Assert
        with pytest.raises(ValueError, match="dimension 1024.*dimension 384"):
            await vectordb_service.ensure_collection_with_dimension(
                collection_name="test_collection",
                vector_size=384,  # New dimension (mismatch!)
                distance="cosine"
            )

    @pytest.mark.asyncio
    async def test_ensure_collection_creates_new_with_suffix_on_mismatch(self, vectordb_service):
        """Test that dimension mismatch creates new collection with dimension suffix."""
        # Arrange
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1024

        vectordb_service.client.collection_exists = AsyncMock(
            side_effect=[True, False])  # Old exists, new doesn't
        vectordb_service.client.get_collection = AsyncMock(
            return_value=mock_collection_info)
        vectordb_service.client.create_collection = AsyncMock()

        # Act
        result = await vectordb_service.ensure_collection_with_dimension(
            collection_name="test_collection",
            vector_size=384,
            distance="cosine",
            auto_migrate=True
        )

        # Assert
        assert result["action"] == "created_new"
        assert result["new_collection_name"] == "test_collection_384"
        assert result["old_collection_name"] == "test_collection"
        assert result["dimension"] == 384

    @pytest.mark.asyncio
    async def test_ensure_collection_recreates_if_recreate_flag_set(self, vectordb_service):
        """Test that collection is recreated if recreate_if_mismatch=True."""
        # Arrange
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1024
        mock_collection_info.points_count = 500

        vectordb_service.client.collection_exists = AsyncMock(
            return_value=True)
        vectordb_service.client.get_collection = AsyncMock(
            return_value=mock_collection_info)
        vectordb_service.client.delete_collection = AsyncMock()
        vectordb_service.client.create_collection = AsyncMock()

        # Act
        result = await vectordb_service.ensure_collection_with_dimension(
            collection_name="test_collection",
            vector_size=384,
            distance="cosine",
            recreate_if_mismatch=True
        )

        # Assert
        assert result["action"] == "recreated"
        assert result["dimension"] == 384
        assert result["points_deleted"] == 500
        vectordb_service.client.delete_collection.assert_called_once_with(
            "test_collection")
        vectordb_service.client.create_collection.assert_called_once()


class TestCollectionNamingHelpers:
    """Test collection naming with model dimensions."""

    def test_format_collection_name_with_dimension(self):
        """Test formatting collection name with dimension suffix."""
        from app.services.vectordb import format_collection_name_with_dimension

        result = format_collection_name_with_dimension("docs", 1024)
        assert result == "docs_1024"

        result = format_collection_name_with_dimension("my-collection", 384)
        assert result == "my-collection_384"

    def test_parse_collection_name_dimension(self):
        """Test parsing dimension from collection name."""
        from app.services.vectordb import parse_collection_dimension

        # With dimension suffix
        result = parse_collection_dimension("docs_1024")
        assert result == 1024

        result = parse_collection_dimension("my-collection_384")
        assert result == 384

        # Without dimension suffix (returns None)
        result = parse_collection_dimension("docs")
        assert result is None

    def test_get_collection_name_for_model(self):
        """Test getting collection name based on model info."""
        from app.services.vectordb import get_collection_name_for_model

        # Test with different dimensions
        result = get_collection_name_for_model(
            base_name="docs",
            model_name="BAAI/bge-m3",
            dimension=1024
        )
        assert result == "docs_bge_m3_1024"

        result = get_collection_name_for_model(
            base_name="products",
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            dimension=384
        )
        assert result == "products_all_minilm_l6_v2_384"


class TestAutoMigration:
    """Test automatic migration logic."""

    @pytest.fixture
    def vectordb_service(self):
        """Create VectorDBService with mocked client."""
        service = VectorDBService(url="http://localhost:6333")
        service.client = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_migrate_collection_copies_points_to_new_collection(self, vectordb_service):
        """Test that migration copies points from old to new collection."""
        # Arrange
        old_collection = "docs_1024"
        new_collection = "docs_384"

        # Mock existing points
        mock_point_1 = MagicMock()
        mock_point_1.id = "id1"
        mock_point_1.payload = {"text": "Document 1",
                                "metadata": {"source": "file1.pdf"}}
        mock_point_1.vector = [0.1] * 1024

        mock_point_2 = MagicMock()
        mock_point_2.id = "id2"
        mock_point_2.payload = {"text": "Document 2",
                                "metadata": {"source": "file2.pdf"}}
        mock_point_2.vector = [0.2] * 1024

        # Mock scroll to retrieve points
        vectordb_service.client.scroll = AsyncMock(return_value=(
            [mock_point_1, mock_point_2],
            None  # No next page
        ))

        # Mock embedding service (for re-embedding)
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_batch = MagicMock(return_value=[
            [0.1] * 384,  # New 384-dim embeddings
            [0.2] * 384
        ])

        vectordb_service.client.upsert = AsyncMock()

        # Act
        result = await vectordb_service.migrate_collection(
            old_collection_name=old_collection,
            new_collection_name=new_collection,
            embedding_service=mock_embedding_service
        )

        # Assert
        assert result["points_migrated"] == 2
        assert result["old_collection"] == old_collection
        assert result["new_collection"] == new_collection
        vectordb_service.client.upsert.assert_called_once()
        mock_embedding_service.embed_batch.assert_called_once_with(
            ["Document 1", "Document 2"])

    @pytest.mark.asyncio
    async def test_migrate_collection_handles_empty_source(self, vectordb_service):
        """Test migration gracefully handles empty source collection."""
        # Arrange
        vectordb_service.client.scroll = AsyncMock(return_value=([], None))
        mock_embedding_service = MagicMock()

        # Act
        result = await vectordb_service.migrate_collection(
            old_collection_name="empty_1024",
            new_collection_name="empty_384",
            embedding_service=mock_embedding_service
        )

        # Assert
        assert result["points_migrated"] == 0
        mock_embedding_service.embed_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_migrate_collection_batches_large_datasets(self, vectordb_service):
        """Test that migration processes large datasets in batches."""
        # Arrange
        # Create 250 mock points (should be processed in batches of 100)
        mock_points_batch_1 = [MagicMock(
            id=f"id{i}",
            payload={"text": f"Doc {i}"},
            vector=[0.1] * 1024
        ) for i in range(100)]

        mock_points_batch_2 = [MagicMock(
            id=f"id{i}",
            payload={"text": f"Doc {i}"},
            vector=[0.2] * 1024
        ) for i in range(100, 200)]

        mock_points_batch_3 = [MagicMock(
            id=f"id{i}",
            payload={"text": f"Doc {i}"},
            vector=[0.3] * 1024
        ) for i in range(200, 250)]

        # Mock scroll to return batches
        vectordb_service.client.scroll = AsyncMock(side_effect=[
            (mock_points_batch_1, "offset_100"),
            (mock_points_batch_2, "offset_200"),
            (mock_points_batch_3, None)
        ])

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed_batch = MagicMock(side_effect=[
            [[0.1] * 384] * 100,
            [[0.2] * 384] * 100,
            [[0.3] * 384] * 50
        ])

        vectordb_service.client.upsert = AsyncMock()

        # Act
        result = await vectordb_service.migrate_collection(
            old_collection_name="large_1024",
            new_collection_name="large_384",
            embedding_service=mock_embedding_service,
            batch_size=100
        )

        # Assert
        assert result["points_migrated"] == 250
        assert vectordb_service.client.scroll.call_count == 3
        assert mock_embedding_service.embed_batch.call_count == 3
        assert vectordb_service.client.upsert.call_count == 3
