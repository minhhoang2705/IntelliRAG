"""Unit tests for Qdrant payload schema models.

This module tests the Pydantic models that define the structure of metadata
payloads stored alongside vectors in Qdrant. These payloads replace the need
for a separate PostgreSQL database.

Test Coverage:
- DocumentMetadata validation
- GCSStorageInfo validation
- ChunkMetadata validation
- ProcessingMetadata validation
- QdrantPayload comprehensive validation
- Field constraints and defaults
- Invalid data handling

Methodology: Test-Driven Development (TDD)
Target Coverage: >90%


Date: 2025-01-23
"""

import pytest
from datetime import datetime, UTC
from pydantic import ValidationError


class TestDocumentMetadataSchema:
    """Test suite for DocumentMetadata schema."""

    def test_document_metadata_valid_creation(self):
        """Test DocumentMetadata can be created with valid data."""
        from app.models.schemas import DocumentMetadata

        metadata = DocumentMetadata(
            filename="test.pdf",
            content_type="application/pdf",
            file_size=1024,
            upload_timestamp=datetime.now(UTC)
        )

        assert metadata.filename == "test.pdf"
        assert metadata.content_type == "application/pdf"
        assert metadata.file_size == 1024
        assert isinstance(metadata.upload_timestamp, datetime)

    def test_document_metadata_file_size_must_be_positive(self):
        """Test DocumentMetadata file_size must be positive integer."""
        from app.models.schemas import DocumentMetadata

        with pytest.raises(ValidationError) as exc_info:
            DocumentMetadata(
                filename="test.pdf",
                content_type="application/pdf",
                file_size=-100,
                upload_timestamp=datetime.now(UTC)
            )

        assert "file_size" in str(exc_info.value).lower()


class TestGCSStorageInfoSchema:
    """Test suite for GCSStorageInfo schema."""

    def test_gcs_storage_info_valid_creation(self):
        """Test GCSStorageInfo can be created with valid data."""
        from app.models.schemas import GCSStorageInfo

        gcs_info = GCSStorageInfo(
            gcs_uri="gs://bucket-name/path/to/file.pdf",
            gcs_bucket="bucket-name",
            gcs_object_path="path/to/file.pdf"
        )

        assert gcs_info.gcs_uri == "gs://bucket-name/path/to/file.pdf"
        assert gcs_info.gcs_bucket == "bucket-name"
        assert gcs_info.gcs_object_path == "path/to/file.pdf"

    def test_gcs_storage_info_uri_must_start_with_gs(self):
        """Test GCSStorageInfo URI must start with 'gs://'."""
        from app.models.schemas import GCSStorageInfo

        with pytest.raises(ValidationError) as exc_info:
            GCSStorageInfo(
                gcs_uri="http://bucket-name/file.pdf",
                gcs_bucket="bucket-name",
                gcs_object_path="file.pdf"
            )

        assert "gcs_uri" in str(exc_info.value).lower()


class TestChunkMetadataSchema:
    """Test suite for ChunkMetadata schema."""

    def test_chunk_metadata_valid_creation(self):
        """Test ChunkMetadata can be created with valid data."""
        from app.models.schemas import ChunkMetadata

        chunk = ChunkMetadata(
            chunk_index=0,
            total_chunks=5,
            chunk_text="This is the first chunk of text.",
            chunk_size=512,
            chunk_overlap=50
        )

        assert chunk.chunk_index == 0
        assert chunk.total_chunks == 5
        assert chunk.chunk_text == "This is the first chunk of text."
        assert chunk.chunk_size == 512
        assert chunk.chunk_overlap == 50

    def test_chunk_metadata_index_must_be_non_negative(self):
        """Test ChunkMetadata chunk_index must be non-negative."""
        from app.models.schemas import ChunkMetadata

        with pytest.raises(ValidationError) as exc_info:
            ChunkMetadata(
                chunk_index=-1,
                total_chunks=5,
                chunk_text="Text content",
                chunk_size=512,
                chunk_overlap=50
            )

        assert "chunk_index" in str(exc_info.value).lower()

    def test_chunk_metadata_text_cannot_be_empty(self):
        """Test ChunkMetadata chunk_text cannot be empty string."""
        from app.models.schemas import ChunkMetadata

        with pytest.raises(ValidationError) as exc_info:
            ChunkMetadata(
                chunk_index=0,
                total_chunks=1,
                chunk_text="",
                chunk_size=512,
                chunk_overlap=50
            )

        assert "chunk_text" in str(exc_info.value).lower()


