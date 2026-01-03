"""Unit tests for upload endpoint.

This module tests the file upload API endpoint with comprehensive TDD coverage.

Date: 2025-10-28
Updated: 2025-10-29 - Full production-ready tests (TDD RED phase)
Updated: 2025-12-31 - Updated for cloud-agnostic storage with dependency injection
"""

import pytest
from httpx import ASGITransport, AsyncClient
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock


def create_mock_storage_service(upload_return_value="gs://bucket/test.pdf"):
    """Create a mock storage service that implements ObjectStorageProtocol."""
    mock = MagicMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.upload_file = AsyncMock(return_value=upload_return_value)
    mock.download_file = AsyncMock(return_value=b"test content")

    # Make it work as async context manager
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)

    return mock


class TestUploadEndpoint:
    """Comprehensive test suite for upload endpoint (TDD)."""

    @pytest.mark.asyncio
    async def test_upload_valid_pdf_success(self, auth_override):
        """Valid PDF upload should return complete response with storage path.

        Expected: 200 status, file_id (UUID), storage_path, file_size, mime_type, uploaded_at.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key
        from app.api.v1.upload import get_storage_service

        pdf_content = b"%PDF-1.4 test content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "documents"}

        mock_storage = create_mock_storage_service("gs://intellirag-uploads/uuid-123/test.pdf")

        app.dependency_overrides[verify_api_key] = auth_override
        app.dependency_overrides[get_storage_service] = lambda: mock_storage
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/upload", files=files, data=data)

            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()

            # Verify complete response schema (storage_path is cloud-agnostic)
            assert "file_id" in data, "Response must include file_id"
            assert "storage_path" in data, "Response must include storage_path"
            assert "file_size" in data, "Response must include file_size"
            assert "mime_type" in data, "Response must include mime_type"
            assert "uploaded_at" in data, "Response must include uploaded_at"

            # Verify values - storage_path can be gs:// or s3://
            assert data["filename"] == "test.pdf"
            assert data["storage_path"].startswith(("gs://", "s3://"))
            assert data["file_size"] == len(pdf_content)
            assert data["mime_type"] == "application/pdf"

            # Verify UUID format for file_id
            import re
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            assert re.match(uuid_pattern, data["file_id"]), "file_id must be UUID format"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_file_too_large_returns_413(self, auth_override):
        """Files exceeding 50MB should return 413 Payload Too Large.

        Expected: 413 status code with error message.
        RED: This should FAIL as size validation doesn't exist.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        # Create 51MB file (exceeds limit)
        large_content = b"x" * (51 * 1024 * 1024)
        files = {"file": ("large.pdf", BytesIO(large_content), "application/pdf")}
        data = {"collection_name": "docs"}

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/upload", files=files, data=data)

            assert response.status_code == 413, f"Expected 413 for large file, got {response.status_code}"
            error_data = response.json()
            assert "detail" in error_data
            assert "too large" in error_data["detail"].lower() or "size" in error_data["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type_returns_400(self, auth_override):
        """Unsupported file types should return 400 Bad Request.

        Expected: 400 status for .exe, .sh, or other non-document files.
        RED: This should FAIL as file type validation doesn't exist.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        exe_content = b"MZ\x90\x00"  # EXE magic bytes
        files = {"file": ("malware.exe", BytesIO(exe_content), "application/x-executable")}
        data = {"collection_name": "docs"}

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/upload", files=files, data=data)

            assert response.status_code == 400, f"Expected 400 for invalid type, got {response.status_code}"
            error_data = response.json()
            assert "detail" in error_data
            assert "invalid" in error_data["detail"].lower() or "type" in error_data["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_gcs_failure_returns_500(self, auth_override):
        """Storage upload failure should return 500 Internal Server Error.

        Expected: 500 status with error message when storage fails.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key
        from app.api.v1.upload import get_storage_service

        pdf_content = b"%PDF-1.4 test"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "docs"}

        # Create a mock that fails on context manager entry
        mock_storage = MagicMock()
        mock_storage.__aenter__ = AsyncMock(side_effect=Exception("Storage connection failed"))
        mock_storage.__aexit__ = AsyncMock(return_value=None)

        app.dependency_overrides[verify_api_key] = auth_override
        app.dependency_overrides[get_storage_service] = lambda: mock_storage
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/upload", files=files, data=data)

            assert response.status_code == 500, f"Expected 500 for storage failure, got {response.status_code}"
            error_data = response.json()
            assert "detail" in error_data
            assert "upload failed" in error_data["detail"].lower() or "error" in error_data["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_requires_collection_name(self, auth_override):
        """Upload should require collection_name parameter.

        Expected: 422 validation error when collection_name is missing.
        RED: This should FAIL as validation doesn't exist.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        pdf_content = b"%PDF-1.4 test"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        # Missing collection_name

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/upload", files=files)

            assert response.status_code == 422, "Should require collection_name parameter"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_validates_allowed_mime_types(self, auth_override):
        """Only allowed MIME types should be accepted.

        Expected: PDF, DOCX, TXT, CSV, MD allowed. Others rejected with 400.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key
        from app.api.v1.upload import get_storage_service

        allowed_types = [
            ("test.pdf", "application/pdf"),
            ("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("test.txt", "text/plain"),
            ("test.csv", "text/csv"),
            ("test.md", "text/markdown")
        ]

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for filename, mime_type in allowed_types:
                    content = b"test content"
                    files = {"file": (filename, BytesIO(content), mime_type)}
                    data = {"collection_name": "docs"}

                    # Create fresh mock for each file type
                    mock_storage = create_mock_storage_service(f"gs://bucket/{filename}")
                    app.dependency_overrides[get_storage_service] = lambda m=mock_storage: m

                    response = await client.post("/api/v1/upload", files=files, data=data)
                    assert response.status_code == 200, f"{mime_type} should be allowed"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_empty_file_returns_400(self, auth_override):
        """Empty files should be rejected.

        Expected: 400 status for 0-byte files.
        RED: This should FAIL as empty file validation doesn't exist.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        empty_content = b""
        files = {"file": ("empty.pdf", BytesIO(empty_content), "application/pdf")}
        data = {"collection_name": "docs"}

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/upload", files=files, data=data)

            assert response.status_code == 400, "Empty files should be rejected"
            error_data = response.json()
            assert "empty" in error_data["detail"].lower() or "size" in error_data["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_records_duration_metric(self, auth_override):
        """Successful upload should record duration metric.

        Expected: file_upload_duration_seconds.observe() called with file type.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key
        from app.api.v1.upload import get_storage_service
        from unittest.mock import patch

        pdf_content = b"%PDF-1.4 test content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "documents"}

        mock_storage = create_mock_storage_service("gs://bucket/test.pdf")

        app.dependency_overrides[verify_api_key] = auth_override
        app.dependency_overrides[get_storage_service] = lambda: mock_storage
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.v1.upload.file_upload_duration_seconds") as mock_duration:
                    response = await client.post("/api/v1/upload", files=files, data=data)

                    assert response.status_code == 200
                    mock_duration.labels.assert_called_once_with(file_type="pdf")
                    mock_duration.labels.return_value.observe.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_records_file_size_metric(self, auth_override):
        """Successful upload should record file size metric.

        Expected: file_upload_size_bytes.observe() called with actual file size.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key
        from app.api.v1.upload import get_storage_service
        from unittest.mock import patch

        pdf_content = b"%PDF-1.4 test content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "documents"}

        mock_storage = create_mock_storage_service("gs://bucket/test.pdf")

        app.dependency_overrides[verify_api_key] = auth_override
        app.dependency_overrides[get_storage_service] = lambda: mock_storage
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.v1.upload.file_upload_size_bytes") as mock_size:
                    response = await client.post("/api/v1/upload", files=files, data=data)

                    assert response.status_code == 200
                    mock_size.labels.assert_called_once_with(file_type="pdf")
                    mock_size.labels.return_value.observe.assert_called_once_with(len(pdf_content))
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_duration_is_positive(self, auth_override):
        """Upload should record positive duration, not zero.

        Expected: duration > 0
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key
        from app.api.v1.upload import get_storage_service
        from unittest.mock import patch

        pdf_content = b"%PDF-1.4 test"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "docs"}

        mock_storage = create_mock_storage_service("gs://bucket/test.pdf")

        app.dependency_overrides[verify_api_key] = auth_override
        app.dependency_overrides[get_storage_service] = lambda: mock_storage
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.v1.upload.file_upload_duration_seconds") as mock_duration:
                    response = await client.post("/api/v1/upload", files=files, data=data)

                    assert response.status_code == 200
                    observed_duration = mock_duration.labels.return_value.observe.call_args[0][0]
                    assert observed_duration > 0, f"Expected duration > 0, got {observed_duration}"
        finally:
            app.dependency_overrides.clear()
