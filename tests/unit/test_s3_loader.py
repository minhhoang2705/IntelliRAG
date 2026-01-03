"""
Unit tests for S3 loader service.

This module tests the S3LoaderService for loading documents from AWS S3.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.documents import Document


@pytest.fixture
def s3_loader_service():
    """Create S3LoaderService instance for testing."""
    from app.services.loaders.s3_loader import S3LoaderService
    return S3LoaderService(bucket="test-bucket", region="us-east-1")


@pytest.mark.asyncio
async def test_s3_loader_init(s3_loader_service):
    """Test S3 loader service initialization."""
    assert s3_loader_service.bucket == "test-bucket"
    assert s3_loader_service.region == "us-east-1"


@pytest.mark.asyncio
async def test_load_file_success(s3_loader_service):
    """Test loading a single file from S3."""
    mock_document = Document(
        page_content="Test content",
        metadata={"source": "s3://test-bucket/test/file.txt"}
    )

    with patch("app.services.loaders.s3_loader.S3FileLoader") as mock_loader_class:
        mock_loader = MagicMock()
        mock_loader.load.return_value = [mock_document]
        mock_loader_class.return_value = mock_loader

        documents = await s3_loader_service.load_file("test/file.txt")

        assert len(documents) == 1
        assert documents[0].page_content == "Test content"
        mock_loader_class.assert_called_once_with(
            bucket="test-bucket",
            key="test/file.txt"
        )


@pytest.mark.asyncio
async def test_load_directory_success(s3_loader_service):
    """Test loading all files from an S3 directory."""
    mock_documents = [
        Document(
            page_content="File 1 content",
            metadata={"source": "s3://test-bucket/docs/file1.txt"}
        ),
        Document(
            page_content="File 2 content",
            metadata={"source": "s3://test-bucket/docs/file2.txt"}
        )
    ]

    with patch("app.services.loaders.s3_loader.S3DirectoryLoader") as mock_loader_class:
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_documents
        mock_loader_class.return_value = mock_loader

        documents = await s3_loader_service.load_directory("docs/")

        assert len(documents) == 2
        assert documents[0].page_content == "File 1 content"
        assert documents[1].page_content == "File 2 content"
        mock_loader_class.assert_called_once_with(
            bucket="test-bucket",
            prefix="docs/",
            loader_func=None
        )


@pytest.mark.asyncio
async def test_load_directory_with_custom_loader(s3_loader_service):
    """Test loading directory with custom loader function."""
    mock_document = Document(
        page_content="Custom loaded content",
        metadata={"source": "s3://test-bucket/custom/file.pdf"}
    )

    custom_loader_func = MagicMock()

    with patch("app.services.loaders.s3_loader.S3DirectoryLoader") as mock_loader_class:
        mock_loader = MagicMock()
        mock_loader.load.return_value = [mock_document]
        mock_loader_class.return_value = mock_loader

        documents = await s3_loader_service.load_directory(
            prefix="custom/",
            loader_func=custom_loader_func
        )

        assert len(documents) == 1
        mock_loader_class.assert_called_once_with(
            bucket="test-bucket",
            prefix="custom/",
            loader_func=custom_loader_func
        )


@pytest.mark.asyncio
async def test_load_file_with_endpoint_url():
    """Test S3 loader with custom endpoint (LocalStack)."""
    from app.services.loaders.s3_loader import S3LoaderService

    service = S3LoaderService(
        bucket="test-bucket",
        region="us-east-1",
        endpoint_url="http://localhost:4566"
    )

    assert service.endpoint_url == "http://localhost:4566"
