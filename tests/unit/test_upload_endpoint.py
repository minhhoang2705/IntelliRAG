"""Unit tests for upload endpoint.

This module tests the file upload API endpoint with comprehensive TDD coverage.

Date: 2025-10-28
Updated: 2025-10-29 - Full production-ready tests (TDD RED phase)
"""

import pytest
from httpx import ASGITransport, AsyncClient
from io import BytesIO
from unittest.mock import AsyncMock, patch, MagicMock


class TestUploadEndpoint:
    """Comprehensive test suite for upload endpoint (TDD)."""

    @pytest.mark.asyncio
    async def test_upload_valid_pdf_success(self):
        """Valid PDF upload should return complete response with GCS path.
        
        Expected: 200 status, file_id (UUID), gcs_path, file_size, mime_type, uploaded_at.
        RED: This should FAIL as endpoint doesn't integrate with GCS yet.
        """
        from app.main import app
        
        pdf_content = b"%PDF-1.4 test content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "documents"}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.v1.upload.gcs_storage") as mock_gcs:
                # Mock GCS context manager
                mock_gcs.__aenter__ = AsyncMock(return_value=mock_gcs)
                mock_gcs.__aexit__ = AsyncMock(return_value=None)
                mock_gcs.upload_file = AsyncMock(return_value="gs://intellirag-uploads/uuid-123/test.pdf")
                
                response = await client.post("/api/v1/upload", files=files, data=data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify complete response schema
        assert "file_id" in data, "Response must include file_id"
        assert "gcs_path" in data, "Response must include gcs_path"
        assert "file_size" in data, "Response must include file_size"
        assert "mime_type" in data, "Response must include mime_type"
        assert "uploaded_at" in data, "Response must include uploaded_at"
        
        # Verify values
        assert data["filename"] == "test.pdf"
        assert data["gcs_path"].startswith("gs://")
        assert data["file_size"] == len(pdf_content)
        assert data["mime_type"] == "application/pdf"
        
        # Verify UUID format for file_id
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, data["file_id"]), "file_id must be UUID format"

    @pytest.mark.asyncio
    async def test_upload_file_too_large_returns_413(self):
        """Files exceeding 50MB should return 413 Payload Too Large.
        
        Expected: 413 status code with error message.
        RED: This should FAIL as size validation doesn't exist.
        """
        from app.main import app
        
        # Create 51MB file (exceeds limit)
        large_content = b"x" * (51 * 1024 * 1024)
        files = {"file": ("large.pdf", BytesIO(large_content), "application/pdf")}
        data = {"collection_name": "docs"}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/upload", files=files, data=data)
        
        assert response.status_code == 413, f"Expected 413 for large file, got {response.status_code}"
        error_data = response.json()
        assert "detail" in error_data
        assert "too large" in error_data["detail"].lower() or "size" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type_returns_400(self):
        """Unsupported file types should return 400 Bad Request.
        
        Expected: 400 status for .exe, .sh, or other non-document files.
        RED: This should FAIL as file type validation doesn't exist.
        """
        from app.main import app
        
        exe_content = b"MZ\x90\x00"  # EXE magic bytes
        files = {"file": ("malware.exe", BytesIO(exe_content), "application/x-executable")}
        data = {"collection_name": "docs"}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/upload", files=files, data=data)
        
        assert response.status_code == 400, f"Expected 400 for invalid type, got {response.status_code}"
        error_data = response.json()
        assert "detail" in error_data
        assert "invalid" in error_data["detail"].lower() or "type" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_gcs_failure_returns_500(self):
        """GCS upload failure should return 500 Internal Server Error.
        
        Expected: 500 status with error message when GCS fails.
        RED: This should FAIL as error handling doesn't exist.
        """
        from app.main import app
        
        pdf_content = b"%PDF-1.4 test"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "docs"}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.v1.upload.gcs_storage") as mock_gcs:
                mock_gcs.__aenter__ = AsyncMock(side_effect=Exception("GCS connection failed"))
                
                response = await client.post("/api/v1/upload", files=files, data=data)
        
        assert response.status_code == 500, f"Expected 500 for GCS failure, got {response.status_code}"
        error_data = response.json()
        assert "detail" in error_data
        assert "upload failed" in error_data["detail"].lower() or "error" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_requires_collection_name(self):
        """Upload should require collection_name parameter.
        
        Expected: 422 validation error when collection_name is missing.
        RED: This should FAIL as validation doesn't exist.
        """
        from app.main import app
        
        pdf_content = b"%PDF-1.4 test"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        # Missing collection_name
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 422, "Should require collection_name parameter"

    @pytest.mark.asyncio
    async def test_upload_validates_allowed_mime_types(self):
        """Only allowed MIME types should be accepted.
        
        Expected: PDF, DOCX, TXT, CSV, MD allowed. Others rejected with 400.
        RED: This should FAIL as MIME validation doesn't exist.
        """
        from app.main import app
        
        allowed_types = [
            ("test.pdf", "application/pdf"),
            ("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("test.txt", "text/plain"),
            ("test.csv", "text/csv"),
            ("test.md", "text/markdown")
        ]
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for filename, mime_type in allowed_types:
                content = b"test content"
                files = {"file": (filename, BytesIO(content), mime_type)}
                data = {"collection_name": "docs"}
                
                with patch("app.api.v1.upload.gcs_storage") as mock_gcs:
                    mock_gcs.__aenter__ = AsyncMock(return_value=mock_gcs)
                    mock_gcs.__aexit__ = AsyncMock(return_value=None)
                    mock_gcs.upload_file = AsyncMock(return_value=f"gs://bucket/{filename}")
                    
                    response = await client.post("/api/v1/upload", files=files, data=data)
                
                assert response.status_code == 200, f"{mime_type} should be allowed"

    @pytest.mark.asyncio
    async def test_upload_empty_file_returns_400(self):
        """Empty files should be rejected.
        
        Expected: 400 status for 0-byte files.
        RED: This should FAIL as empty file validation doesn't exist.
        """
        from app.main import app
        
        empty_content = b""
        files = {"file": ("empty.pdf", BytesIO(empty_content), "application/pdf")}
        data = {"collection_name": "docs"}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/upload", files=files, data=data)
        
        assert response.status_code == 400, "Empty files should be rejected"
        error_data = response.json()
        assert "empty" in error_data["detail"].lower() or "size" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_records_duration_metric(self):
        """Successful upload should record duration metric.

        Expected: file_upload_duration_seconds.observe() called with file type.
        RED: This should FAIL as metrics are not instrumented yet.
        """
        from app.main import app

        pdf_content = b"%PDF-1.4 test content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "documents"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.v1.upload.gcs_storage") as mock_gcs:
                with patch("app.api.v1.upload.file_upload_duration_seconds") as mock_duration:
                    mock_gcs.__aenter__ = AsyncMock(return_value=mock_gcs)
                    mock_gcs.__aexit__ = AsyncMock(return_value=None)
                    mock_gcs.upload_file = AsyncMock(return_value="gs://bucket/test.pdf")

                    response = await client.post("/api/v1/upload", files=files, data=data)

                    assert response.status_code == 200
                    mock_duration.labels.assert_called_once_with(file_type="pdf")
                    mock_duration.labels.return_value.observe.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_records_file_size_metric(self):
        """Successful upload should record file size metric.

        Expected: file_upload_size_bytes.observe() called with actual file size.
        RED: This should FAIL as size metric is not instrumented yet.
        """
        from app.main import app

        pdf_content = b"%PDF-1.4 test content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "documents"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.v1.upload.gcs_storage") as mock_gcs:
                with patch("app.api.v1.upload.file_upload_size_bytes") as mock_size:
                    mock_gcs.__aenter__ = AsyncMock(return_value=mock_gcs)
                    mock_gcs.__aexit__ = AsyncMock(return_value=None)
                    mock_gcs.upload_file = AsyncMock(return_value="gs://bucket/test.pdf")

                    response = await client.post("/api/v1/upload", files=files, data=data)

                    assert response.status_code == 200
                    mock_size.labels.assert_called_once_with(file_type="pdf")
                    mock_size.labels.return_value.observe.assert_called_once_with(len(pdf_content))

    @pytest.mark.asyncio
    async def test_upload_duration_is_positive(self):
        """Upload should record positive duration, not zero.

        Expected: duration > 0
        RED: Will FAIL as duration is hardcoded to 0.
        """
        from app.main import app

        pdf_content = b"%PDF-1.4 test"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"collection_name": "docs"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.v1.upload.gcs_storage") as mock_gcs:
                with patch("app.api.v1.upload.file_upload_duration_seconds") as mock_duration:
                    mock_gcs.__aenter__ = AsyncMock(return_value=mock_gcs)
                    mock_gcs.__aexit__ = AsyncMock(return_value=None)
                    mock_gcs.upload_file = AsyncMock(return_value="gs://bucket/test.pdf")

                    response = await client.post("/api/v1/upload", files=files, data=data)

                    assert response.status_code == 200
                    observed_duration = mock_duration.labels.return_value.observe.call_args[0][0]
                    assert observed_duration > 0, f"Expected duration > 0, got {observed_duration}"
