"""
Unit tests for S3 storage service.

This module tests the S3StorageService implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.storage.s3_storage import S3StorageService
from app.exceptions import StorageError


@pytest.mark.asyncio
async def test_s3_storage_init():
    """Test S3 storage initialization."""
    service = S3StorageService("test-bucket", "us-east-1")

    assert service.bucket_name == "test-bucket"
    assert service.region == "us-east-1"
    assert service._session is None
    assert service._client is None
    assert service._session_active is False


@pytest.mark.asyncio
async def test_s3_storage_connect():
    """Test S3 storage connection."""
    service = S3StorageService("test-bucket", "us-east-1")

    with patch("aioboto3.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_session.client.return_value = mock_client

        await service.connect()

        assert service._session is not None
        assert service._client == mock_client
        assert service._session_active is True


@pytest.mark.asyncio
async def test_s3_storage_disconnect():
    """Test S3 storage disconnection."""
    service = S3StorageService("test-bucket", "us-east-1")
    service._session = MagicMock()
    service._client = AsyncMock()
    service._client.__aexit__ = AsyncMock()
    service._session_active = True

    await service.disconnect()

    service._client.__aexit__.assert_called_once()
    assert service._session_active is False


@pytest.mark.asyncio
async def test_s3_storage_upload_file_success():
    """Test successful file upload to S3."""
    service = S3StorageService("test-bucket", "us-east-1")
    service._session_active = True

    mock_client = AsyncMock()
    mock_client.put_object = AsyncMock()
    service._client = mock_client

    test_data = b"Hello, S3!"
    result = await service.upload_file(
        test_data,
        "test/file.txt",
        "text/plain",
        {"collection": "test"}
    )

    assert result == "s3://test-bucket/test/file.txt"
    mock_client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_s3_storage_upload_file_not_connected():
    """Test file upload fails when not connected."""
    service = S3StorageService("test-bucket", "us-east-1")
    service._session_active = False

    with pytest.raises(StorageError, match="S3 client not connected"):
        await service.upload_file(b"data", "path", "text/plain")


@pytest.mark.asyncio
async def test_s3_storage_download_file_success():
    """Test successful file download from S3."""
    service = S3StorageService("test-bucket", "us-east-1")
    service._session_active = True

    mock_response = {"Body": AsyncMock()}
    mock_response["Body"].read = AsyncMock(return_value=b"Hello from S3!")

    mock_client = AsyncMock()
    mock_client.get_object = AsyncMock(return_value=mock_response)
    service._client = mock_client

    result = await service.download_file("test/file.txt")

    assert result == b"Hello from S3!"
    mock_client.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="test/file.txt"
    )


@pytest.mark.asyncio
async def test_s3_storage_download_file_not_connected():
    """Test file download fails when not connected."""
    service = S3StorageService("test-bucket", "us-east-1")
    service._session_active = False

    with pytest.raises(StorageError, match="S3 client not connected"):
        await service.download_file("path")


@pytest.mark.asyncio
async def test_s3_storage_context_manager():
    """Test S3 storage as async context manager."""
    service = S3StorageService("test-bucket", "us-east-1")

    with patch("aioboto3.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_session.client.return_value = mock_client

        async with service:
            assert service._session_active is True

        mock_client.__aexit__.assert_called_once()
