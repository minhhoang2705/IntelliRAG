"""Unit tests for upload endpoint.

This module tests the file upload API endpoint.

Date: 2025-10-28
"""

from fastapi.testclient import TestClient


class TestUploadEndpoint:
    """Test suite for upload endpoint."""

    def test_upload_endpoint_exists(self):
        """Test that POST /api/v1/upload endpoint exists.

        Expected: Endpoint responds (not 404).
        """
        from app.main import app
        client = TestClient(app)

        response = client.post("/api/v1/upload")

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404

    def test_upload_accepts_file_parameter(self):
        """Test that upload endpoint accepts file parameter.

        Expected: Endpoint accepts multipart/form-data with file.
        """
        from app.main import app
        from io import BytesIO
        client = TestClient(app)

        # Create a test file
        file_content = b"Test PDF content"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}

        response = client.post("/api/v1/upload", files=files)

        # Should accept the file (not 422 validation error for missing file)
        assert response.status_code != 422

    def test_upload_returns_file_info(self):
        """Test that upload endpoint returns uploaded file information.

        Expected: Response contains filename and size.
        """
        from app.main import app
        from io import BytesIO
        client = TestClient(app)

        file_content = b"Test PDF content"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}

        response = client.post("/api/v1/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert data["filename"] == "test.pdf"
