"""Unit tests for GCS storage service.


Date: 2025-01-22
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO


class TestGCSStorageService:
    """Test suite for GCSStorageService."""

    def test_gcs_storage_service_initialization(self):
        """Test GCS storage service can be initialized."""
        from app.services.gcs_storage import GCSStorageService

        service = GCSStorageService(
            project_id="test-project",
            bucket_name="test-bucket",
            credentials_path="/path/to/creds.json"
        )

        assert service.project_id == "test-project"
        assert service.bucket_name == "test-bucket"
        assert service.credentials_path == "/path/to/creds.json"
        assert service.client is None
        assert service._session_active is False

    @pytest.mark.asyncio
    async def test_gcs_connect_successfully(self):
        """Test GCS client can connect successfully."""
        from app.services.gcs_storage import GCSStorageService

        service = GCSStorageService(
            project_id="test-project",
            bucket_name="test-bucket"
        )

        with patch('app.services.gcs_storage.Storage') as mock_storage:
            mock_client = AsyncMock()
            mock_storage.return_value = mock_client
            mock_client.get_bucket = AsyncMock()

            await service.connect()

            assert service.client is not None
            assert service._session_active is True
            mock_client.get_bucket.assert_called_once_with("test-bucket")

    @pytest.mark.asyncio
    async def test_gcs_disconnect_successfully(self):
        """Test GCS client can disconnect successfully."""
        from app.services.gcs_storage import GCSStorageService

        service = GCSStorageService(
            project_id="test-project",
            bucket_name="test-bucket"
        )

        # Simulate connected state
        service.client = AsyncMock()
        service._session_active = True

        await service.disconnect()

        assert service._session_active is False
        service.client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_gcs_async_context_manager(self):
        """Test GCS can be used as async context manager."""
        from app.services.gcs_storage import GCSStorageService

        with patch('app.services.gcs_storage.Storage') as mock_storage:
            mock_client = AsyncMock()
            mock_storage.return_value = mock_client
            mock_client.get_bucket = AsyncMock()

            async with GCSStorageService(
                project_id="test-project",
                bucket_name="test-bucket"
            ) as service:
                assert service._session_active is True
                assert service.client is not None

            # After exiting context, should be disconnected
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_gcs_upload_file_successfully(self):
        """Test GCS can upload file successfully."""
        from app.services.gcs_storage import GCSStorageService

        service = GCSStorageService(
            project_id="test-project",
            bucket_name="test-bucket"
        )

        # Setup mock client
        service.client = AsyncMock()
        service._session_active = True
        service.client.upload = AsyncMock()

        # Test data
        file_data = BytesIO(b"test content")
        object_path = "test/document.pdf"
        content_type = "application/pdf"

        gcs_uri = await service.upload_file(
            file_data=file_data,
            object_path=object_path,
            content_type=content_type
        )

        assert gcs_uri == "gs://test-bucket/test/document.pdf"
        service.client.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_gcs_download_file_successfully(self):
        """Test GCS can download file successfully."""
        from app.services.gcs_storage import GCSStorageService

        service = GCSStorageService(
            project_id="test-project",
            bucket_name="test-bucket"
        )

        # Setup mock client
        service.client = AsyncMock()
        service._session_active = True
        service.client.download = AsyncMock(return_value=b"test content")

        content = await service.download_file("test/document.pdf")

        assert content == b"test content"
        service.client.download.assert_called_once_with(
            bucket="test-bucket",
            object_name="test/document.pdf"
        )

    @pytest.mark.asyncio
    async def test_gcs_upload_raises_error_when_not_connected(self):
        """Test GCS upload raises error when not connected."""
        from app.services.gcs_storage import GCSStorageService
        from app.exceptions import StorageError

        service = GCSStorageService(
            project_id="test-project",
            bucket_name="test-bucket"
        )

        # Not connected
        service._session_active = False

        with pytest.raises(StorageError, match="GCS client not connected"):
            await service.upload_file(
                file_data=BytesIO(b"test"),
                object_path="test.pdf",
                content_type="application/pdf"
            )

    @pytest.mark.asyncio
    async def test_gcs_download_raises_error_when_not_connected(self):
        """Test GCS download raises error when not connected."""
        from app.services.gcs_storage import GCSStorageService
        from app.exceptions import StorageError

        service = GCSStorageService(
            project_id="test-project",
            bucket_name="test-bucket"
        )

        # Not connected
        service._session_active = False

        with pytest.raises(StorageError, match="GCS client not connected"):
            await service.download_file("test.pdf")
