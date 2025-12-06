"""Unit tests for GCS document loader service.

Tests for loading documents from Google Cloud Storage using LangChain loaders.
This service integrates with LangChain's GCSFileLoader and GCSDirectoryLoader.

Date: 2025-10-24
"""

import pytest
from unittest.mock import patch
from langchain_core.documents import Document


class TestGCSLoaderService:
    """Test suite for GCS document loader service."""

    @pytest.mark.asyncio
    async def test_load_single_file_from_gcs(self, mocker):
        """Test loading a single file from GCS.

        RED Phase: Will fail because GCSLoaderService doesn't exist.
        """
        from app.services.gcs_loader import GCSLoaderService

        # Mock LangChain's GCSFileLoader
        mock_document = Document(
            page_content="Sample content from GCS file",
            metadata={"source": "gs://test-bucket/sample.txt"}
        )

        mock_loader = mocker.Mock()
        mock_loader.load.return_value = [mock_document]

        with patch('app.services.gcs_loader.GCSFileLoader', return_value=mock_loader):
            service = GCSLoaderService(
                project_name="test-project",
                bucket="test-bucket"
            )

            # Test loading a single file
            documents = await service.load_file(blob="sample.txt")

            assert documents is not None
            assert len(documents) == 1
            assert documents[0].page_content == "Sample content from GCS file"
            assert "gs://test-bucket/sample.txt" in documents[0].metadata["source"]

    @pytest.mark.asyncio
    async def test_load_directory_from_gcs(self, mocker):
        """Test loading multiple files from GCS directory.

        RED Phase: Will fail because load_directory method doesn't exist.
        """
        from app.services.gcs_loader import GCSLoaderService

        # Mock documents from different files
        mock_documents = [
            Document(
                page_content="Content from file 1",
                metadata={"source": "gs://test-bucket/docs/file1.txt"}
            ),
            Document(
                page_content="Content from file 2",
                metadata={"source": "gs://test-bucket/docs/file2.txt"}
            )
        ]

        mock_loader = mocker.Mock()
        mock_loader.load.return_value = mock_documents

        with patch('app.services.gcs_loader.GCSDirectoryLoader', return_value=mock_loader):
            service = GCSLoaderService(
                project_name="test-project",
                bucket="test-bucket"
            )

            # Test loading from directory prefix
            documents = await service.load_directory(prefix="docs/")

            assert documents is not None
            assert len(documents) == 2
            assert documents[0].page_content == "Content from file 1"
            assert documents[1].page_content == "Content from file 2"