class TestProcessingMetadataSchema:
    """Test suite for ProcessingMetadata schema."""

    def test_processing_metadata_valid_creation(self):
        """Test ProcessingMetadata can be created with valid data."""
        from app.models.schemas import ProcessingMetadata

        processing = ProcessingMetadata(
            processing_timestamp=datetime.now(UTC),
            embedding_model="BAAI/bge-m3",
            embedding_dimension=1024,
            chunk_strategy="semantic"
        )

        assert isinstance(processing.processing_timestamp, datetime)
        assert processing.embedding_model == "BAAI/bge-m3"
        assert processing.embedding_dimension == 1024
        assert processing.chunk_strategy == "semantic"

    def test_processing_metadata_embedding_dimension_must_be_positive(self):
        """Test ProcessingMetadata embedding_dimension must be positive."""
        from app.models.schemas import ProcessingMetadata

        with pytest.raises(ValidationError) as exc_info:
            ProcessingMetadata(
                processing_timestamp=datetime.now(UTC),
                embedding_model="test-model",
                embedding_dimension=0,
                chunk_strategy="semantic"
            )

        assert "embedding_dimension" in str(exc_info.value).lower()


class TestQdrantPayloadSchema:
    """Test suite for comprehensive QdrantPayload schema."""

    def test_qdrant_payload_valid_creation(self):
        """Test QdrantPayload can be created with all components."""
        from app.models.schemas import (
            QdrantPayload, DocumentMetadata, GCSStorageInfo,
            ChunkMetadata, ProcessingMetadata
        )

        payload = QdrantPayload(
            document=DocumentMetadata(
                filename="test.pdf",
                content_type="application/pdf",
                file_size=2048,
                upload_timestamp=datetime.now(UTC)
            ),
            storage=GCSStorageInfo(
                gcs_uri="gs://bucket/test.pdf",
                gcs_bucket="bucket",
                gcs_object_path="test.pdf"
            ),
            chunk=ChunkMetadata(
                chunk_index=0,
                total_chunks=3,
                chunk_text="Sample text",
                chunk_size=512,
                chunk_overlap=50
            ),
            processing=ProcessingMetadata(
                processing_timestamp=datetime.now(UTC),
                embedding_model="BAAI/bge-m3",
                embedding_dimension=1024,
                chunk_strategy="semantic"
            ),
            collection_id="default",
            tags=["finance", "report"]
        )

        assert payload.document.filename == "test.pdf"
        assert payload.storage.gcs_bucket == "bucket"
        assert payload.chunk.chunk_index == 0
        assert payload.processing.embedding_dimension == 1024
        assert payload.collection_id == "default"
        assert "finance" in payload.tags

    def test_qdrant_payload_to_dict(self):
        """Test QdrantPayload can be converted to dict for Qdrant storage."""
        from app.models.schemas import (
            QdrantPayload, DocumentMetadata, GCSStorageInfo,
            ChunkMetadata, ProcessingMetadata
        )

        payload = QdrantPayload(
            document=DocumentMetadata(
                filename="test.pdf",
                content_type="application/pdf",
                file_size=2048,
                upload_timestamp=datetime.now(UTC)
            ),
            storage=GCSStorageInfo(
                gcs_uri="gs://bucket/test.pdf",
                gcs_bucket="bucket",
                gcs_object_path="test.pdf"
            ),
            chunk=ChunkMetadata(
                chunk_index=0,
                total_chunks=1,
                chunk_text="Text",
                chunk_size=512,
                chunk_overlap=50
            ),
            processing=ProcessingMetadata(
                processing_timestamp=datetime.now(UTC),
                embedding_model="test-model",
                embedding_dimension=1024,
                chunk_strategy="semantic"
            ),
            collection_id="default"
        )

        payload_dict = payload.model_dump(mode='json')

        assert isinstance(payload_dict, dict)
        assert "document" in payload_dict
        assert "storage" in payload_dict
        assert "chunk" in payload_dict
        assert "processing" in payload_dict
        assert payload_dict["collection_id"] == "default"

    def test_qdrant_payload_tags_defaults_to_empty_list(self):
        """Test QdrantPayload tags field defaults to empty list."""
        from app.models.schemas import (
            QdrantPayload, DocumentMetadata, GCSStorageInfo,
            ChunkMetadata, ProcessingMetadata
        )

        payload = QdrantPayload(
            document=DocumentMetadata(
                filename="test.pdf",
                content_type="application/pdf",
                file_size=2048,
                upload_timestamp=datetime.now(UTC)
            ),
            storage=GCSStorageInfo(
                gcs_uri="gs://bucket/test.pdf",
                gcs_bucket="bucket",
                gcs_object_path="test.pdf"
            ),
            chunk=ChunkMetadata(
                chunk_index=0,
                total_chunks=1,
                chunk_text="Text",
                chunk_size=512,
                chunk_overlap=50
            ),
            processing=ProcessingMetadata(
                processing_timestamp=datetime.now(UTC),
                embedding_model="test-model",
                embedding_dimension=1024,
                chunk_strategy="semantic"
            ),
            collection_id="default"
        )

        assert payload.tags == []
        assert isinstance(payload.tags, list)
